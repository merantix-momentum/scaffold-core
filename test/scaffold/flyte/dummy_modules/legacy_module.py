from datetime import datetime

import flytekitplugins.omegaconf  # noqa F401
from flytekit import task, workflow
from omegaconf import DictConfig


@task
def scheduled_task() -> str:  # noqa B008 B006
    """A dummy task for the scheduled dummy workflows."""
    return "Test: scheduled-task"


@workflow
def scheduled_legacy_wf(cfg: DictConfig, kickoff_time: datetime = datetime(2020, 1, 1)) -> str:  # noqa B008 B006
    """Legacy-style cron workflow: a single ``cfg`` input plus the Flyte-injected ``kickoff_time``.

    Mirrors a workflow scheduled via ``CronSchedule(kickoff_time_input_arg="kickoff_time")``.
    """
    return scheduled_task()


@workflow
def legacy_wf(cfg: DictConfig) -> str:  # noqa B008 B006
    """Legacy-style non-scheduled workflow: a single ``cfg`` input, no ``kickoff_time``."""
    return scheduled_task()
