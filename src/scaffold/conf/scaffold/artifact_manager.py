import typing as t
from dataclasses import field

from omegaconf import MISSING

from scaffold.hydra.config_helpers import structured_config

GROUP = "scaffold/artifact_manager"


@structured_config(group=GROUP)
class ArtifactManagerConf:
    _target_: str = MISSING
    collection: str = "default"


@structured_config(group=GROUP)
class WandbArtifactManagerConf(ArtifactManagerConf):
    _target_: str = "scaffold.data.artifact_manager.wandb.WandbArtifactManager"
    entity: str = "mxm"
    project: str = MISSING


@structured_config(group=GROUP)
class FileSystemArtifactManagerConf(ArtifactManagerConf):
    _target_: str = "scaffold.data.artifact_manager.filesystem.FileSystemArtifactManager"
    url: str = MISSING
    fs_kwargs: t.Dict = field(default_factory=dict)
