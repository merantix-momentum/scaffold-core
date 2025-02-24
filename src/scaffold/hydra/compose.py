import warnings
from copy import deepcopy
from functools import reduce
from inspect import isclass
from typing import List, Optional, Union

import hydra
from hydra.core.config_store import ConfigStore
from omegaconf import DictConfig, OmegaConf

import scaffold
from scaffold.hydra.config_helpers import StructuredConfig

CONFIG_STORE = ConfigStore.instance()


def _compose_path(
    config_path: str,
    config_dir: Optional[str] = None,
    overrides: Optional[List[str]] = None,
    return_hydra_config: bool = False,
) -> DictConfig:
    """Initialized hydra if needed and composes a config from the config store, either yaml of structured config."""
    with scaffold.hydra.initialize(config_dir=config_dir):
        return hydra.compose(
            config_path.lstrip("/"), overrides=overrides or [], return_hydra_config=return_hydra_config
        )


def _instance_warning(config: StructuredConfig) -> None:
    """Trigger a warning if a StructuredConfig instance is passed."""
    if isinstance(config, StructuredConfig) and config != config.__class__():
        warnings.warn(
            "Instantiating a structured config with different argument has no effect on composition!"
            "The reason is that defaults list and dataclass fields behave differently during instantiation."
            f" Will compose {config.__class__.__name__} class with default values."
        )


def compose(
    config_name_or_class: Union[str, StructuredConfig],
    config_dir: Optional[str] = None,
    overrides: Optional[List[str]] = None,
    return_hydra_config: bool = False,
    check_missing: Optional[bool] = False,
    return_leaf: Optional[bool] = True,
) -> DictConfig:
    """Alternative for hydra.compose, which differs in the following ways:

    1. No need to call `hydra.initialize` before composing a config, since this will use `scaffold.hydra.initialize`
       internally, which uses an existing instance if available.
    2. Is able to compose a config from a `StructuredConfig` class, which does not require the user to know the path
       in the config store, where the structured config was registered.
    3. Can check for missing values right away, instead of throwing an exception when trying to access them.
    4. Can automatically return the leaf node of the given config. When calling the original
       hydra.compose("/my/grouped/config"), this results in a config with the keys config["my"]["group"][...].
       Setting return_leaf=True, scaffold.hydra.compose will automatically return the result of config["my"]["group"]
       instead of adding all group keys.

    Args:
        config_name_or_class (Union[str, StructuredConfig]): Path to the config in the config store, or StructuredConfig
            class. Passing an instance of StructuredConfig has the same effect, but will throw a warning if the instance
            arguments are not the same as the default ones.
        config_dir (Optional[str] = None): Optional absolute config directory to add to the search path.
        overrides (List[str] = None): Hydra overrides. See https://hydra.cc/docs/advanced/override_grammar/basic/.
        return_hydra_config (bool = False): If True, returns the hydra in the root of the config.
        check_missing (Optional[bool] = False): If True, will throw an exception if omegaconf.MISSING or '???' values
            are present.
        return_leaf (Optional[bool] = True): If True, will return the leaf node of the config path inside the config
            store, so compose("/my/grouped/config") will return only the values in the "config" node or yaml, without
            still containing the group keys in the returned config.

    Returns:
        Rendered DictConfig.
    """
    _config = deepcopy(config_name_or_class)
    compose_args = dict(config_dir=config_dir, overrides=overrides or [], return_hydra_config=return_hydra_config)

    if isinstance(_config, str):
        _config = _compose_path(_config, **compose_args)
    elif isinstance(config_name_or_class, StructuredConfig) or (
        isclass(_config)  # The separate isclass check is unfortunately needed.
        and issubclass(_config, StructuredConfig)
    ):
        _instance_warning(_config)
        store_path = _config.get_store_path()  # This is a class method, not an instance method
        _config = _compose_path(store_path, **compose_args)
    else:
        raise ValueError(f"Expected config to be of type Union[str, StructuredConfig], but got {type(_config)}.")

    if return_leaf:
        if isinstance(config_name_or_class, str):
            parent_keys = config_name_or_class.strip("/").split("/")[:-1]
        else:
            # Will result in an empty list, if the store path is just "MyConfig" and has not parents.
            parent_keys = config_name_or_class.get_store_path().split("/")[:-1]

        # Index through all levels (e.g. ["scaffold", "entrypoint", ...]) and returns the last result
        _config = reduce(DictConfig.get, parent_keys, _config)
        # Detach from original root, so that exceptions for missing values appear relative to the leaf.
        _config = DictConfig(OmegaConf.to_container(_config))

    if check_missing:
        # This triggers omegaconf.errors.MissingMandatoryValue for MISSING values.
        OmegaConf.to_object(_config)

    return _config
