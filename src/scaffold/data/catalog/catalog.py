from typing import Any, Dict, List, MutableMapping, Optional

from omegaconf import OmegaConf

from scaffold.data.catalog.dataset import Dataset, PartialDataset
from scaffold.data.catalog.meta import MetaData
from scaffold.data.iterstream.source import FilePathGenerator, IterableSamplerSource, IterableSource

ALLOWED_DATASETS = []


class Catalog(MetaData, MutableMapping):
    vals: Optional[Dict[str, MetaData]] = {}

    def __getitem__(self, key: str) -> MetaData:
        return self.vals[key]

    def __setitem__(self, key: str, value: MetaData) -> None:
        self.vals[key] = value

    def __delitem__(self, key: str) -> None:
        del self.vals[key]

    def __iter__(self) -> iter:
        return iter(self.vals)

    def __len__(self) -> int:
        return len(self.vals)


class SafeInit:
    def __init__(self, cls: type) -> None:
        self.cls = cls

    def __call__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> Dataset:
        if self.cls is PartialDataset:
            a_target = OmegaConf.create(kwargs["func_cfg"])["_target_"]
            notfound = True
            for s in ALLOWED_DATASETS:
                m = ".".join(a_target.split(".")[:-1])
                c = a_target.split(".")[-1]
                if m == s.__module__ and c == s.__name__:
                    notfound = False
                    break
            if notfound:
                raise ValueError(
                    f"PartialDataset instantiating {a_target} is not allowed! "
                    + "Use ALLOWED_DATASETS to whitelist Dataset types."
                )
        elif self.cls not in ALLOWED_DATASETS:
            raise ValueError(
                f"Instantiation of {self.cls} is not allowed! " + "Use ALLOWED_DATASETS to whitelist Dataset types."
            )
        return self.cls(*args, **kwargs)


# Whitelist Dataset types that can be used in LazyDataset
ALLOWED_DATASETS.append(Catalog)
ALLOWED_DATASETS.append(PartialDataset)
ALLOWED_DATASETS.append(IterableSource)
ALLOWED_DATASETS.append(IterableSamplerSource)
ALLOWED_DATASETS.append(FilePathGenerator)
