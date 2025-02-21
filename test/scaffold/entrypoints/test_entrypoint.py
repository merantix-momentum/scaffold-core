import hydra
from hydra.core.global_hydra import GlobalHydra

from scaffold.hydra.constants import VERSION_BASE
from scaffold.integration_test.helpers import ExampleEntrypointConf, MinimalExampleEntrypoint, MyContext

REL_CONFIG_PATH = "../conf/"
ENTRYPOINT_CONFIG = "test_entrypoint_config"
ENTRYPOINT_CONFIG_CONTEXTS = "test_entrypoint_config_with_contexts"


def test_entrypoint_with_hydra_yaml() -> None:
    """User uses hydra main for constructing the config."""
    with hydra.initialize(config_path=REL_CONFIG_PATH):
        config: ExampleEntrypointConf = hydra.compose(config_name=ENTRYPOINT_CONFIG)
        entrypoint = MinimalExampleEntrypoint(config)
        out = entrypoint("you")
        assert out == "Hey from yaml you"


def test_entrypoint_with_hydra_yaml_and_python_context() -> None:
    """User uses hydra main for constructing the config, and pass ctx from python."""
    with hydra.initialize(config_path=REL_CONFIG_PATH, version_base=VERSION_BASE):
        config: ExampleEntrypointConf = hydra.compose(config_name=ENTRYPOINT_CONFIG)
        entrypoint = MinimalExampleEntrypoint(config, contexts=[MyContext()])
        out = entrypoint("you")
        assert out == "Hey from yaml you"
        mycontext = entrypoint.contexts[-1]
        assert not mycontext.ctx_active


def test_entrypoint_with_hydra_yaml_and_yaml_context() -> None:
    """User uses hydra main for constructing the config, including a context yaml config."""
    with hydra.initialize(config_path=REL_CONFIG_PATH, version_base=VERSION_BASE):
        config: ExampleEntrypointConf = hydra.compose(config_name=ENTRYPOINT_CONFIG_CONTEXTS)
        entrypoint = MinimalExampleEntrypoint(config)
        out = entrypoint("you")
        assert out == "Hey from yaml and with specified context you"
        mycontext = entrypoint.contexts[-1]
        assert not mycontext.ctx_active


def test_entrypoint_from_config_name_or_class(absolute_test_config_dir: str) -> None:
    """Constructing the configs from dataclasses"""
    entrypoint = MinimalExampleEntrypoint.from_config_name_or_class(ExampleEntrypointConf)
    assert entrypoint("you") == "Hey you"
    assert not GlobalHydra.instance().is_initialized()

    # The absolute path is only needed if the config name can't be found in existing dirs,
    # e.g. added through search path plugins
    entrypoint = MinimalExampleEntrypoint.from_config_name_or_class(
        ENTRYPOINT_CONFIG, config_dir=absolute_test_config_dir
    )
    assert entrypoint("you") == "Hey from yaml you"
    assert not GlobalHydra.instance().is_initialized()

    # If hydra is already initialized, .from_config_name composes the config using this global hydra instance.
    with hydra.initialize(config_path=REL_CONFIG_PATH, version_base=VERSION_BASE):
        entrypoint = MinimalExampleEntrypoint.from_config_name_or_class(ExampleEntrypointConf)
        assert entrypoint("you") == "Hey you"

        entrypoint = MinimalExampleEntrypoint.from_config_name_or_class(ENTRYPOINT_CONFIG)
        assert entrypoint("you") == "Hey from yaml you"


def test_time_str_generation() -> None:
    """Test if we display the time delta correctly with TimerContext"""
    from scaffold.ctx_manager import TimerContext

    assert "10.00 sec" == TimerContext._get_time_str(0, 10)
    assert "10.10 sec" == TimerContext._get_time_str(0, 10.099)
    assert "4 min 2.00 sec" == TimerContext._get_time_str(50, 4 * 60 + 2 + 50)
    assert "59 min 0.10 sec" == TimerContext._get_time_str(70, 10.099)
    assert "1 hours 33 min 7.00 sec" == TimerContext._get_time_str(0, 1 * 60**2 + 33 * 60 + 7)
