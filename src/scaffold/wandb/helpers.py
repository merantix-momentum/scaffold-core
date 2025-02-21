import json
import logging
import os

import wandb

WANDB_SECRET = "wandb-access-secret"
WANDB_KEY = "key_map"

logger = logging.getLogger(__name__)


def wandb_environment_setup(username: str) -> None:
    """
    Retrieve wandb login secrets secrets and export them as environment variables.
    This is a convenience function for our Flyte setup to be called before `wandb.init()`.

    If this function is called in local setup, i.e. outside of flyte task context, it will not do anything.

    Args:
        username (str): WandB user handle for look up of API key
    """
    # locally authentication should already be setup
    if wandb.api.api_key is None and "WANDB_API_KEY" not in os.environ.keys():
        # in a cloud context the secret containing the mapping usernames <> API-key should be accessible
        try:
            import flytekit

            secret_val = flytekit.current_context().secrets.get(WANDB_SECRET, WANDB_KEY)
            mapping = json.loads(secret_val)
            logger.info(f"Usernames found in the cloud: {list(mapping.keys())}")
            os.environ["WANDB_API_KEY"] = mapping[username]
        except (ModuleNotFoundError, ValueError):
            logger.warning(
                f"Could not retrieve secret: {WANDB_SECRET} {WANDB_KEY}\nNot changing setup - if wandb "
                f"authentication is an issue, please ensure the secret is made accessible. If you are executing "
                "locally, please set up the wandb environment variables manually."
            )
