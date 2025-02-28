import importlib.util


def register_all() -> None:
    """All @structured_config classes register themselves when imported / defined"""
    from scaffold.conf.scaffold import artifact_manager  # noqa:F401
    from scaffold.conf.scaffold import entrypoint  # noqa:F401

    if importlib.util.find_spec("flytekit") is not None:
        # only import in case we installed flyte extra package
        from scaffold.conf.scaffold import flyte_launcher  # noqa:F401
