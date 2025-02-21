import os
from contextlib import contextmanager
from typing import Iterator, Optional

import hydra
from hydra.core.global_hydra import GlobalHydra

from scaffold.hydra.constants import VERSION_BASE


@contextmanager
def initialize(
    config_dir: Optional[str] = None, job_name: Optional[str] = "app", exists_ok: Optional[bool] = True
) -> Iterator[GlobalHydra]:
    """Context manager, that either uses an existing hydra instance, or initializes one temporarily.

    Args:
        config_dir (Optional[str]): Absolute directory that should be added to the search path.
        job_name (Optional[str]): hydra.job.name which should be set.
        exists_ok (Optional[bool]): Do not fail if hydra is already initialized and yield GlobalHydra.instance().
    """
    if config_dir is not None and not os.path.isabs(config_dir):
        raise ValueError("scaffold.hydra.initialize() requires an absolute config_dir!")
    if GlobalHydra.instance().is_initialized():
        if exists_ok:
            yield GlobalHydra.instance()
        else:
            raise ValueError(
                "GlobalHydra is already initialized, call GlobalHydra.instance().clear() if you want to re-initialize, "
                "or set scaffold.hydra.initialize(exist_ok=True) to return the current instance."
            )
    else:
        if config_dir is not None:
            with hydra.initialize_config_dir(config_dir=config_dir, job_name=job_name, version_base=VERSION_BASE):
                yield GlobalHydra.instance()
        else:
            with hydra.initialize(config_path=None, job_name=job_name, version_base=VERSION_BASE):
                yield GlobalHydra.instance()
