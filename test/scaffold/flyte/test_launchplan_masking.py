from types import SimpleNamespace

import pytest
from omegaconf import OmegaConf

from scaffold.config_masking import MASKED_VALUE

pytest.importorskip("flytekit")
from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteLauncher


class _DummyWorkflow:
    interface = SimpleNamespace(inputs={"db_password": object(), "username": object()})


def test_create_launchplan_masks_sensitive_default_inputs(monkeypatch) -> None:
    """LaunchPlan defaults should not persist secret values from config."""
    captured = {}

    class _DummyLaunchPlan:
        def __init__(self) -> None:
            self.name = "dummy_lp"

    def _mock_create(*args, **kwargs):
        captured["default_inputs"] = kwargs["default_inputs"]
        return _DummyLaunchPlan()

    import flytekit

    monkeypatch.setattr(flytekit.LaunchPlan, "create", _mock_create)

    cfg = OmegaConf.create(
        {
            "hydra": {
                "launcher": {"workflow": {"cron_schedule": None}},
                "hydra_logging": {"version": 1},
                "verbose": False,
            },
            "db_password": "top-secret",
            "username": "alice",
        }
    )

    FlyteLauncher._create_launchplan(
        workflow=_DummyWorkflow(),
        cfg=cfg,
        module_name="dummy.module",
        idx=0,
        config_name="test",
        notifications=[],
    )

    assert captured["default_inputs"]["db_password"] == MASKED_VALUE
    assert captured["default_inputs"]["username"] == "alice"
