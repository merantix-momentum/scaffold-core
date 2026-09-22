import re
import typing as t

from omegaconf import DictConfig, ListConfig, OmegaConf

MASKED_VALUE = "***MASKED***"

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(secret|token|password|passwd|credential|api[_-]?key|private[_-]?key|access[_-]?key)",
    flags=re.IGNORECASE,
)
_SECRET_RESOLVER_PATTERN = re.compile(r"\$\{\s*(aws_secret|azure_secret|gcp_secret)\s*:", flags=re.IGNORECASE)


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_PATTERN.search(key))


def _looks_like_secret_resolver(value: t.Any) -> bool:
    return isinstance(value, str) and bool(_SECRET_RESOLVER_PATTERN.search(value))


def _mask_node(node: t.Any, parent_key: t.Optional[str] = None) -> t.Any:
    if isinstance(node, dict):
        return {k: _mask_node(v, parent_key=k) for k, v in node.items()}

    if isinstance(node, list):
        return [_mask_node(v, parent_key=parent_key) for v in node]

    if (parent_key is not None and _is_sensitive_key(parent_key)) or _looks_like_secret_resolver(node):
        return MASKED_VALUE

    return node


def mask_sensitive_config(cfg: t.Any) -> t.Any:
    """Return a copy of cfg with sensitive values masked for safe logging/registration.

    DictConfig/ListConfig are converted with resolve=False to avoid resolving resolvers
    while preparing telemetry or metadata payloads.
    """
    if isinstance(cfg, (DictConfig, ListConfig)):
        cfg = OmegaConf.to_container(cfg, resolve=False)

    return _mask_node(cfg)
