Data Catalog
==========

Scaffold provides an API for organizing datasets within your data science project.
The functionality is provided through the :py:class:`Catalog` and :py:class:`Dataset` classes.

Simple Catalog Example
----------------

Create the catalog

.. code-block:: python

    from scaffold.data.catalog import Catalog

    c = Catalog()

Turn any callable into a dataset using :py:func:`partialDataset` and add it to the catalog.

.. code-block:: python

    from scaffold.data.catalog import Catalog, partialDataset
    from scaffold.data.iterstream import IterableSource

    c["imagenet"] = partialDataset(IterableSource, range(10), metadata={"description": "my dataset"})

A catalog implements the :py:class:`MutableMapping` interface. Use it like a py:class:`Dict` to access the dataset from catalog.

.. code-block:: python

    # Access dataset
    print(c["imagenet"]().collect())

    # Read metadata
    print(f'Imagenet metadata: {c["imagenet"].metadata}')


Store and share catalogs
----------------------

Catalogs can be serialized and deserialized with :py:mod:`Pydantic` compatible framework. 
We prefer using :py:mod:`hydra-zen`. Scaffold provides a helper target to safely load a catalog from arbitrary sources called :py:class:`SafeInit`.

.. code-block:: python

    from hydra_zen import instantiate, just
    from scaffold.data.catalog import SafeInit

    # serialize catalog
    cfg = just(c)

    # store cfg to file or share it ...

    # deserialize catalog
    c_loaded = instantiate(cfg, _target_wrapper_=SafeInit)

Custom Dataset Types
--------------------

You can create custom dataset types by subclassing :py:class:`Dataset`. Let's build a csv dataloader:

.. code-block:: python

    from scaffold.data.catalog import Catalog, Dataset, partialDataset, ALLOWED_DATASETS
    import pandas as pd

    class CSVLoader(Dataset):
        path: str

        def __call__(self):
            return pd.read_csv(self.path)

    # register custom dataset type to whitelist it for :py:class:`SafeInit`
    ALLOWED_DATASETS.append(CSVLoader)

    c = Catalog()
    c["csv_dataset"] = CSVLoader(path="path/to/csv/file.csv")
    print(c["csv_dataset"]().head())  # prints the first few rows of the CSV file

Artifacts
------------------

Scaffold supports versioned artifacts through the :py:class:`ArtifactDataset` class. Artifacts are managed by an artifact manager, such as :py:class:`FileSystemArtifactManagerDataset` or :py:class:`WandBArtifactManagerDataset`.

.. code-block:: python

    from scaffold.data.catalog import Catalog, ArtifactDataset, FileSystemArtifactManagerDataset

    c = Catalog()
    
    # Define an artifact manager
    manager = FileSystemArtifactManagerDataset(url="./artifacts")

    # Add an artifact to the catalog
    c["my_model"] = ArtifactDataset(artifact_name="model", manager=manager)

    # Push a file as a new version of the artifact
    c["my_model"].push("path/to/model.pt")

    # List all versions
    print(c["my_model"].sorted_versions())

    # Get the latest version
    latest_model = c["my_model"].latest()

    # Get a specific version
    v1_model = c["my_model"]["v1"]()


Hierarchical Catalogs
---------------------

Catalogs can be nested to create hierarchical structures. Use another :py:class:`Catalog` as value in a parent catalog.

.. code-block:: python

    from scaffold.data.catalog import Catalog, partialDataset
    from scaffold.data.iterstream import IterableSource

    c = Catalog()

    c["imagenet"] = Catalog(vals={
        "train": partialDataset(IterableSource, range(1000)),
        "val": partialDataset(IterableSource, range(200)),
    })

    # Access nested dataset
    print(c["imagenet"]["train"]().collect())
