from hydra_zen import builds
from omegaconf import MISSING

from scaffold.conf import scaffold_store
from scaffold.torch.lightning.callbacks import LightningCheckpointer

GROUP = "scaffold/lightning/checkpointer"

LightningCheckpointerConf = builds(
    LightningCheckpointer,
    artifact_manager=MISSING,
    target_afid=None,
    target_afid_best=None,
    resume_checkpoint_afid=None,
    resume_checkpoint_version=None,
    only_log_current_best=False,
)

scaffold_store(LightningCheckpointerConf, group=GROUP, name="LightningCheckpointerConf")
