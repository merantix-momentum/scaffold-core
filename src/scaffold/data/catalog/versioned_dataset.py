from __future__ import annotations

from typing import Any, List

from scaffold.data.catalog.catalog import ALLOWED_DATASETS, Catalog
from scaffold.data.catalog.dataset import Dataset


class VersionedDataset(Catalog, Dataset):
    version: str

    def __getitem__(self, key: str) -> VersionedDataset:
        if key not in self.vals:
            raise KeyError(f"Version '{key}' not found. Available versions: {list(self.vals.keys())}")
        self.version = key
        return self

    def __setitem__(self, key: str, value: Dataset) -> None:
        for x in key.split("."):
            if not x.isdigit():
                raise ValueError(
                    f"Version string '{key}' is not valid. Only numeric versions separated by '.' are allowed."
                )
        self.vals[key] = value

    @property
    def latest(self) -> VersionedDataset:
        versions = list(self.vals.keys())
        versions.sort(key=lambda s: [int(u) for u in s.split(".")])
        self.version = versions[-1]
        return self

    def push(self, dataset: Dataset) -> VersionedDataset:
        latest_version = self.sorted_versions()[-1]
        version_parts = latest_version.split(".")
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        new_version = ".".join(version_parts)

        self.vals[new_version] = dataset
        self.version = new_version
        return self

    def sorted_versions(self) -> List[str]:
        versions = list(self.vals.keys())
        # bubble sort versions
        for i in range(len(versions)):
            for j in range(0, len(versions) - i - 1):
                v1_parts = versions[j].split(".")
                v2_parts = versions[j + 1].split(".")
                for p1, p2 in zip(v1_parts, v2_parts):
                    if p1.isdigit() and p2.isdigit():
                        if int(p1) > int(p2):
                            versions[j], versions[j + 1] = versions[j + 1], versions[j]
                            break
                    elif p1.isdigit():
                        versions[j], versions[j + 1] = versions[j + 1], versions[j]
                        break
                    elif p2.isdigit():
                        break
                    else:
                        if p1 > p2:
                            versions[j], versions[j + 1] = versions[j + 1], versions[j]
                            break
        return versions

    def __call__(self, /, *args, **kwargs) -> Any:
        if self.version not in self.vals:
            raise KeyError(f"Version '{self.version}' not found. Available versions: {list(self.vals.keys())}")
        return self.vals[self.sorted_versions()[-1]](*args, **kwargs)


ALLOWED_DATASETS.append(VersionedDataset)
