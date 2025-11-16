from abc import abstractmethod
from typing import Any, Dict

from hydra_zen import builds, instantiate
from omegaconf import OmegaConf
from pyparsing import ABC

from scaffold.data.catalog.meta import MetaData


class Dataset(MetaData, ABC):
    @abstractmethod
    def __call__(self, **kwargs: Dict[str, Any]) -> Any:
        raise NotImplementedError


class PartialDataset(Dataset):
    func_cfg: str

    def __call__(self, /, *args, **kwargs) -> Any:
        return instantiate(OmegaConf.create(self.func_cfg), *args, **kwargs)


def partialDataset(func: callable, /, *args, metadata: Dict[str, Any] = None, **kwargs) -> PartialDataset:
    return PartialDataset(func_cfg=OmegaConf.to_yaml(builds(func, *args, **kwargs)), metadata=metadata)
