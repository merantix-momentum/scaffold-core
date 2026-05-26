import importlib.util
from typing import Any

from hydra.core.config_store import ConfigStore
from hydra_zen import ZenStore

scaffold_store = ZenStore(name="scaffold")
legacy_scaffold_store = ZenStore(name="scaffold_legacy")


def add_if_not_exists(store: ZenStore, cfg_object: Any, group: str, name: str):
    """Add a config to the store if it doesn't already exist.
    Args:
        store: the ZenStore to add to
        cfg_object: the config object to add
        group: the Hydra config group to add to
        name: the name of the config within the group
    """
    cs = ConfigStore.instance()
    try:
        cs.list(group)
        if f"{name}.yaml" not in cs.list(group):
            store(cfg_object, group=group, name=name)
    except (KeyError, IOError):
        # group doesn't exist yet, safe to add
        store(cfg_object, group=group, name=name)


def register_all() -> None:
    """Import all scaffold conf modules (triggering store() calls) then flush to hydra's ConfigStore."""
    from scaffold.conf.scaffold import artifact_manager  # noqa: F401
    from scaffold.conf.scaffold import ctx_manager  # noqa: F401
    from scaffold.conf.scaffold import (  # noqa E501 NOTE: This module is deprecated and will be removed in a future release!; noqa: F401
        entrypoint,
    )

    if importlib.util.find_spec("flytekit") is not None:
        from scaffold.conf.scaffold import flyte_launcher  # noqa: F401

    if importlib.util.find_spec("lightning") is not None:
        from scaffold.conf.scaffold.lightning import callbacks  # noqa: F401

    scaffold_store.add_to_hydra_store(overwrite_ok=True)

    from scaffold.conf.scaffold.flyte_launcher import FlyteLauncherConf
    from scaffold.flyte.launcher_conf import FlyteWorkflowConf

    # to maintain backwards compatibility, add legacy configs to the store if they were not set by the user already
    add_if_not_exists(legacy_scaffold_store, FlyteLauncherConf, "hydra/launcher", "flyte")
    add_if_not_exists(legacy_scaffold_store, FlyteWorkflowConf, "scaffold/flyte_launcher", "FlyteWorkflowConfig")

    legacy_scaffold_store.add_to_hydra_store(overwrite_ok=True)
