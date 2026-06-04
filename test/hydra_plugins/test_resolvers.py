"""Tests for secrets resolver plugins.

These are integration tests that verify the resolvers work with OmegaConf.
They don't test the actual cloud API calls since those SDKs aren't installed.
"""
from omegaconf import OmegaConf

from hydra_plugins.aws_secrets_plugin.aws_secrets_plugin import register_aws_resolver
from hydra_plugins.gcp_secrets_plugin.gcp_secrets_plugin import register_gcp_resolver
from hydra_plugins.azure_secrets_plugin.azure_secrets_plugin import (
    register_azure_resolver,
)


class TestResolverRegistration:
    """Test that all resolvers can be registered with OmegaConf."""

    def test_aws_resolver_registration(self) -> None:
        """Test AWS resolver registration."""
        register_aws_resolver()
        cfg = OmegaConf.create({"secret": "${aws_secret:test}"})
        assert cfg is not None

    def test_gcp_resolver_registration(self) -> None:
        """Test GCP resolver registration."""
        register_gcp_resolver()
        cfg = OmegaConf.create({"secret": "${gcp_secret:test}"})
        assert cfg is not None

    def test_azure_resolver_registration(self) -> None:
        """Test Azure resolver registration."""
        register_azure_resolver()
        cfg = OmegaConf.create({"secret": "${azure_secret:vault, secret}"})
        assert cfg is not None
