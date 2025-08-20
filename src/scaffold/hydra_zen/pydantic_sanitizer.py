from typing import Any, Mapping, Sequence, Callable
from omegaconf import OmegaConf, DictConfig, ListConfig
from hydra_zen.third_party.pydantic import pydantic_parser

def _to_plain(obj: Any) -> Any:
    """
    Recursively convert OmegaConf containers into plain Python containers.
    Leaves non-container objects unchanged.
    """
    if isinstance(obj, (DictConfig, ListConfig)):
        # Convert and resolve interpolations; handles nested DictConfig/ListConfig
        return OmegaConf.to_container(obj, resolve=True)
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        return type(obj)(_to_plain(v) for v in obj)
    return obj

def sanitized_pydantic_parser(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Compose a sanitizer with hydra-zen's pydantic_parser.
    The sanitizer runs first on args/kwargs, then pydantic_parser handles validation.
    """
    base_wrapper = pydantic_parser(fn)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        clean_args = tuple(_to_plain(a) for a in args)
        clean_kwargs = {k: _to_plain(v) for k, v in kwargs.items()}
        return base_wrapper(*clean_args, **clean_kwargs)

    return wrapper
