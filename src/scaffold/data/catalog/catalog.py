from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from scaffold.data.catalog.dataproduct import DataProduct


class Catalog(ABC):
    """
    A catalog is a collection of dataproducts and subcatalogs.
    It is a hierarchical structure that can be used to organize dataproducts and catalogs.
    """

    @abstractmethod
    def create_catalog(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def drop_catalog(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def rename_catalog(self, old_id: str, new_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists_catalog(self, id: str) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def catalogs(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def load_catalog(self, id: str) -> Catalog:
        raise NotImplementedError

    @abstractmethod
    def register_dataproduct(self, id: str, dataproduct: DataProduct) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_dataproduct(self, id: str) -> DataProduct:
        raise NotImplementedError

    @abstractmethod
    def drop_dataproduct(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists_dataproduct(self, id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def rename_dataproduct(self, old_id: str, new_id: str) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def dataproducts(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def set_properties(self, properties: Dict[str, str]) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def properties(self, properties) -> Dict[str, str]:
        raise NotImplementedError

    def __repr__(self) -> str:  # noqa D105
        return f"Catalog(catalogs={self.catalogs}, dataproducts={self.dataproducts}, properties={self.properties})"


class ImmutableCatalog(Catalog):
    def __init__(self, catalog: Catalog) -> None:
        r"""Turn catalog immutable."""
        self._catalog = catalog

    def __repr__(self) -> str:  # noqa D105
        return self._catalog.__repr__()

    @property
    def catalogs(self) -> List[str]:
        return self._catalog.catalogs

    def exists_catalog(self, id: str) -> bool:
        return self._catalog.exists_catalog(id)

    def load_catalog(self, id: str) -> Catalog:
        return self._catalog.load_catalog(id)

    def exists_dataproduct(self, id: str) -> bool:
        raise NotImplementedError

    def load_dataproduct(self, id: str) -> DataProduct:
        return self._catalog.load_dataproduct(id)

    @property
    def dataproducts(self) -> List[str]:
        raise self._catalog.dataproducts

    @property
    def properties(self) -> Dict[str, str]:
        return self._catalog.properties
