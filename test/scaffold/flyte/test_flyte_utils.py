from unittest.mock import MagicMock

import pytest
from hydra_zen import builds
from omegaconf import OmegaConf

from scaffold.flyte.flyte_utils import apply_runtime_cfg, zen_call

# ── zen_call tests ────────────────────────────────────────────────────────────


def _add(a: int, b: int) -> int:
    return a + b


def _greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"


def test_zen_call_simple() -> None:
    """zen_call instantiates config and calls the function."""
    cfg = OmegaConf.structured(builds(_add, a=1, b=2))
    assert zen_call(_add, cfg) == 3


def test_zen_call_with_kwargs() -> None:
    """zen_call forwards extra kwargs via functools.partial."""
    Conf = builds(_add, a=1, populate_full_signature=True, zen_exclude=["b"])
    cfg = OmegaConf.structured(Conf)
    assert zen_call(_add, cfg, b=10) == 11


def test_zen_call_with_defaults() -> None:
    """zen_call respects default values in the target function."""
    cfg = OmegaConf.structured(builds(_greet, name="World"))
    assert zen_call(_greet, cfg) == "Hello, World!"


# ── apply_runtime_cfg tests ──────────────────────────────────────────────────


def test_apply_runtime_cfg_no_logging() -> None:
    """apply_runtime_cfg is a no-op when logging_cfg is absent."""
    runtime_cfg = OmegaConf.create({})
    apply_runtime_cfg(runtime_cfg)


def test_apply_runtime_cfg_with_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_runtime_cfg calls configure_log when logging_cfg is present."""
    mock_configure = MagicMock()
    import hydra.core.utils

    monkeypatch.setattr(hydra.core.utils, "configure_log", mock_configure)

    logging_cfg = {"version": 1, "root": {"level": "INFO"}}
    runtime_cfg = OmegaConf.create({"logging_cfg": logging_cfg, "verbose": False})
    apply_runtime_cfg(runtime_cfg)
