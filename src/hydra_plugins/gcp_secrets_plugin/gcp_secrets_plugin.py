"""GCP Secret Manager resolver plugin.

This module automatically registers an OmegaConf resolver for GCP Secret Manager
when Hydra initializes. Secrets are fetched lazily on-demand.

Usage in YAML configs:
    api_key: "${gcp_secret:project_id/secret_name, key_name}"
"""
import json
from typing import Optional

from omegaconf import OmegaConf


def get_gcp_secret(secret_name: str, key: Optional[str] = None) -> str:
    """Fetch a secret from GCP Secret Manager.

    Args:
        secret_name: The name of the secret (format: "project_id/secret_name" or
                     "projects/project_id/secrets/secret_name/versions/latest").
        key: Optional key if the secret is JSON. If provided, returns the value
             for that key from the JSON secret string.

    Returns:
        The secret value as a string.

    Raises:
        ImportError: If google-cloud-secret-manager is not installed.
        ValueError: If the secret format is invalid or secret is not valid JSON.
        Exception: If the secret cannot be retrieved from GCP.
    """
    try:
        from google.cloud import secretmanager
    except ImportError:
        raise ImportError(
            "google-cloud-secret-manager is not installed. "
            "Install it with: pip install google-cloud-secret-manager"
        )

    # Handle both short format (project/secret) and full format
    if secret_name.startswith("projects/"):
        resource_name = secret_name
    else:
        # Extract project and secret from simplified format
        parts = secret_name.split("/")
        if len(parts) == 2:
            project_id, secret_id = parts
            resource_name = (
                f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            )
        else:
            raise ValueError(
                f"Invalid GCP secret format: {secret_name}. "
                f"Use 'project_id/secret_name' or full resource name."
            )

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": resource_name})

    secret_str = response.payload.data.decode("UTF-8")

    if key:
        try:
            secret_dict = json.loads(secret_str)
            return secret_dict.get(key, "")
        except json.JSONDecodeError:
            raise ValueError(
                f"Secret '{secret_name}' is not valid JSON. "
                f"Cannot extract key '{key}'."
            )

    return secret_str


def register_gcp_resolver() -> None:
    """Register the GCP Secret Manager resolver with OmegaConf.

    This function is called automatically when Hydra initializes due to the
    plugin discovery mechanism.
    """
    OmegaConf.register_new_resolver("gcp_secret", get_gcp_secret, replace=True)


# Automatically register resolver when this module is imported
register_gcp_resolver()
