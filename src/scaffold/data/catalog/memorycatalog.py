from typing import Dict, List

from scaffold.data.catalog.catalog import Catalog
from scaffold.data.catalog.dataproduct import DataProduct


class MemoryCatalog(Catalog):
    def __init__(self) -> None:
        self._catalogs: Dict = {}
        self._dataproducts: Dict = {}
        self._properties: Dict = {}
        super().__init__()

    def create_catalog(self, id: str) -> None:
        assert not self.exists_catalog(id)
        self._catalogs[id] = MemoryCatalog()

    def drop_catalog(self, id: str) -> None:
        del self._catalogs[id]

    def rename_catalog(self, old_id: str, new_id: str) -> None:
        assert self.exists_catalog(old_id) and not self.exists_catalog(new_id)
        self._catalogs[new_id] = self._catalogs[old_id]
        self.drop_dataproduct(old_id)

    def exists_catalog(self, id: str) -> bool:
        return id in self._catalogs

    @property
    def catalogs(self) -> List[str]:
        return list(self._catalogs.keys())

    def load_catalog(self, id: str) -> Catalog:
        return self._catalogs[id]

    def register_dataproduct(self, id: str, dataproduct: DataProduct) -> None:
        assert id is not None and id != "" and not self.exists_dataproduct(id)
        self._dataproducts[id] = dataproduct

    def load_dataproduct(self, id: str) -> DataProduct:
        return self._dataproducts[id]

    def drop_dataproduct(self, id: str) -> None:
        del self._dataproducts[id]

    def exists_dataproduct(self, id: str) -> bool:
        return id in self._dataproducts

    def rename_dataproduct(self, old_id: str, new_id: str) -> None:
        assert self.exists_dataproduct(old_id) and not self.exists_dataproduct(new_id)
        self._dataproducts[new_id] = self._dataproducts[old_id]
        self.drop_dataproduct(old_id)

    @property
    def dataproducts(self) -> List[str]:
        return list(self._dataproducts.keys())

    def set_properties(self, properties: Dict[str, str]) -> None:
        assert properties is not None
        self._properties = properties

    @property
    def properties(self) -> Dict[str, str]:
        return self._properties
