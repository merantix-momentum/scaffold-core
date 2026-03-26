from hydra_zen import builds, store
from omegaconf import MISSING

from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager
from scaffold.data.artifact_manager.wandb import WandbArtifactManager

GROUP = "scaffold/artifact_manager"

WandbArtifactManagerConf = builds(
    WandbArtifactManager,
    collection="default",
    entity="mxm",
    project=MISSING,
)

FileSystemArtifactManagerConf = builds(
    FileSystemArtifactManager,
    collection="default",
    url=MISSING,
    fs_kwargs={},
)

store(WandbArtifactManagerConf, group=GROUP, name="WandbArtifactManagerConf")
store(FileSystemArtifactManagerConf, group=GROUP, name="FileSystemArtifactManagerConf")
