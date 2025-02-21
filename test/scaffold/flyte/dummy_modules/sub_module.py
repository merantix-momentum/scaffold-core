import flytekitplugins.omegaconf  # noqa F401
from flytekit import task, workflow
from omegaconf import DictConfig

from .sub_sub_module import sub_sub_wf


@task
def sub_task() -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing"""
    return "Test: sub-task"


@task
def dummy_task() -> str:  # noqa B008 B006
    """A dummy task that should not get registered in testing"""
    return "Test: sub-task"


@workflow
def sub_wf(cfg: DictConfig) -> str:  # noqa B008 B006
    """
    A mini-workflow for testing purposes
    """
    sub_sub_wf(cfg=cfg)
    return sub_task()


@workflow
def dummy_wf(cfg: DictConfig) -> str:  # noqa B008 B006
    """
    A dummy workflow for testing purposes - should not get registered
    """
    return sub_task()
