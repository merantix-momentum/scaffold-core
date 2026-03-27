from hydra_zen import make_config, store

from scaffold.ctx_manager import (  # noqa: F401
    DEFAULT_LOGGING,
    DISABLED_LOGGING,
    NONE_LOGGING,
    STDOUT_AND_LOGFILE_LOGGING,
    STDOUT_LOGGING,
)

GROUP = "scaffold/entrypoint"

# Deprecated: use hydra-zen builds()/store() directly for your own configs.
EntrypointConf = make_config(
    # We unfortunately have to use Any inside 'contexts' instead of e.g. ContextConf,
    # because otherwise all context configs can't add additional arguments.
    contexts={},
    logging=DEFAULT_LOGGING,  # Same options as hydra.job_logging; override per logging variant
    verbose=False,  # Same as hydra.verbose, but applied to our logging setup
)
store(EntrypointConf, group=GROUP, name="EntrypointConf")
