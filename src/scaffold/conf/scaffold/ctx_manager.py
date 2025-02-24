import typing as t
from dataclasses import field

from omegaconf import MISSING

from scaffold.hydra.config_helpers import structured_config


@structured_config(group="ctx_manager")
class ContextConfig:
    _target_: str = MISSING


@structured_config(group="ctx_manager")
class WandBContextConfig(ContextConfig):
    _target_: str = "scaffold.ctx_manager.WandBContext"
    base_url: str = MISSING
    project: str = MISSING
    entity: str = "mxm"
    group: t.Optional[str] = None
    job_type: t.Optional[str] = None
    tags: t.Optional[t.List[str]] = None
    name: t.Optional[str] = None
    notes: t.Optional[str] = None
    run_id: t.Optional[str] = None
    user: t.Optional[str] = None
    resume: bool = False


@structured_config(group="ctx_manager")
class LoggingContextConfig(ContextConfig):
    defaults: t.List[t.Any] = field(
        default_factory=lambda: [
            {"scaffold/entrypoint/logging@log_config": "default"},
        ]
    )

    _target_: str = "scaffold.ctx_manager.LoggingContext"
    log_config: t.Dict[str, t.Any] = MISSING  # Same options as hydra.job_logging
    verbose: t.Any = False  # Same as hydra.verbose, but applied to our logging setup, instead of hydra.job_logging
