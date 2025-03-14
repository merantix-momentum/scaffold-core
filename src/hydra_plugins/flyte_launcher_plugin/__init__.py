import importlib
import logging

if importlib.util.find_spec("flytekit") is None:
    # if we cannot import flyte, importing flyte_launcher throws and error and we assume that
    # in that case we do not want to have the plugin available at all.
    # this ensure users who did not install flyte extra and dont need this plugin do not get
    # a confusing error message (which could be ignored anyway)
    logging.getLogger(__name__).warning("Could not import flytekit. Hydra flyte launcher plugin disabled")
    __all__ = []
else:
    # from . import  as flyte_launcher
    from . import _flyte_launcher as flyte_launcher
    from ._flyte_launcher import FlyteLauncher

    __all__ = [flyte_launcher, FlyteLauncher]
