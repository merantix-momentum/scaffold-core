import importlib.util

from hydra_zen import store


def register_all() -> None:
    """Import all scaffold conf modules (triggering store() calls) then flush to hydra's ConfigStore."""
    from scaffold.conf.scaffold import artifact_manager  # noqa: F401
    from scaffold.conf.scaffold import ctx_manager  # noqa: F401

    if importlib.util.find_spec("flytekit") is not None:
        from scaffold.conf.scaffold import flyte_launcher  # noqa: F401

    if importlib.util.find_spec("lightning") is not None:
        from scaffold.conf.scaffold.lightning import callbacks  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
