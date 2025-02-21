from typing import List, Tuple

import flytekitplugins.omegaconf  # noqa F401
from flytekit import conditional, dynamic, map_task, task, workflow
from omegaconf import DictConfig

from scaffold.flyte.core import mxm_register


@task
def dummy_task(wf_name: str) -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears in several test workflows"""
    return f"Test: task in {wf_name}"


@task
def top_lvl_task(cfg: DictConfig) -> Tuple[List[int], bool, bool]:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears at the top level of the main workflow"""
    return cfg.numbers, cfg.cond1, cfg.cond2


@task
def decorator_task() -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it is declared using the mxm_register decorator"""
    return "Test: decorator task"


@workflow
def decorator_wf() -> str:  # noqa B008 B006
    """A dummy workflow that should get registered in testing as it appears in a conditional within the main workflow"""
    return dummy_task(wf_name="Decorator_workflow")


@mxm_register(nodes=[decorator_task, decorator_wf])
@dynamic
def dynamic_wf() -> str:  # noqa B008 B006
    """A dynamic workflow that should get registered in testing as it appears at the top level of the main workflow"""
    for _ in range(10):
        decorator_task()
        decorator_wf()
    return "Test: dynamic"


@task
def mapped_task(i: int) -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears in a map-task call within the main workflow"""
    return f"Test: mapped task {i}"


@task
def if_task() -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears in a conditional within the main workflow"""
    return "Test: if task"


@task
def elif_task() -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears in a conditional within the main workflow"""
    return "Test: elif task"


@task
def else_task() -> str:  # noqa B008 B006
    """A dummy task that should get registered in testing as it appears in a conditional within the main workflow"""
    return "Test: else task"


@workflow
def if_wf() -> str:  # noqa B008 B006
    """A dummy workflow that should get registered in testing as it appears in a conditional within the main workflow"""
    return dummy_task(wf_name="If_workflow")


@workflow
def elif_wf() -> str:  # noqa B008 B006
    """A dummy workflow that should get registered in testing as it appears in a conditional within the main workflow"""
    return dummy_task(wf_name="Elif_workflow")


@workflow
def else_wf() -> str:  # noqa B008 B006
    """A dummy workflow that should get registered in testing as it appears in a conditional within the main workflow"""
    return dummy_task(wf_name="Else_workflow")


@workflow
def main_wf(cfg: DictConfig) -> Tuple[str, str]:  # noqa B008 B006
    """Execute all tasks for static_workflow.

    Args:
        cfg (DictConfig): master config for the hydra_launcher and tasks.
    Returns:
        dict: target_afids of executed entrypoints
    """
    numbers, my_condition, my_alternate_condition = top_lvl_task(cfg=cfg)
    dynamic_wf()
    map_task(mapped_task)(i=numbers)
    dummy1 = (
        conditional("my_conditional")
        .if_(my_condition.is_true())
        .then(if_task())
        .elif_(my_alternate_condition.is_true())
        .then(elif_task())
        .else_()
        .then(else_task())
    )
    dummy2 = (
        conditional("my_conditional")
        .if_(my_condition.is_true())
        .then(if_wf())
        .elif_(my_alternate_condition.is_true())
        .then(elif_wf())
        .else_()
        .then(else_wf())
    )
    return dummy1, dummy2
