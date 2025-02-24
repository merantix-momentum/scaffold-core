import flytekitplugins.omegaconf  # noqa F401
from flytekit import task, workflow
from omegaconf import DictConfig

from .sub_module import sub_wf


@task
def dummy_task() -> str:  # noqa B008 B006
    """A dummy task that should not get registered in testing"""
    return "Test: subtask"


@workflow
def main_wf(cfg: DictConfig) -> str:  # noqa B008 B006
    """Execute all tasks for static_workflow.

    Args:
        cfg (DictConfig): master config for the hydra_launcher and tasks.
    Returns:
        dict: target_afids of executed entrypoints
    """
    return sub_wf(cfg=cfg)
