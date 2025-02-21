"""This module defines specific fixtures for unit tests. Shared fixtures are defined in shared_fixtures.py.

####################################
Please do not import from this file.
####################################

Not importing from conftest is a best practice described in the note here:
https://pytest.org/en/6.2.x/writing_plugins.html#conftest-py-local-per-directory-plugins
"""
import sys
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scaffold.integration_test.helpers import configure_mock
from scaffold.integration_test.shared_fixtures import *  # noqa: F401, F403


@pytest.fixture()
def absolute_test_config_dir() -> str:
    """Absolute config dir for the test configs."""
    return str((Path(__file__).parent / "scaffold" / "conf").resolve())


@pytest.fixture(scope="session")
def gpu_mock() -> None:
    """Configures a mock up of some GPU measurements"""
    configure_mock()


@pytest.fixture
def mock_wandb(monkeypatch) -> MagicMock:
    """This mocks the whole wandb module when used as a fixture."""
    mock = MagicMock()
    monkeypatch.setitem(sys.modules, "wandb", mock)
    return mock


@pytest.fixture
def mock_logger(monkeypatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr("scaffold.ctx_manager.logger", mock)
    return mock


class MockContextManager(AbstractContextManager):
    def __init__(self):
        self.enter = MagicMock()
        self.exit = MagicMock()

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit(exc_type, exc_val, exc_tb)
        # Returning False to indicate the exception should not be suppressed.
        return False
