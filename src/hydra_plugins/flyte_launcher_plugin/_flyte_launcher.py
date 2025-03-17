from __future__ import annotations

import copy
import gzip
import importlib
import logging
import os
import pathlib
import random
import string
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

import pyprojroot
from flytekit import Email, Slack
from flytekit.core.notification import Notification
from flytekit.exceptions.user import FlyteEntityNotExistException, FlyteInvalidInputException

try:
    # not available in older flyte versions
    from flytekit.exceptions.system import FlyteSystemUnavailableException

    imported_unavailable_exceptions = True
except ImportError:
    imported_unavailable_exceptions = False
from hydra.core.utils import configure_log, filter_overrides, JobReturn, run_job, setup_globals
from hydra.plugins.launcher import Launcher
from hydra.types import HydraContext, TaskFunction
from omegaconf import DictConfig, OmegaConf, open_dict

from scaffold.conf.scaffold.flyte_launcher import (
    ExecutionEnvironmentEnum,
    FlyteDockerImageConfig,
    FlyteNotificationConfig,
    FlyteNotificationEnum,
    FlyteWorkflowConfig,
)

if TYPE_CHECKING:
    from flytekit import LaunchPlan, Workflow
    from flytekit.core.base_task import PythonTask
    from flytekit.core.workflow import WorkflowBase
    from flytekit.remote.entities import FlyteLaunchPlan
    from flytekit.remote.remote import FlyteRemote

logger = logging.getLogger(__name__)


class FlyteLauncher(Launcher):
    def __init__(
        self,
        execution_environment: str,
        endpoint: str,
        build_images: bool,
        fast_serialization: bool,
        run: bool,
        workflow: FlyteWorkflowConfig,
        notifications: Optional[List[FlyteNotificationConfig]],
    ) -> None:
        """
        Construct Flyte launcher.

        Args:
            execution_environment (str): Can be either 'local' or 'remote'
            endpoint (str): The Flyte platform endpoint to connect to
            build_images (bool): whether the launcher should build the docker images containing the workflow code
            fast_serialization (bool): whether to use fast serialization to inject code into existing containers
            run (bool): whether the workflow is executed after registration
            workflow: (FlyteWorkflowConfig): the config related to workflow execution/registration
            notifications (Optional[List[FlyteNotificationConfig]]): A list of `FlyteNotificationConfig` objects,
                each specifying the notification settings for the workflow. These configurations define:
                    - **Phases**: Workflow execution phases that will trigger the notification.
                    - **Recipients**: A list of recipient identifiers (e.g., email addresses or Slack email).
                    - **Type**: The communication method for the notification, such as email or Slack.
        """
        self.config: Optional[DictConfig] = None
        self.hydra_context: Optional[HydraContext] = None
        self.workflow_config: FlyteWorkflowConfig = workflow

        assert execution_environment in [
            "local",
            "remote",
        ], f"Execution environment must be either 'local' or 'remote', but was '{execution_environment}'."
        self.execution_environment = execution_environment
        self.notifications = notifications
        self.endpoint = endpoint
        self.build_images = build_images
        self.fast_serialization = fast_serialization
        self.run = run

    def setup(
        self,
        *,
        hydra_context: HydraContext,
        task_function: TaskFunction,
        config: DictConfig,
    ) -> None:
        """Setup hydra config and context."""
        self.config = config
        self.hydra_context = hydra_context
        self.task_function = task_function

    def _hydra_launch_setup(self) -> None:
        setup_globals()
        assert self.config is not None
        assert self.hydra_context is not None
        configure_log(self.config.hydra.hydra_logging, self.config.hydra.verbose)
        sweep_dir = Path(str(self.config.hydra.sweep.dir))
        sweep_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Launch job with Flyte Launcher.")
        logger.info(f"Sweep output dir : {sweep_dir}")

    def _extract_module_name_from_task_function(self) -> str:
        """Extract the module name from the @hydra.main decorated task function in the workflow file.
        The module of the task function at runtime should be __main__ since it is executed with
        `python path/to/workflow.py`.
        This function tries to extract the corresponding module name as 'path.to.workflow'.

        This is important, because flyte needs to find the workflow with the module notation, since __main__ is not
        defined inside the container when running remotely.
        """
        path_flag = False
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())  # The src directory needs to be in the PATH in order to find module_name.
            path_flag = True

        main_module = sys.modules[self.task_function.__module__].__file__
        relative_path = os.path.relpath(main_module, os.getcwd())
        module_string = os.path.splitext(relative_path)[0].replace(os.sep, ".")
        if module_string.startswith("src."):
            # we expect a src dir to be in pythonpath, but not to be a valid python package, i.e. has an init file
            # therefore the flyte task can run into issues when trying to import package 'src'. So we dont want to
            # have module names starting with src
            module_string = module_string[4:]

        # Checking if the module if importable, without importing it again, since it is already imported as __main__.
        if importlib.util.find_spec(module_string) is None:
            raise ModuleNotFoundError(
                f"Could not find the module '{module_string}'.\n"
                "This module is assumed to be the module that contains your @hydra.main decorated function.\n"
                f"Please check if the path to your task function is a valid python module: {main_module.__file__}."
            )
        if path_flag:
            sys.path.remove(os.getcwd())

        return module_string

    @staticmethod
    def _get_workflows_and_tasks(module_string: str) -> Tuple[WorkflowBase, List[WorkflowBase], List[PythonTask]]:
        """Recursively find all PythonTask and WorkflowBase objects in the given module.
        We assume one workflow to be the "main_workflow" which ties it all together.
        Please refer to the docs of 'identify_main_workflow' for more details.

        Args:
            module_string (str): String like 'flyte_workflows.my_workflow' corresponding to a
                file like 'flyte_workflows/my_workflow.py'.
        """

        from flytekit.core.base_task import PythonTask
        from flytekit.core.python_function_task import PythonFunctionTask
        from flytekit.core.workflow import WorkflowBase

        from scaffold.flyte.core import identify_main_workflow

        main_workflow, flyte_entities = identify_main_workflow(module_string)

        # order of registration matters because flyte checks dependency relationships
        # tasks get separated and registered first
        # workflows are registered in reverse order of discovery (lowest recursion first)
        for entity in flyte_entities:
            if not isinstance(entity, PythonTask) and not isinstance(entity, WorkflowBase):
                raise TypeError(
                    f"Expected only entities of type PythonTask or WorkflowBase, but found '{type(entity)}' instead!"
                )
        tasks = [
            obj
            for obj in flyte_entities
            if isinstance(obj, PythonTask)
            and getattr(obj, "execution_mode", None) != PythonFunctionTask.ExecutionBehavior.DYNAMIC
        ]
        workflows = [obj for obj in reversed(flyte_entities) if isinstance(obj, WorkflowBase)]

        return main_workflow, workflows, tasks

    def _resolve_pipeline_version(self) -> str:
        """Generate a unique version string that can be used for tagging build images and the flyte pipeline.
        NOTE: Make sure that you set a unique pipeline version if you set it manually in the config.

        We try to generate a version based on this order of trials:
        1. Manually set version in config.
        2. Git repository hash + '-dirty' if uncommited changes exist + random string if flyte domain is `development`
        3. Random string as a fallback.

        Returns:
            str - the pipeline version
        """
        from git.exc import InvalidGitRepositoryError

        from scaffold.flyte.git import get_branch_identifier

        if (version := self.config.hydra.launcher.workflow.version) is not None:
            pipeline_version = version
            logger.info(f"Using specified pipeline version from config: '{pipeline_version}'.")
        else:
            try:
                pipeline_version = get_branch_identifier(
                    random_suffix=(self.config.hydra.launcher.workflow.domain == "development")
                )
                logger.info(f"Generated pipeline version based on git repo: '{pipeline_version}'.")
            except InvalidGitRepositoryError:
                pipeline_version = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
                logger.info(
                    "Could not find a git repository."
                    f" Generated pipeline version based on random string: '{pipeline_version}'."
                )
                if not self.build_images:
                    logging.info(
                        "No images will be build and no docker images with the random pipeline version exist.\n"
                        "Will use provided target versions to execute tasks in."
                    )
                    for image in [
                        self.config.hydra.launcher.workflow.default_image
                    ] + self.config.hydra.launcher.workflow.extra_images:
                        if image.target_image_version is None:
                            raise ValueError(
                                f"Version for image '{image.flyte_image_name}' ({image.target_image})"
                                f" was not explicitly set."
                            )
                        logging.info(
                            f"Setting image '{image.flyte_image_name}' ({image.target_image}) version to tag "
                            f"'{image.target_image_version}'."
                        )

        # Set config entry so that it can be interpolated to individual image descriptions
        self.config.hydra.launcher.workflow.version = pipeline_version
        return pipeline_version

    @staticmethod
    def _resolve_docker_context_to_root_project_dir(image_config: FlyteDockerImageConfig) -> Tuple[str]:
        """
        Resolve the docker context relative to the root of the `project.
        This enables the user to run the launcher from any subdirectory of the project.

        Args:
            image_config (FlyteDockerImageConfig): Image to build

        Returns:
            Tuple[str, str] - The relative path to the project root and the relative path to the dockerfile

        """
        # https://github.com/chendaniely/pyprojroot/blob/main/src/pyprojroot/here.py
        project_root = pyprojroot.here()
        logger.info(f"Identified project root as: {project_root}")

        # get relative path from current working directory to project root
        project_root_rel = os.path.relpath(project_root, start=os.getcwd())
        docker_context = os.path.join(
            project_root_rel,
            image_config.docker_context,
        )
        dockerfile_path = os.path.join(docker_context, image_config.dockerfile_path)
        return docker_context, dockerfile_path

    def _run_image_build(self) -> Tuple[str, Dict[str, str]]:
        """
        Build all images specified in hydra config and return names

        Returns:
            Tuple[str, Dict[str, str]] - The name of the default image as well as a mapping from flyte image names to
                                         their full identifiers.
        """
        from scaffold.flyte.image_builder import build_image

        extra_images = {}

        self._check_unique_image_repo_conf()

        with open_dict(self.config.hydra.launcher.workflow.default_image.buildargs) as build_args:
            build_args["BASE_IMAGE"] = self.config.hydra.launcher.workflow.default_image.base_image
            build_args["BASE_VERSION"] = self.config.hydra.launcher.workflow.default_image.base_image_version

        if (
            self.config.hydra.launcher.workflow.default_image.base_image
            == self.config.hydra.launcher.workflow.default_image.target_image
        ):
            logger.error(
                f"Base image and target image for default image "
                f"'{self.config.hydra.launcher.workflow.default_image.flyte_image_name}' are identical: "
                f"{self.config.hydra.launcher.workflow.default_image.base_image}.\n"
                f" Please use a different target instead of mutating an existing image"
            )

        docker_context, dockerfile = self._resolve_docker_context_to_root_project_dir(
            self.config.hydra.launcher.workflow.default_image
        )
        default_image_tag = build_image(
            dockerfile=dockerfile,
            workdir_path=docker_context,
            image_repo=self.config.hydra.launcher.workflow.default_image.target_image,
            image_tag=self.config.hydra.launcher.workflow.default_image.target_image_version,
            push_image=True,
            buildargs=self.config.hydra.launcher.workflow.default_image.buildargs,
            secrets=self.config.hydra.launcher.workflow.default_image.secrets,
            **OmegaConf.to_container(self.config.hydra.launcher.workflow.default_image.docker_kwargs),
        )

        if self.config.hydra.launcher.workflow.extra_images is not None:
            for extra_image in self.config.hydra.launcher.workflow.extra_images:
                with open_dict(extra_image.buildargs) as build_args:
                    build_args["BASE_IMAGE"] = extra_image.base_image
                    build_args["BASE_VERSION"] = extra_image.base_image_version

                if extra_image.base_image == extra_image.target_image:
                    logger.error(
                        f"Base image and target image for extra image "
                        f"'{self.config.hydra.launcher.workflow.default_image.flyte_image_name}' are identical: "
                        f"{self.config.hydra.launcher.workflow.default_image.base_image}.\n"
                        f" Please use a different target instead of mutating an existing image"
                    )
                docker_context, dockerfile = self._resolve_docker_context_to_root_project_dir(extra_image)
                tag = build_image(
                    dockerfile=dockerfile,
                    workdir_path=docker_context,
                    image_repo=extra_image.target_image,
                    image_tag=extra_image.target_image_version,
                    push_image=True,
                    buildargs=extra_image.buildargs,
                    secrets=extra_image.secrets,
                    **OmegaConf.to_container(extra_image.docker_kwargs),
                )
                extra_images[extra_image.flyte_image_name] = tag

        return default_image_tag, extra_images

    def _check_unique_image_repo_conf(self) -> None:
        """
        Check that all configured image repositories are unique.
        If not, this leads to unexpected behavior, as only the latest built image will be used for all tasks.

        Raises:
            ValueError: If any of the configured image repositories are not unique.
        """
        if self.config.hydra.launcher.workflow.extra_images is not None:
            repos = [e_cfg.target_image for e_cfg in self.config.hydra.launcher.workflow.extra_images] + [
                self.config.hydra.launcher.workflow.default_image.target_image
            ]
            if len(repos) != len(set(repos)):
                raise ValueError(
                    "All specified image repositories must be unique. "
                    "Please check your flyte launcher config of default and extra images."
                )

    def _get_and_check_image_tags_without_building(self) -> Tuple[str, Dict[str, str]]:
        """
        Check the existence of provided image details and compile full list of identifiers for flyte

        Returns:
            Tuple[str, Dict[str, str]] - The name of the default image as well as a mapping from flyte image names to
                                         their full identifiers.
        """
        import docker

        docker_client = docker.from_env()

        def _check_if_image_exists(image: str) -> None:
            try:
                docker_client.images.get_registry_data(image)
            except docker.errors.NotFound:
                msg = f"Could not find image: {image}!\n"
                raise UserWarning(msg)

        extra_images = {}
        default_image_tag = (
            f"{self.config.hydra.launcher.workflow.default_image.base_image}:"
            f"{self.config.hydra.launcher.workflow.default_image.base_image_version}"
        )
        _check_if_image_exists(default_image_tag)
        if self.config.hydra.launcher.workflow.extra_images is not None:
            for extra_image in self.config.hydra.launcher.workflow.extra_images:
                extra_image_uri = f"{extra_image.target_image}:{extra_image.target_image_version}"
                _check_if_image_exists(extra_image_uri)
                extra_images[extra_image.flyte_image_name] = extra_image_uri

        return default_image_tag, extra_images

    @staticmethod
    def _format_notifications(notifications_config: Optional[List[FlyteNotificationConfig]]) -> List[Notification]:
        """
        Converts FlyteNotificationConfig to a list of Flyte notification objects.
        """
        notifications: List[Notification] = []

        for notification in notifications_config:
            if notification.type == FlyteNotificationEnum.email:
                notifications.append(
                    Email(
                        phases=notification.phases,
                        recipients_email=notification.recipients,
                    )
                )
            elif notification.type == FlyteNotificationEnum.slack:
                notifications.append(
                    Slack(
                        phases=notification.phases,
                        recipients_email=notification.recipients,
                    )
                )

        return notifications

    @staticmethod
    def _create_launchplan(
        workflow: Workflow,
        cfg: DictConfig,
        module_name: str,
        idx: int,
        config_name: str,
        notifications: List[Notification],
    ) -> LaunchPlan:
        """Create a launch plan with the given config.

        This is created to make the workflows executable from the UI. With the templated launch plans, the
        user can execute the workflows from the UI without the need of explicitly typing/giving any config.
        The launchplan will have the overriden configs as the default input.

        If `cfg` contains cronjob configuration, it is applied to the LaunchPlan.

        Args:
            cfg (DictConfig): hydra configuration of the workflow.
            workflow (Workflow): workflow to be executed with the prepared LaunchPlan.
            module_name (str): The name of the python module containing the workflow.
            idx (int): idx of the respective hydra override belonging to this `cfg` object.
            config_name (str): Name of the base hydra configuration file used to launch the workflow.
            notifications (List[Notification]): A list of `Notification` objects, where each object defines:
                - **Phases**: The workflow execution phases that will trigger the notification.
                - **Recipients**: A list of recipient identifiers to be notified.
                - **Type**: The notification channel, such as email or Slack.

        Returns:
            A LaunchPlan object

        """
        from croniter import croniter
        from flytekit import CronSchedule, LaunchPlan

        cfg_arg_name = "cfg"
        kickoff_time_arg_name = "kickoff_time"
        kwargs = {}

        if cfg_arg_name not in workflow.interface.inputs.keys():
            raise ValueError(f"The arguments of the main workflow must contain '{cfg_arg_name}'")

        if (cron_exp := cfg.hydra.launcher.workflow.cron_schedule) is not None:
            assert idx == 0, "Cronjobs can't be registered with multiple overrides!"
            assert croniter.is_valid(cron_exp), f"Invalid cron expression {cron_exp}."

            kwargs["schedule"] = CronSchedule(
                schedule=cron_exp,
                kickoff_time_input_arg=kickoff_time_arg_name,
            )

        # Remove the hydra section that is passed to the Flyte workflow.
        # WARNING: If the hydra section is passed, set "config.hydra.job.id" and "config.hydra.job.num".
        # The hydra section can contain interpolation entries, which expect these values to exist.
        cfg = copy.deepcopy(cfg)
        with open_dict(cfg):
            del cfg["hydra"]

        templated_lp = LaunchPlan.create(
            f"hydra_workflow_cfg_{module_name}_{config_name}_{idx}",
            workflow=workflow,
            notifications=notifications,
            default_inputs={
                cfg_arg_name: cfg,
            },
            **kwargs,
        )
        if not hasattr(templated_lp, "__name__"):
            # necessary for flyte version 1.14.0, see https://github.com/flyteorg/flyte/issues/6062
            templated_lp.__name__ = templated_lp.name

        return templated_lp

    @staticmethod
    def _activate_launch_plan(remote: FlyteRemote, launchplan: FlyteLaunchPlan) -> None:
        """Activate a cron scheduled launch plan.

        Args:
            remote (FlyteRemote): a FlyteRemote object to send the update request
            launchplan (FlyteLaunchPlan): a remote flyte launchplan with cron scheduler to activate
        """
        from flytekit.models.launch_plan import LaunchPlanState

        remote.client.update_launch_plan(
            id=launchplan.id,
            state=LaunchPlanState.ACTIVE,
        )

    def _launch_local(self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int) -> Sequence[JobReturn]:
        """
        Execute workflow locally.

        Method borrowed from hydra's basic launcher:
        https://github.com/facebookresearch/hydra/blob/809718cdcd64f9cd930d26dea69f2660a6ffa833/hydra/_internal/core_plugins/basic_launcher.py#L51
        """
        logger.info("Workflow executed locally, flyte workflow config is ignored.")

        setup_globals()
        assert self.hydra_context is not None
        assert self.config is not None
        assert self.task_function is not None

        configure_log(self.config.hydra.hydra_logging, self.config.hydra.verbose)
        sweep_dir = self.config.hydra.sweep.dir
        Path(str(sweep_dir)).mkdir(parents=True, exist_ok=True)
        logger.info(f"Launching {len(job_overrides)} jobs locally")
        runs: List[JobReturn] = []
        for idx, overrides in enumerate(job_overrides):
            idx = initial_job_idx + idx
            lst = " ".join(filter_overrides(overrides))
            logger.info(f"\t#{idx} : {lst}")
            sweep_config = self.hydra_context.config_loader.load_sweep_config(self.config, list(overrides))
            with open_dict(sweep_config):
                sweep_config.hydra.job.id = idx
                sweep_config.hydra.job.num = idx
            ret = run_job(
                hydra_context=self.hydra_context,
                task_function=self.task_function,
                config=sweep_config,
                job_dir_key="hydra.sweep.dir",
                job_subdir_key="hydra.sweep.subdir",
            )
            runs.append(ret)
            configure_log(self.config.hydra.hydra_logging, self.config.hydra.verbose)
        return runs

    def _launch_remote(self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int) -> Sequence[JobReturn]:
        """Register tasks and workflow with flyte and optionally execute workflow."""

        # NOTE: We need these lazy imports, since hydra tries to register this plugin, even if you don't
        # set the launcher to hydra/launcher=flyte. This means, that users who want to install scaffold,
        # but want to use hydra without flyte, will get a user warning for not being able to import flytekit.

        from flytekit.configuration import FastSerializationSettings
        from flytekit.exceptions.user import FlyteEntityAlreadyExistsException
        from flytekit.tools.fast_registration import compute_digest
        from flytekit.tools.script_mode import tar_strip_file_attributes

        from hydra_plugins.flyte_launcher_plugin._flyte_ignore import FlyteIgnore
        from scaffold.flyte.core import get_serialization_settings, temp_flyte_remote

        # process configs and local directory structure
        self._hydra_launch_setup()

        config_name = self.config.hydra.job.config_name
        module_string = self._extract_module_name_from_task_function()
        main_workflow, workflows, tasks = self._get_workflows_and_tasks(module_string)
        pipeline_version = self._resolve_pipeline_version()

        configs, templated_lps = [], []

        notifications = self._format_notifications(self.notifications)

        for idx, overrides in enumerate(job_overrides):
            if len(overrides) > 0:
                config = self.hydra_context.config_loader.load_sweep_config(self.config, overrides)
            else:
                config = self.config

            configs.append(config)
            templated_lps.append(
                self._create_launchplan(main_workflow, config, module_string, idx, config_name, notifications)
            )

        # prepare docker image (or verify provided tags exist)
        if self.build_images:
            logging.info("Building images ...")
            default_image_tag, extra_images = self._run_image_build()
        else:
            logging.info("Skip building images ...")
            default_image_tag, extra_images = self._get_and_check_image_tags_without_building()

        logging.info(f"Using default image: {default_image_tag}")
        logging.info(f"Using extra images: {extra_images}")

        with temp_flyte_remote(
            project=self.config.hydra.launcher.workflow.project,
            domain=self.config.hydra.launcher.workflow.domain,
            endpoint=self.endpoint,
        ) as remote:
            # if in fast-serialisation mode, prepare archive to inject into existing container - altered copy of:
            # https://github.com/flyteorg/flytekit/blob/5dd887cf5cbe817a35d682a32886f304a97fc910/flytekit/remote/remote.py#L769
            # https://github.com/flyteorg/flytekit/blob/5dd887cf5cbe817a35d682a32886f304a97fc910/flytekit/remote/remote.py#L695
            # https://github.com/flyteorg/flytekit/blob/5dd887cf5cbe817a35d682a32886f304a97fc910/flytekit/tools/fast_registration.py#L22

            fast_serialization_settings = None
            if not self.build_images and self.fast_serialization:
                logging.info(
                    "Registering workflows and tasks in fast serialization mode!\n"
                    "This means that we will copy your code into the respective containers without building!"
                )

                # build and upload tar to inject in existing container
                ignorer = FlyteIgnore(".", ignore_path=self.config.hydra.launcher.workflow.ignore)
                digest = compute_digest(pathlib.Path("."), ignorer.is_ignored)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    archive_fname = os.path.join(tmp_dir, f"fast_{digest}.tar.gz")
                    tar_path = os.path.join(tmp_dir, "tmp.tar")
                    with tarfile.open(tar_path, "w") as tar:
                        tar.add(".", arcname="", filter=lambda x: ignorer.tar_filter(tar_strip_file_attributes(x)))
                    with gzip.GzipFile(filename=archive_fname, mode="wb", mtime=0) as gzipped:
                        with open(tar_path, "rb") as tar_file:
                            gzipped.write(tar_file.read())
                    # upload archive
                    _, native_url = remote.upload_file(pathlib.Path(archive_fname))

                # create serialisation description for registration of new task versions
                fast_serialization_settings = FastSerializationSettings(
                    enabled=True,
                    destination_dir=".",
                    distribution_location=native_url,
                )

            settings = get_serialization_settings(
                default_image=default_image_tag,
                extra_images=extra_images,
                fast_serialization_settings=fast_serialization_settings,
                domain=self.config.hydra.launcher.workflow.domain,
                project=self.config.hydra.launcher.workflow.project,
            )

            # register workflows and tasks
            try:
                for task in tasks:
                    remote.register_task(task, serialization_settings=settings, version=pipeline_version)
                for workflow in workflows:
                    remote.register_workflow(workflow, serialization_settings=settings, version=pipeline_version)
                remote.register_workflow(main_workflow, serialization_settings=settings, version=pipeline_version)
            except (FlyteInvalidInputException, FlyteEntityAlreadyExistsException):
                logger.info(f"Workflow already registered with version {pipeline_version}.")
            except Exception as e:
                if imported_unavailable_exceptions and isinstance(e, FlyteSystemUnavailableException):
                    raise FlyteSystemUnavailableException(
                        "Couldnt reach flyte! Check if you have port forwarded flyteadmin service, "
                        "see https://docs.scaffold.merantix-momentum.cloud/usage/hydra_flyte_launcher/full_example.html"
                    )
                else:
                    raise e

            else:
                logger.info("Workflows and tasks successfully registered.")

            # fetch or register launchplan
            for config, templated_lp in zip(configs, templated_lps):
                try:
                    remote_lp = remote.fetch_launch_plan(
                        name=templated_lp.name,
                        version=pipeline_version,
                        project=self.config.hydra.launcher.workflow.project,
                        domain=self.config.hydra.launcher.workflow.domain,
                    )
                except FlyteEntityNotExistException:
                    # we need to register a new launch plan as we couldnt fetch one
                    lp_ver = pipeline_version + "_lp"  # flyte 1.14+ doesnt like same version for lp and tasks
                    settings.version = lp_ver
                    remote_lp = remote.register_launch_plan(
                        templated_lp,
                        version=lp_ver,
                        project=self.config.hydra.launcher.workflow.project,
                        domain=self.config.hydra.launcher.workflow.domain,
                        serialization_settings=settings,
                    )

                # Leave the inputs empty here, as it was configured while registering the LaunchPlan.
                if self.run is True:
                    if config.hydra.launcher.workflow.cron_schedule is not None:
                        self._activate_launch_plan(
                            remote=remote,
                            launchplan=remote_lp,
                        )
                        logger.info(
                            f"Launchplan {remote_lp.name} with cron schedule is activated "
                            f"with version: {pipeline_version}."
                        )
                    else:
                        remote.execute(
                            remote_lp, wait=False, inputs=templated_lp.saved_inputs, type_hints={"cfg": DictConfig}
                        )
                        logger.info(f"Workflow {main_workflow.name} is executed with version: {pipeline_version}.")

            if self.run is False:
                lp_names = " ".join([f"'{lp.name}'" for lp in templated_lps])
                logger.info(f"Launchplans {lp_names} are registered with version: {pipeline_version}.")

        return []

    def launch(self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int) -> Sequence[JobReturn]:
        """
        Launch the workflow either locally or register the workflow with flyte and optionally execute it.
        Having this functionality is useful for offering ability to switch between local and remote execution
        without changing the entire hydra config, but only a single flag.

        Args:
            job_overrides: a List of List<String>, where each inner list is the arguments for one job run.
            initial_job_idx: Initial job idx in batch.

        Returns:
            an array of return values from run_job with indexes corresponding to the input list indexes.
        """

        if self.execution_environment == ExecutionEnvironmentEnum.local:
            return self._launch_local(job_overrides, initial_job_idx)
        elif self.execution_environment == ExecutionEnvironmentEnum.remote:
            return self._launch_remote(job_overrides, initial_job_idx)
        else:
            raise ValueError(
                f"Execution environment must be either 'local' or 'remote', but was '{self.execution_environment}'."
            )
