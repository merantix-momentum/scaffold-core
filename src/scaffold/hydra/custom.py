"""
This module helps you managing hydra configs and running hydra sessions with configs.
Having an own runner for hydra session as a replacement for the @hydra.main annotation
is necessary since the original annotation performs parsing of argparse parameters and
running the sessions at the same time. To use e.g. click instead of argparse both aspects had to be disentangled.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hydra._internal.config_search_path_impl import ConfigSearchPathImpl
from hydra._internal.hydra import Hydra as HydraClass
from hydra._internal.utils import detect_calling_file_or_module_from_task_function, run_and_report
from hydra.core.config_store import ConfigStore
from hydra.types import TaskFunction
from omegaconf import DictConfig

logger = logging.getLogger(__name__)


def resolve_rel_config_path(a_file: str, config_path: str) -> str:
    """Returns absolute path between relative file and folder

    Args:
        a_file: Reference file path e.g. __file__
        config_path: Relative path from e.g. __file__ to config

    Returns: str with absolute path to config
    """
    a_path = os.path.dirname(os.path.realpath(a_file))
    return str((Path(a_path) / config_path).resolve())


def resolve_and_split_path(config_path: str) -> Tuple[Path, str]:
    """Check if the file exists and split the path into the directory and base name without .yaml.

    Args:
        config_path: Path to the hydra config yaml.

    Returns:
        The absolute directory name and the file path without .yaml or .yml

    Raises:
        FileNotFoundError if file does not exist
    """
    config_path = Path(config_path).resolve()

    # check if the file exists, if not there is no error, but Hydra just uses the defaults
    # defined in the config store and ignores that you gave it a non-existing config path
    if not config_path.is_file():
        raise FileNotFoundError(f"Cannot find specified config file at {config_path}")

    return config_path.parent, config_path.name.replace(".yaml", "").replace(".yml", "")


def run_with_hydra(task_function: TaskFunction, config_dir: str, config_name: str, overrides: List[str] = None) -> Any:
    """Run a function in a hydra session using the specified config.

    Args:
        task_function: Method that should be executed.
        config_path: Absolute path to config.
        overrides: List of config parameter overrides with
                   syntax https://hydra.cc/docs/next/advanced/override_grammar/basic/"

    Returns:
        Return value from task_function
    """
    from hydra.core.global_hydra import GlobalHydra

    if overrides is None:
        overrides = []

    # create a hydra session
    hydra_env = _get_hydra_env(task_function, config_dir)

    # adapted from https://github.com/facebookresearch/hydra/blob/bf1f92c49ede2db7b3e2e70a06c68c3a6b0bfe41/hydra/_internal/utils.py#L274 # noqa: E501
    ret = None
    try:
        # run task_function using hydra
        ret = run_and_report(
            lambda: hydra_env.run(config_name=config_name, task_function=task_function, overrides=overrides)
        )
    finally:
        # cleanup hydra session
        GlobalHydra.instance().clear()

    return ret.return_value


def _get_hydra_env(task_function: TaskFunction, config_dir: str) -> HydraClass:
    """Discovers provided, plugin, and global configs and bootstraps a hydra session with them.

    Args:
        task_function: File path to the yaml config file. This file path does not have to include the ".yaml" extension.
        config_dir: Absolute path to the config directory

    Returns:
        Return hydra instance
    """
    # adapted from https://github.com/facebookresearch/hydra/blob/bf1f92c49ede2db7b3e2e70a06c68c3a6b0bfe41/hydra/_internal/utils.py#L274 # noqa: E501

    # lazy imports to not slow down components that do not use hydra
    from hydra.core.plugins import Plugins
    from hydra.plugins.search_path_plugin import SearchPathPlugin

    # retrieve attributes of task_function to later name the hydra run after it
    (
        calling_file,
        calling_module,
        task_name,
    ) = detect_calling_file_or_module_from_task_function(task_function)

    # bootstrap config discovery
    search_path = ConfigSearchPathImpl()

    # add specified config based on an absolute path
    search_path.append("command-line", f"file://{config_dir}")

    # add global hydra config
    search_path.append("hydra", "pkg://hydra.conf")

    # add configs found by installed SearchPathPlugins
    search_path_plugins = Plugins.instance().discover(SearchPathPlugin)
    for spp in search_path_plugins:
        plugin = spp()
        assert isinstance(plugin, SearchPathPlugin)
        plugin.manipulate_search_path(search_path)

    # add installed schema discoveries
    search_path.append("schema", "structured://")

    # use run_and_report to execute a hydra run which returns a hydra run environment
    hydra_env = run_and_report(
        lambda: HydraClass.create_main_hydra2(task_name=task_name, config_search_path=search_path)
    )

    # INFO: Do not forget to cleanup your session with GlobalHydra.instance().clear()
    return hydra_env


def init_configstore(config_name: str, config_schema: "dataclass") -> ConfigStore:
    """Method to initialise the configstore. To be called if the entrypoint gets executed as the config file should then
    adhere to this schema.

    Args:
        config_name: Note that this name MUST be equal to the config file (without .yaml) name, otherwise Hydra doesn't
            merge the config yaml with this config store.
        config_schema: Schema dataclass definition for the config.

    Returns: None

    Raises:
        ValueError: If `config_name` contains the file extension.
    """

    if Path(config_name).suffix != "":
        raise ValueError(f"File extension must be omitted in 'config_name'. Given: {config_name}.")
    cs = ConfigStore.instance()
    dataclass_name = config_schema.__name__
    # we set the name of the dataclass as name of the top level schema
    # that means if we look at a bundle yaml, we know which dataclass defines the schema
    cs.store(name=dataclass_name, node=config_schema)
    return cs


def get_cfg_from_config_fp(
    config_fp: str,
    config_class: Optional["dataclass"] = None,  # noqa: F821
    overrides: List[str] = None,
    add_schema_funcs: Optional[List[Callable]] = None,
) -> DictConfig:
    """
    Helper function that returns a hydra config object.
    Can be used for tests or debugging and the show config command.

    Before composing the config provided in `config_fp`, all functions in `add_schema_funcs` will be called.

    IMPORTANT:
        This does not work when Hydra is already initialized

    Args:
        config_fp (str): absolute filepath to the component config (bundle).
        config_class (Optional["dataclass"]): Dataclass schema for the config.
        overrides (List[str] = None): Values in the config that should be overridden.
        add_schema_funcs (Optional[List[Callable]] = None): Functions that should be called after the
            config store is initialised. These functions can be used to add schemas to the config store
            so they can be checked against the given config file. Since these schemas can vary between
            components, every component implements these separately.

    Returns:
        The dataclass representing the config object

    Raises:
        FileNotFoundError: If specified config file does not exist.
    """
    # This function is not needed for most entrypoints, so just import the stuff we need for it lazily
    from hydra import compose, initialize_config_dir

    overrides = overrides if overrides is not None else []
    add_schema_funcs = add_schema_funcs if add_schema_funcs is not None else []

    config_dir, config_name = resolve_and_split_path(config_fp)

    with initialize_config_dir(config_dir=str(config_dir.absolute())):
        # Load the schema
        if config_class is not None:
            cs = init_configstore(config_name, config_class)
        else:
            cs = ConfigStore.instance()
        for add_schema in add_schema_funcs:
            add_schema(cs)
        cfg = compose(config_name, overrides=overrides)

    return cfg


def run_component_with_config_fp(
    run_component_func: Callable,
    config_fp: str,
    config_bundle_class: Optional["dataclass"] = None,  # noqa: F821
    overrides: List[str] = None,
    add_schema_funcs: Optional[List[Callable]] = None,
) -> Dict:
    """
    Generic entry point for an entrypoint component based on a config file path.
    This function should standardize how to instantiate the config store, the hydra environment
    and finally run the given function with the config in that environment.

    Before running the component, all functions in `add_schema_funcs` will be called which should
    add all needed schemas to the hydra config store.

    IMPORTANT:
        This call will try to instantiate a new Hydra environment, so calling this function inside an
        environment where a global Hydra instance already exists will raise an Error.
        If you want to call an entrypoint component inside an existing Hydra state (i.e. in another project
        that also used hydra), please try to load the needed configs for that component manually.

    Args:
        run_component_func (Callable): Component function that takes a config instance.
        config_fp (str): absolute filepath to the component config (bundle).
        config_bundle_class (Optional["dataclass"]): Dataclass schema for the config.
        overrides (List[str] = None): Values in the config that should be overridden.
        add_schema_funcs (Optional[List[Callable]] = None): Functions that should be called after the
            config store is initialised. These functions can be used to add schemas to the config store
            so they can be checked against the given config file. Since these schemas can vary between
            components, every component implements these separately.

    Returns:
        Return value of the run_component_func
    """
    overrides = overrides if overrides is not None else []
    add_schema_funcs = add_schema_funcs if add_schema_funcs is not None else []

    config_dir, config_name = resolve_and_split_path(config_fp)
    if config_bundle_class is not None:
        cs = init_configstore(config_name, config_bundle_class)
    else:
        cs = ConfigStore.instance()
    for add_schema in add_schema_funcs:
        add_schema(cs)

    return run_with_hydra(run_component_func, str(config_dir), config_name, overrides)
