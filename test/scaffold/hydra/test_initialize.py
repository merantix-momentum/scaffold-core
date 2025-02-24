from pathlib import Path

import hydra
import pytest
from hydra.core.global_hydra import GlobalHydra

from scaffold.hydra import initialize
from scaffold.hydra.constants import VERSION_BASE


def test_hydra_initialize() -> None:
    """test_hydra_initialize"""
    # Normal initialization
    with initialize() as instance:
        assert instance.is_initialized()

    abs_test_dir = str((Path(__file__).parent).resolve())
    with initialize(config_dir=abs_test_dir) as instance:
        assert instance.is_initialized()

    # Using existing instance
    with hydra.initialize(config_path=None, version_base=VERSION_BASE):
        hydra_instance = GlobalHydra.instance()
        assert hydra_instance.is_initialized()
        with initialize() as instance:
            assert id(instance) == id(hydra_instance)

        # Optionally also raise if there is an existing instance.
        with pytest.raises(ValueError):
            with initialize(exists_ok=False):
                pass
