from dummy_modules.legacy_module import legacy_wf, scheduled_legacy_wf
from omegaconf import OmegaConf

from scaffold.constants import KICKOFF_TIME_KEY
from scaffold.flyte.core import build_workflow_inputs


def test_legacy_scheduled_workflow_builds_cfg() -> None:
    """A legacy cron workflow (``cfg`` + injected ``kickoff_time``) is built in legacy mode.

    ``cfg`` must get the whole job config as a default so FlyteAdmin can create scheduled
    executions, while ``kickoff_time`` must be left out (Flyte injects it at fire time).
    """
    job_cfg = OmegaConf.create({"foo": 1, "bar": {"baz": 2}})

    inputs = build_workflow_inputs(scheduled_legacy_wf, job_cfg, hydra_cfg=None)

    assert inputs == {"cfg": job_cfg}
    assert inputs["cfg"] is job_cfg, "Legacy mode should pass the whole config through, unexploded"
    assert KICKOFF_TIME_KEY not in inputs, "kickoff_time is injected by Flyte, not from the config"


def test_legacy_non_scheduled_workflow_builds_cfg() -> None:
    """A legacy non-cron workflow (single ``cfg`` input) is still built in legacy mode."""
    job_cfg = OmegaConf.create({"foo": 1, "bar": {"baz": 2}})

    inputs = build_workflow_inputs(legacy_wf, job_cfg, hydra_cfg=None)

    assert inputs == {"cfg": job_cfg}
    assert inputs["cfg"] is job_cfg, "Legacy mode should pass the whole config through, unexploded"
