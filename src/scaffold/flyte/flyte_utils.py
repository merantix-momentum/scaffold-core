import dataclasses
import functools
import logging
import typing as t
from typing import Any, Callable

from flytekit.configuration import Config as FlyteConfig
from flytekit.core import task
from flytekit.core.cache import Cache
from flytekit.remote import FlyteLaunchPlan, FlyteRemote
from hydra_zen import zen
from omegaconf import DictConfig, OmegaConf

from scaffold.constants import RUNTIME_CFG_KEY
from scaffold.flyte.core import build_workflow_inputs

logger = logging.getLogger(__name__)


def apply_runtime_cfg(runtime_cfg: DictConfig) -> None:
    """Apply runtime configuration (usually inside a Flyte pod).

    Currently configures Python logging via Hydra's ``configure_log`` when
    ``logging_cfg`` is present in *runtime_cfg*.

    Args:
        runtime_cfg (DictConfig): A DictConfig that conforms to ``RuntimeConf`` (fields: ``logging_cfg``,
            ``verbose``).
    """
    logging_cfg = OmegaConf.select(runtime_cfg, "logging_cfg")
    if logging_cfg is not None:
        from hydra.core.utils import configure_log

        configure_log(logging_cfg, OmegaConf.select(runtime_cfg, "verbose", default=False))


def runtime_task(
    *,
    runtime_cfg_key: str = RUNTIME_CFG_KEY,
    **task_kwargs: Any,
) -> Callable[[Callable[..., Any]], Any]:
    """Drop-in replacement for ``@task`` that applies ``runtime_cfg`` before execution.

    In addition to calling the wrapped function, this decorator:

    1. Calls ``apply_runtime_cfg`` with the ``runtime_cfg`` keyword argument so
       that logging (and other runtime settings) are configured at the start of
       every remote task execution.
    2. Automatically adds ``runtime_cfg`` to ``Cache.ignored_inputs`` so that
       changes to runtime-only settings (e.g. log verbosity) never invalidate
       the Flyte task cache.

    Args:
        runtime_cfg_key (str): Name of the ``DictConfig`` parameter that carries runtime settings.
            Defaults to ``RUNTIME_CFG_KEY``.
        **task_kwargs (Any): All keyword arguments accepted by flytekit's ``@task`` decorator (e.g.
            ``requests``, ``cache``, ``container_image``).

    Example
    -------
    ::

        @runtime_task(requests=DEFAULT_RESOURCES, cache=Cache(version="1"))
        def my_task(cfg: DictConfig, runtime_cfg: DictConfig) -> str:
            return zen(my_function)(cfg)
    """
    cache = task_kwargs.get("cache")
    if isinstance(cache, Cache):
        existing = (cache.ignored_inputs,) if isinstance(cache.ignored_inputs, str) else cache.ignored_inputs
        task_kwargs["cache"] = dataclasses.replace(
            cache,
            ignored_inputs=tuple(set(existing) | {runtime_cfg_key}),
        )

    def decorator(fn: Callable[..., Any]) -> Any:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            runtime_cfg = kwargs.get(runtime_cfg_key)
            if isinstance(runtime_cfg, DictConfig):
                apply_runtime_cfg(runtime_cfg)
            else:
                logger.warning("Not explicitly applying runtime config. If running locally, this is probably fine.")
            return fn(*args, **kwargs)

        return task(**task_kwargs)(wrapper)

    return decorator


def zen_call(fn: t.Callable[..., t.Any], cfg: t.Dict, **kwargs: t.Any) -> t.Any:
    """Invoke a zen-wrapped function with config plus optional runtime kwargs.

    A convenience over the two patterns that appear in task bodies:

    - ``zen(fn)(cfg)`` — when all inputs come from the config.
    - ``zen(functools.partial(fn, **kwargs))(cfg)`` — when some inputs come
      from previous task outputs and cannot be expressed as config fields.

    Args:
        fn (Callable[..., Any]): Plain Python function to wrap with ``zen()``.
        cfg (Dict): Per-task ``DictConfig`` passed in from the workflow.
        **kwargs (Any): Runtime values to pre-fill on *fn* before ``zen()`` processes the
            config. When empty, no ``partial`` is created.

    Returns:
        Any: The return value of the zen-wrapped function call.
    """
    wrapped = functools.partial(fn, **kwargs) if kwargs else fn
    return zen(wrapped)(cfg)


def run_local_workflow(workflow_fn: t.Any, cfg: t.Dict) -> None:
    """Execute a Flyte workflow from Hydra's ``main()`` function.

    Builds ``runtime_cfg`` from the active ``HydraConfig`` and maps all other
    config keys to workflow inputs by name.

    Args:
        workflow_fn (WorkflowBase): A flytekit ``@workflow``-decorated function.
        cfg (DictConfig): The ``DictConfig`` received by the Hydra ``main()`` function.

    Example
    -------
    ::

        def main(cfg: DictConfig) -> None:
            run_workflow(pipeline, cfg)
    """
    from hydra.core.hydra_config import HydraConfig

    inputs = build_workflow_inputs(workflow_fn, cfg, HydraConfig.get())
    workflow_fn(**inputs)


class FlyteRemoteHelper:
    def __init__(self, domain: str, admin_endpoint: str, insecure: bool = True, project: str = "default"):
        """
        Instantiates a flyteRemote object internally.

        Args:
            domain (str): In which flyte domain we operate, usually one of staging, development, production
            admin_endpoint (str): Connection to Flyte admin. Usually 'flyteadmin.flyte.svc.cluster.local:81' within the
                cluster, or localhost:30081 if forwarded
                via `kubectl port-forward --address 0.0.0.0 svc/flyteadmin 30081:81 -n flyte`
            insecure (bool): If true, no SSL is used for the connection. If the connection is just within cluster or
                through a port-forward done by kubectl it can be set to True.
            project (str): flyte project to operate in. Defaults to 'default'
        """
        self.flyte_remote = FlyteRemote(
            config=FlyteConfig.for_endpoint(endpoint=admin_endpoint, insecure=insecure),
            default_domain=domain,
            default_project=project,
        )

    def fetch_launchplan(self, launchplan_name: str) -> FlyteLaunchPlan:
        """Fetches a registered, remote launchplan by name."""
        return self.flyte_remote.fetch_launch_plan(name=launchplan_name)

    def execute_flyte_launchplan(self, launchplan_name: str, input_args: dict, wait: bool = False) -> t.Any:
        """
        Fetches a launchplan using the connection from init and executes it with the given arguments.

        Args:
            launchplan_name (str): Name of the launchplan.
                Note that launchplans registered via scaffold usually have a _0 suffix.
            input_args (dict): A dictionary mapping from workflow input arguments as string keys to the values with
                which the workflow gets executed. All arguments that do not have a default argument in the launchplan
                need to be provided. Note that cfg does have a default argument in launchplans registered using the
                flyte launcher.
            wait (bool): If true, this function will only return once the workflow finishes. Defaults to False.

        Returns:
            FlyteWorkflowExecution: The execution object returned by the remote client.
        """
        lp = self.fetch_launchplan(launchplan_name)
        r = self.flyte_remote.execute(lp, inputs=input_args, wait=wait)
        return r
