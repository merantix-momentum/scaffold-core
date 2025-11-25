from __future__ import annotations

from typing import Any, List, Mapping

from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager
from scaffold.data.artifact_manager.wandb import WandbArtifactManager
from scaffold.data.catalog.catalog import ALLOWED_DATASETS
from scaffold.data.catalog.dataset import Dataset


class WandBArtifactManagerDataset(Dataset):
    entity: str = None
    project: str = None
    collection_name: str = "default"
    _manager: WandbArtifactManager = None

    def __call__(self, /, *args, **kwargs) -> WandbArtifactManager:
        if self._manager is None:
            self._manager = WandbArtifactManager(
                entity=self.entity, project=self.project, collection=self.collection_name
            )
        return self._manager


class FileSystemArtifactManagerDataset(Dataset):
    url: str
    collection_name: str = "default"
    _manager: FileSystemArtifactManager = None

    def __call__(self, /, *args, **kwargs) -> FileSystemArtifactManager:
        if self._manager is None:
            self._manager = FileSystemArtifactManager(url=self.url, collection=self.collection_name)
        return self._manager


class ArtifactDataset(Dataset, Mapping):
    artifact_name: str
    manager: WandBArtifactManagerDataset | FileSystemArtifactManagerDataset
    version: str | None = None

    def __getitem__(self, key: str) -> ArtifactDataset:
        self.version = key
        return self

    @property
    def latest(self) -> ArtifactDataset:
        self.version = self.sorted_versions()[-1]
        return self

    def push(self, path: str) -> ArtifactDataset:
        self.manager().log_files(self.artifact_name, path)
        self.version = self.sorted_versions()[-1]
        return self

    def sorted_versions(self) -> List[str]:
        return self.manager().list_versions(self.artifact_name)

    def __call__(self, to: str | None = None, /, *args, **kwargs) -> Any:
        if self.version is None:
            self.version = self.sorted_versions()[-1]
        return self.manager().download_artifact(self.artifact_name, version=self.version, to=to)

    def __iter__(self) -> iter:
        return iter(self.sorted_versions())

    def __len__(self) -> int:
        return len(self.sorted_versions())


ALLOWED_DATASETS.append(ArtifactDataset)
ALLOWED_DATASETS.append(FileSystemArtifactManagerDataset)
ALLOWED_DATASETS.append(WandBArtifactManagerDataset)
