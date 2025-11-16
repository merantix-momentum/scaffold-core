import pytest

from scaffold.data.catalog.catalog import ALLOWED_DATASETS, Catalog, SafeInit
from scaffold.data.catalog.dataset import PartialDataset, partialDataset
from scaffold.data.catalog.meta import MetaData


class DummyMeta(MetaData):
    pass


# Top-level helper callables so hydra_zen.builds can resolve an import path
def not_allowed_func():
    return 123


def build_value(x: int, y: int = 2):
    return {"sum": x + y}


def test_catalog_mapping_basic_operations():
    catalog = Catalog()
    assert len(catalog) == 0

    item_meta = MetaData(metadata={"source": "unit-test", "version": 1})
    catalog["item1"] = item_meta
    assert len(catalog) == 1
    assert catalog["item1"].metadata["version"] == 1

    # iteration yields the key we inserted
    assert list(iter(catalog)) == ["item1"]

    del catalog["item1"]
    assert len(catalog) == 0


def test_safeinit_allows_whitelisted_class():
    # Catalog is whitelisted at module import time
    factory = SafeInit(Catalog)
    inst = factory(metadata={"ok": True})
    assert isinstance(inst, Catalog)
    assert inst.metadata["ok"] is True


def test_safeinit_blocks_non_whitelisted_class():
    assert DummyMeta not in ALLOWED_DATASETS  # sanity check
    factory = SafeInit(DummyMeta)
    with pytest.raises(ValueError) as e:
        factory(metadata={"bad": True})
    assert "not allowed" in str(e.value)


def test_safeinit_partialdataset_allows_target_in_whitelist():
    # Build a PartialDataset whose _target_ points to an allowed Dataset type (Catalog)
    pd = partialDataset(Catalog, metadata={"pd": True})
    factory = SafeInit(PartialDataset)
    inst = factory(func_cfg=pd.func_cfg, metadata=pd.metadata)
    assert isinstance(inst, PartialDataset)
    # Calling the PartialDataset should instantiate the target (Catalog)
    created = inst()
    assert isinstance(created, Catalog)


def test_safeinit_partialdataset_blocks_disallowed_target():
    # A plain function isn't an allowed dataset class
    pd = partialDataset(not_allowed_func)
    factory = SafeInit(PartialDataset)
    with pytest.raises(ValueError) as e:
        factory(func_cfg=pd.func_cfg, metadata=pd.metadata)
    assert "is not allowed" in str(e.value)


def test_partialdataset_instantiate_original_callable():
    # Ensure partialDataset wiring returns the callable's result when invoked
    pd = partialDataset(build_value, 3, y=4)
    # Since build_value isn't whitelisted as a Dataset class, SafeInit should reject it
    factory = SafeInit(PartialDataset)
    with pytest.raises(ValueError):
        factory(func_cfg=pd.func_cfg, metadata=pd.metadata)

    # Direct invocation (bypassing SafeInit) should still work because PartialDataset itself can call instantiate
    result = pd()
    assert result == {"sum": 7}
