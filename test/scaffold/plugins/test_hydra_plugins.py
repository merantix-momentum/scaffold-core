"""Adapted from https://github.com/facebookresearch/hydra/blob/main/examples/plugins/example_searchpath_plugin/tests/test_example_search_path_plugin.py"""  # noqa: E501
import subprocess
from pathlib import Path

import pytest
from hydra import initialize
from hydra.core.global_hydra import GlobalHydra
from hydra.core.plugins import Plugins
from hydra.plugins.launcher import Launcher
from hydra.plugins.search_path_plugin import SearchPathPlugin

from hydra_plugins.flyte_launcher_plugin.flyte_launcher import FlyteLauncher
from hydra_plugins.scaffold_searchpath_plugin.scaffold_searchpath_plugin import ScaffoldSearchPathPlugin


def test_discovery() -> None:
    """Tests that plugins can be discovered via the plugins subsystem when looking at all Plugins"""
    assert ScaffoldSearchPathPlugin.__name__ in [x.__name__ for x in Plugins.instance().discover(SearchPathPlugin)]
    assert FlyteLauncher.__name__ in [x.__name__ for x in Plugins.instance().discover(Launcher)]


def test_config_installed() -> None:
    """Tests if the scaffold configs are correctly added to the config store."""
    with initialize(config_path=None):
        config_loader = GlobalHydra.instance().config_loader()
        assert "ArtifactManagerConf" in config_loader.get_group_options("scaffold/artifact_manager")
        assert "EntrypointConf" in config_loader.get_group_options("scaffold/entrypoint")
        assert "FlyteWorkflowConfig" in config_loader.get_group_options("scaffold/flyte_launcher")


def test_flyte_config_installed() -> None:
    """Tests if the flyte related configs are correctly added to the config store."""
    with initialize(config_path=None):
        config_loader = GlobalHydra.instance().config_loader()
        assert "FlyteDockerImageConfig" in config_loader.get_group_options("scaffold/flyte_launcher")
        assert "FlyteWorkflowConfig" in config_loader.get_group_options("scaffold/flyte_launcher")


def test_hydra_plugin_available() -> None:
    """Tests it the 'ScaffoldSearchPathPlugin' got registered. Test only makes sense if the package got installed."""
    dir = Path(__file__).parent.absolute()
    result = subprocess.check_output(f"python3 {dir / 'dummy_main.py'} -i plugins all", shell=True, text=True)
    assert "ScaffoldSearchPathPlugin" in result
    assert "FlyteLauncher" in result


@pytest.mark.parametrize(
    "config_name",
    [
        "scaffold/flyte_launcher/FlyteDockerImageConfig",
        "scaffold/flyte_launcher/FlyteWorkflowConfig",
        "scaffold/entrypoint/EntrypointConf",
    ],
)
def test_config_store_available_through_plugin(config_name: str) -> None:
    """Tests if we can reach configs in added config store groups.
    The config store might not be reachable when scaffold.conf is not imported properly.
    """
    dir = Path(__file__).parent.absolute()
    result = subprocess.check_output(
        f"python3 {dir / 'dummy_main.py'} --config-name {config_name} -i config",
        shell=True,
        text=True,
    )
    # Displays in the default list
    assert config_name in result
