import pytest
from omegaconf import OmegaConf

from scaffold.data.catalog.dataset import Dataset, PartialDataset, partialDataset


def add(a: int, b: int) -> int:
    return a + b


def test_partial_dataset_creation_and_call():
    pd = partialDataset(add, 2, b=3, metadata={"name": "adder"})
    assert isinstance(pd, PartialDataset)
    # Calling without args uses the captured args/kwargs from builds
    assert pd() == 5


def test_partial_dataset_metadata_preserved():
    pd = partialDataset(add, 1, b=4, metadata={"custom": 123})
    assert pd.metadata == {"custom": 123}


def test_partial_dataset_default_metadata_is_empty_dict():
    pd = partialDataset(add, 1)
    # When metadata isn't provided, factory passes None explicitly
    assert pd.metadata is None


def test_partial_dataset_func_cfg_contains_target():
    pd = partialDataset(add, 10, b=5)
    cfg = OmegaConf.create(pd.func_cfg)
    assert "_target_" in cfg
    # Ensure hydra-zen captured args correctly
    assert cfg.get("_target_").endswith("add")
    assert cfg.get("_args_") == [10]
    assert cfg.get("b") == 5


def test_partial_dataset_is_subclass_of_dataset():
    assert issubclass(PartialDataset, Dataset)


def test_dataset_cannot_be_instantiated_directly():
    # Creating a subclass without implementing __call__ should raise TypeError due to abstractmethod
    class BadDataset(Dataset):
        pass

    with pytest.raises(TypeError):
        BadDataset()  # abstract __call__ not implemented
