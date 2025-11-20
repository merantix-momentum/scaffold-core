from __future__ import annotations

import functools
from abc import abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from types import MethodType
from typing import Any, Callable, Dict, List, Optional, Type

from hydra.core.config_store import ConfigStore
from omegaconf import DictConfig, OmegaConf

CONFIG_STORE = ConfigStore.instance()


def check_cfg_for_missing_values(allowed_missing: Optional[List[str]] = None):
    """
    Decorator function that ensures we have no entries with MISSING values.

    It checks entries to see if they have not been overwritten via YAML or CLI.
    Entries ending with logging, like the entry that is part of the EntrypointConf, are not checked.

    Usage:
    >>> @hydra.main(
    ...     config_name="my_config",
    ... )
    ... @check_cfg_for_missing_values(['myconfig.subconfig_tree.this_entry_may_be_missing'])
    ... def main(cfg: DictConfig) -> None:
    ...     pass
    """

    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(cfg: DictConfig, **kwargs: Any) -> Any:
            missing = OmegaConf.missing_keys(cfg)
            missing = [itm for itm in missing if not itm.endswith("logging")]
            if allowed_missing is not None:
                missing = [itm for itm in missing if itm not in allowed_missing]
            if len(missing) > 0:
                raise ValueError(
                    f"Entries in the config have missing values without being explicitly allowed: ({missing}\nPlease "
                    f'either set value for them in the yaml files or via CLI or add them to the list "allowed_missing")'
                )
            return func(cfg, **kwargs)

        return wrapper

    return decorator


class StructuredConfig:
    @classmethod
    @abstractmethod
    def get_store_args(cls: Type[StructuredConfig]) -> Dict[str, str]:
        """Returns the arguments used to store this dataclass in the config store."""
        ...

    @classmethod
    @abstractmethod
    def get_store_path(cls: Type[StructuredConfig]) -> str:
        """Returns the path to the node of the StructuredConfig inside the config store."""
        ...


def _add_structured_config_base(cls: "dataclass", store_args: dict) -> type:
    """Dynamically add StructuredConfig as a base to dataclass.

    This is done, because the scaffold.hydra.compose() method needs to know the config store location of the dataclass.
    Additionally this only requires the user to use @structured_config without inheriting from StructuredConfig.

    You are then able to compose a structured config after importing in python, without knowing its config store
    position.
    >>> from scaffold.hydra import compose
    >>> config = compose(MyStructuredConfig, overrides=[...])

    Args:
        store_args (Dict): Arguments for the config store location.

    Returns:
        New class with base StructuredConfig.
    """
    _store_args = deepcopy(store_args)

    def get_store_args(cls: StructuredConfig) -> Dict[str, str]:
        """Returns the arguments used to store this dataclass in the config store."""
        return deepcopy(_store_args)

    def get_store_path(cls: StructuredConfig) -> str:
        """Returns the path to the node of the StructuredConfig inside the config store."""
        _args = cls.get_store_args()
        if _args["group"] is None:
            return _args["name"]
        return str(Path(_args["group"], _args["name"]))

    cls.get_store_args = MethodType(get_store_args, cls)
    cls.get_store_path = MethodType(get_store_path, cls)

    # Add StructuredConfig as base. Inheritance order from right to left.
    # Also making sure that the resulting class is still attached to the original module.
    cls = type(cls.__name__, (cls, StructuredConfig), {"__module__": cls.__module__})
    return cls


def structured_config(
    _cls: Optional[Type] = None,
    name: Optional[str] = None,
    group: Optional[str] = None,
    package: Optional[str] = None,
    provider: Optional[str] = None,
    frozen: bool = False,
) -> Callable:
    """Decorator which extends the @dataclass in the following ways:
    1. Adds the decorated class to the config store with reasonable defaults for
       name (class name) and provider (python package)
    2. Adds the base type StructuredConfig to the class
    3. Adds a class method get_store_args() which can be used to get the store location from the class.

    NOTE: The decorated class is only registered, if the module containing it is imported!

    Example:
        >>> @structured_config
            class MyRootConfig()
                ...
        >>> @structured_config(group="my/group")
            class MyGroupConfig()
                ...

    Args:
        name (Optional[str]): Name of the config node. By default the class.__name__.
        group (Optional[str]): Config group, subgroup separator is '/'. If None, will be placed in the root.
        package (Optional[str]): Config package, which specifies where the config is applied.
            By default, this is derived from the group ("my/group" -> my.group)
        provider (Optional[str]): The name of the module/app providing this config.
            Helps debugging. By default this is set to the python module of the structured_config.
        frozen (Optional[bool]): Whether the dataclass should be read only.

    Returns:
        Class decorator.
    """

    @wraps(_cls, updated=())  # See wraps use for classes https://stackoverflow.com/a/65470430
    def struct_config_decorator(cls: type) -> type:
        dataclass_decorator = dataclass(frozen=frozen)
        cls = dataclass_decorator(cls)

        # When using "/group" hydra adds an empty key as a first level ["", "group"].
        # To keep things consistent, we always want to use the first group as the first key.
        _group = group.strip("/") if group is not None else group
        store_args = dict(
            name=name or cls.__name__,
            group=_group,
            package=package,
            provider=provider or cls.__module__,
        )

        cls = _add_structured_config_base(cls, store_args)

        # Note: node class for hydra store needs to be set after class extension with _add_structured_config_base
        store_args["node"] = cls

        CONFIG_STORE.store(**store_args)

        return cls

    # Decorator either used as @structured_config or @structured_config()
    return struct_config_decorator(_cls) if _cls else struct_config_decorator
