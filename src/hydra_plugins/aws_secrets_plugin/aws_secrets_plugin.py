"""AWS Secrets Manager resolver plugin.

This module automatically registers an OmegaConf resolver for AWS Secrets Manager
when Hydra initializes. Secrets are fetched lazily on-demand.

Usage in YAML configs:
    password: "${aws_secret:secret_name, key_name}"
"""
import json
from typing import Optional

from omegaconf import OmegaConf


def get_aws_secret(secret_id: str, key: Optional[str] = None) -> str:
    """Fetch a secret from AWS Secrets Manager.

    Args:
        secret_id: The name or ARN of the secret in Secrets Manager.
        key: Optional key if the secret is JSON. If provided, returns the value
             for that key from the JSON secret string.

    Returns:
        The secret value as a string.

    Raises:
        ImportError: If boto3 is not installed.
        Exception: If the secret cannot be retrieved from AWS.
    """
    try:
        import boto3
    except ImportError:
        raise ImportError(
            "boto3 is not installed. Install it with: pip install boto3"
        )

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_id)

    secret_str = response.get("SecretString") or response.get("SecretBinary", "")

    if key:
        try:
            secret_dict = json.loads(secret_str)
            return secret_dict.get(key, "")
        except json.JSONDecodeError:
            raise ValueError(
                f"Secret '{secret_id}' is not valid JSON. "
                f"Cannot extract key '{key}'."
            )

    return secret_str


def register_aws_resolver() -> None:
    """Register the AWS Secrets Manager resolver with OmegaConf.

    This function is called automatically when Hydra initializes due to the
    plugin discovery mechanism.
    """
    OmegaConf.register_new_resolver("aws_secret", get_aws_secret, replace=True)


# Automatically register resolver when this module is imported
register_aws_resolver()
