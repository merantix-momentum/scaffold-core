import logging


def register_fsspec_to_aim():
    logger = logging.getLogger(__name__)
    try:
        import fsspec
        from aim.storage.artifacts.artifact_registry import registry
    except ImportError:
        logger.warning(
            "It seems that aim_utils or fsspec are not installed. "
            "Skipping registering fsspec to aim_utils's artifact manager."
        )
        return  # if aim_utils or fsspec are not installed, do nothing
    from scaffold.aim_utils.fsspec_artifact_storage import FsspecArtifactStorage

    for protocol in fsspec.available_protocols():
        if protocol in registry.registry:  # only register if not already supported
            # since this functionality was added to explicitly support Google Cloud Storage, warn when aim supports GCS.
            if protocol == "gs":
                logger.warning(
                    "Aim now supports GCS. "
                    "Calling register_fsspec_to_aim is no longer needed for GCS support. "
                    "Skipping registering."
                )
            continue
        registry.register(protocol, FsspecArtifactStorage)
