from dataclasses import field
from typing import Any, Dict, List, Optional

from omegaconf import MISSING

from scaffold.hydra.config_helpers import structured_config

GROUP = "scaffold/entrypoint"


@structured_config(group=GROUP)
class EntrypointConf:
    defaults: List[Any] = field(
        default_factory=lambda: [
            {"/scaffold/entrypoint/logging@logging": "default"},
        ]
    )
    # We unfortunately have to use Any inside 'contexts' instead of e.g. ContextConf,
    # because otherwise all context configs can't add additional arguments.
    # Hydra does not allow for Union types, which would be required, of multiple types of configs should be allowed.
    # Hydra itself solves it this way too until now: https://github.com/facebookresearch/hydra/blob/796fdf1c54eabdcd5121d3a9c8ab6af70ee41763/hydra/conf/__init__.py#L142  # noqa E501
    contexts: Optional[Dict[str, Any]] = field(default_factory=lambda: {})
    logging: Dict[str, Any] = MISSING  # Same options as hydra.job_logging
    verbose: Any = False  # Same as hydra.verbose, but applied to our logging setup, instead of hydra.job_logging
