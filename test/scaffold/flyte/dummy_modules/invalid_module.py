import flytekitplugins.omegaconf  # noqa F401
from flytekit import workflow
from omegaconf import DictConfig

from .sub_module import dummy_wf, sub_wf  # noqa F401


@workflow
def wrapper_wf(cfg: DictConfig) -> str:  # noqa B008 B006
    """Execute all tasks for static_workflow.

    Args:
        cfg (DictConfig): master config for the hydra_launcher and tasks.
    Returns:
        dict: target_afids of executed entrypoints
    """
    return sub_wf(cfg=cfg)
