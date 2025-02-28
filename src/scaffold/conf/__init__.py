import importlib.util


def register_all() -> None:
    """All @structured_config classes register themselves when imported / defined"""
    from scaffold.conf.scaffold import artifact_manager  # noqa:F401
    from scaffold.conf.scaffold import entrypoint  # noqa:F401

    try:
        if importlib.util.find_spec("flytekit") is not None:
            from scaffold.conf.scaffold import flyte_launcher  # noqa:F401
    except ModuleNotFoundError:
        # in case we didnt install flyte extra package
        pass
