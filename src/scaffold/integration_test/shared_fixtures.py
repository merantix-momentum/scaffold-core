"""This module defines shared fixtures that can be used inside a conftest.py like this

from scaffold.integration_test.shared_fixtures import *  # noqa: F401, F403

These fixtures will then be shared with the tests under the scope of the conftest.py.

This is useful for splitting unit and integration tests and defining separate conftest files.
Specific fixtures for integration or unit tests can then be defined in the respective conftest.
"""
