from typing import Optional

from omegaconf import MISSING

from scaffold.conf.scaffold.artifact_manager import ArtifactManagerConf
from scaffold.hydra.config_helpers import structured_config

GROUP = "scaffold/lightning/checkpointer"


@structured_config(group=GROUP)
class LightningCheckpointerConf:
    _target_: str = "scaffold.torch.lightning.callbacks.LightningCheckpointer"
    artifact_manager: ArtifactManagerConf = MISSING
    target_afid: Optional[str] = None  # artifact id to log the state of the model at the end of every epoch
    target_afid_best: Optional[str] = None  # artifact id to log the best model at the end of training
    resume_checkpoint_afid: Optional[str] = None  # artifact id to load a model state from at the start of training
    resume_checkpoint_version: Optional[int] = None  # If None, will load the latest version
    only_log_current_best: bool = False
