"""Tests for the deprecated Entrypoint class.

These tests verify backward compatibility for projects that still use Entrypoint/EntrypointConf
while emitting DeprecationWarnings to encourage migration to hydra-zen.
"""

from contextlib import AbstractContextManager
from typing import Any

import pytest
from hydra_zen import make_config
from omegaconf import OmegaConf

from scaffold.conf.scaffold.entrypoint import EntrypointConf
from scaffold.ctx_manager import DISABLED_LOGGING
from scaffold.entrypoints import Entrypoint

# All tests in this file exercise deprecated APIs — suppress warnings globally
# except where we explicitly test that the warning fires.
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# Helpers that simulate an "old project" using the deprecated Entrypoint API


ExampleEntrypointConf = make_config(bases=(EntrypointConf,), greeting="Hey")


class MyContext(AbstractContextManager):
    def __init__(self) -> None:
        self.ctx_active = False

    def __enter__(self) -> "MyContext":
        self.ctx_active = True
        return self

    def __exit__(self, *_: Any) -> None:
        self.ctx_active = False


class MinimalExampleEntrypoint(Entrypoint[Any]):
    def run(self, name: str) -> str:  # type: ignore[override]
        return f"{self.config.greeting} {name}"


def _make_cfg(**overrides: Any) -> Any:
    """Build a structured DictConfig from ExampleEntrypointConf with logging disabled."""
    return OmegaConf.structured(ExampleEntrypointConf(logging=DISABLED_LOGGING, **overrides))


# Tests


def test_entrypoint_basic() -> None:
    """Entrypoint runs and returns the expected value."""
    entrypoint = MinimalExampleEntrypoint(_make_cfg())
    assert entrypoint("you") == "Hey you"


def test_entrypoint_with_custom_greeting() -> None:
    """Config fields can be overridden."""
    entrypoint = MinimalExampleEntrypoint(_make_cfg(greeting="Hello"))
    assert entrypoint("you") == "Hello you"


def test_entrypoint_with_python_context() -> None:
    """Contexts passed as python arguments are entered and exited correctly."""
    ctx = MyContext()
    entrypoint = MinimalExampleEntrypoint(_make_cfg(), contexts=[ctx])
    entrypoint("you")
    assert ctx in entrypoint.contexts
    assert not ctx.ctx_active  # context was properly exited after __call__


def test_entrypoint_config_type_check_passes_for_subclass() -> None:
    """Config subclasses of EntrypointConf are accepted."""
    SubConf = make_config(bases=(EntrypointConf,), greeting="Sub", extra=42)
    entrypoint = MinimalExampleEntrypoint(OmegaConf.structured(SubConf(logging=DISABLED_LOGGING)))
    assert entrypoint("you") == "Sub you"


def test_entrypoint_config_type_check_passes_for_plain_dict() -> None:
    """Plain DictConfigs (e.g. from scaffold.hydra.compose) are accepted without type errors."""

    class PlainEntrypoint(Entrypoint[Any]):
        def run(self, *_: Any) -> str:
            return "ok"

    plain_cfg = OmegaConf.create({"greeting": "Hi", "logging": DISABLED_LOGGING, "verbose": False, "contexts": {}})
    assert PlainEntrypoint(plain_cfg)() == "ok"


def test_entrypoint_emits_deprecation_warning() -> None:
    """Instantiating Entrypoint emits a DeprecationWarning."""
    cfg = _make_cfg()
    with pytest.warns(DeprecationWarning, match="Entrypoint is deprecated"):
        MinimalExampleEntrypoint(cfg)


def test_time_str_generation() -> None:
    """TimerContext formats durations correctly."""
    from scaffold.ctx_manager import TimerContext

    assert "10.00 sec" == TimerContext._get_time_str(0, 10)
    assert "10.10 sec" == TimerContext._get_time_str(0, 10.099)
    assert "4 min 2.00 sec" == TimerContext._get_time_str(50, 4 * 60 + 2 + 50)
    assert "59 min 0.10 sec" == TimerContext._get_time_str(70, 10.099)
    assert "1 hours 33 min 7.00 sec" == TimerContext._get_time_str(0, 1 * 60**2 + 33 * 60 + 7)
