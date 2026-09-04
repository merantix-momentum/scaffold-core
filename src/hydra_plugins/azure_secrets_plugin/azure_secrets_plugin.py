"""Azure Key Vault resolver plugin.

This module automatically registers an OmegaConf resolver for Azure Key Vault
when Hydra initializes. Secrets are fetched lazily on-demand.

Usage in YAML configs:
    token: "${azure_secret:vault_name, secret_name}"
"""

from omegaconf import OmegaConf


def get_azure_secret(vault_name: str, secret_name: str) -> str:
    """Fetch a secret from Azure Key Vault.

    Args:
        vault_name: The name of the Key Vault (just the vault name, not full URL).
        secret_name: The name of the secret to retrieve.

    Returns:
        The secret value as a string.

    Raises:
        ImportError: If azure-identity or azure-keyvault-secrets is not installed.
        Exception: If the secret cannot be retrieved from Azure.
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError:
        raise ImportError(
            "azure-identity and azure-keyvault-secrets are not installed. "
            "Install them with: "
            "pip install azure-identity azure-keyvault-secrets"
        )

    vault_url = f"https://{vault_name}.vault.azure.net"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    secret = client.get_secret(secret_name)
    return secret.value


def register_azure_resolver() -> None:
    """Register the Azure Key Vault resolver with OmegaConf.

    This function is called automatically when Hydra initializes due to the
    plugin discovery mechanism.
    """
    OmegaConf.register_new_resolver("azure_secret", get_azure_secret, replace=True)


# Automatically register resolver when this module is imported
register_azure_resolver()
