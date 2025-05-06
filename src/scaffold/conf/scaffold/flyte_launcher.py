from dataclasses import field
from enum import Enum, unique
from typing import Dict, List, Optional

from flytekit.models.core.execution import WorkflowExecutionPhase

from scaffold.hydra.config_helpers import structured_config

GROUP = "hydra/launcher"


@unique
class FlyteDomainEnum(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


@unique
class FlyteNotificationEnum(str, Enum):
    email = "email"
    slack = "slack"


@unique
class FlyteWorkglowExecutionPhaseEnum(str, Enum):
    UNDEFINED = WorkflowExecutionPhase.UNDEFINED
    QUEUED = WorkflowExecutionPhase.QUEUED
    RUNNING = WorkflowExecutionPhase.RUNNING
    SUCCEEDING = WorkflowExecutionPhase.SUCCEEDING
    SUCCEEDED = WorkflowExecutionPhase.SUCCEEDED
    FAILING = WorkflowExecutionPhase.FAILING
    FAILED = WorkflowExecutionPhase.FAILED
    ABORTED = WorkflowExecutionPhase.ABORTED
    TIMED_OUT = WorkflowExecutionPhase.TIMED_OUT
    ABORTING = WorkflowExecutionPhase.ABORTING


@unique
class ExecutionEnvironmentEnum(str, Enum):
    local = "local"
    remote = "remote"


@structured_config(group="scaffold/flyte_launcher")
class FlyteDockerImageConfig:
    # Repo and version tag injected as ARG BASE_IMAGE and ARG BASE_VERSION into docker build step
    # If image is not being build, this is the image that is being used
    base_image: str = "${hydra.launcher.workflow.default_image.base_image}"
    base_image_version: Optional[str] = "${hydra.launcher.workflow.default_image.base_image_version}"
    # target repo and tag the built container is pushed to
    target_image: str = "${hydra.launcher.workflow.default_image.target_image}"
    target_image_version: Optional[str] = "${hydra.launcher.workflow.version}"
    # Docker context is always relative to the project root, which is identified by the presence of the pyproject.toml
    # and other files like setup.py, requirements.txt, etc. (source: https://github.com/chendaniely/pyprojroot)
    dockerfile_path: str = "infrastructure/docker/Dockerfile"
    docker_context: str = "."
    # keyword args for build call: https://docker-py.readthedocs.io/en/stable/api.html#module-docker.api.build
    buildargs: Dict[str, str] = field(default_factory=dict)
    # mount secrets to the build context
    secrets: Optional[List[str]] = None
    docker_kwargs: Dict[str, str] = field(default_factory=dict)
    # Internal image name, that tasks refer to in flyte.
    flyte_image_name: str = "default"


@structured_config(group="scaffold/flyte_launcher")
class FlyteWorkflowConfig:
    default_image: FlyteDockerImageConfig = field(
        default_factory=lambda: FlyteDockerImageConfig(
            base_image="${hydra.launcher.workflow.default_image.target_image}",
            base_image_version="latest",
        )
    )  # Image used for all tasks by default.
    extra_images: List[FlyteDockerImageConfig] = field(default_factory=list)
    ignore: str = ".flyteignore"
    version: Optional[str] = None  # If not set, will be automatically created based on git hash or random string.
    project: str = "default"  # Flyte project that the workflow will be registered in.
    domain: FlyteDomainEnum = FlyteDomainEnum.development  # Flyte domain inside the flyte project.
    cron_schedule: Optional[str] = None  # Cron schedule for the execution of the workflow.


@structured_config(group="scaffold/flyte_launcher")
class FlyteNotificationConfig:
    type: FlyteNotificationEnum = FlyteNotificationEnum.email
    phases: List[FlyteWorkglowExecutionPhaseEnum] = field(default_factory=list)
    recipients: List[str] = field(default_factory=list)


@structured_config(group=GROUP, name="flyte")
class LauncherConfig:
    _target_: str = "hydra_plugins.flyte_launcher_plugin._flyte_launcher.FlyteLauncher"
    execution_environment: ExecutionEnvironmentEnum = ExecutionEnvironmentEnum.remote
    endpoint: str = "localhost:30081"
    build_images: bool = True
    fast_serialization: bool = False
    run: bool = True
    workflow: FlyteWorkflowConfig = field(default_factory=FlyteWorkflowConfig)
    notifications: List[FlyteNotificationConfig] = field(default_factory=list)
