Artifact Manager
================

Overview
--------
The artifact manager subpackage provides a unified interface for logging, retrieving, and managing
artifacts across multiple backends. The subpackage defines a base abstract class, ``ArtifactManager``,
and includes concrete implementations for the following backends.

- **FileSystemArtifactManager**: Manages artifacts on a filesystem (local or cloud, e.g. using a gs:// bucket).
- **WandbArtifactManager**: Manages artifacts using the Weights & Biases (WandB) platform.

In addition, we also implement convenience context managers:
-  **DirectoryLogger**, which is useful for logging an entire folder as an artifact.
-  **ModelLogger**, which is a specialized logger for torch models and their states.


Basic Concept
-------------
The artifact manager is designed around two core principles: immutability and reproducibility.

**Immutability:**  
Each time an artifact is logged, the manager automatically creates a new version using a simple naming
convention (for example, "v0", "v1", "v2", etc.). Once an artifact is logged, its version is never modified.
This guarantees that past artifacts remain unchanged and can be reliably retrieved, ensuring that experiments
or production workflows remain fully reproducible. The artifact manager ensures that every logged artifact is
immutable and versioned, enabling you to re-run experiments or roll back to previous states with confidence.
You can learn more about artifacts and their use cases from `WandB docs <https://docs.wandb.ai/guides/artifacts/>`_.

**Unified Interface:**  
By providing a consistent interface regardless of the storage backend (whether a local or cloud-based store or WandB),
the artifact manager decouples the logging and retrieval logic from the storage implementation. This makes it easy
to switch artifact stores without changing your code. Artifacts are organized into collections (which act as logical groupings)
so that different experiments or types of data remain well separated.


Using a Cloud Artifact Store (gs:// Bucket)
---------------------------------------------
The ``FileSystemArtifactManager`` can be used with a cloud-based artifact store, such as a Google Cloud Storage
bucket. In the example below, we initialize the artifact manager with a gs:// URL, log a file artifact, and
download it back to a local directory.

.. code-block:: python

    from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager

    # Initialize the artifact manager with a cloud artifact store (gs:// bucket)
    manager = FileSystemArtifactManager(url="gs://mybucket/artifacts")

    # Log a file artifact.
    # This call uploads the file located at "/path/to/local/file.txt" as "my_artifact".
    # It also uploads the description as metadata. The exact location is specified in constants.py. Currently, it is "<artifact_base>/meta/readme.txt".
    # This (short) description should explain what the artifact is, and for what purpose it was generated.
    # log_files() returns an Artifact object with metadata about the logged artifact.
    artifact = manager.log_files("my_artifact", "/path/to/local/file.txt", "this is a description that will be logged to a file alongside the artifact")
    print(f"Logged artifact: {artifact.name}, version: {artifact.version}, collection: {artifact.collection}")

    # Download the artifact to a local directory.
    # download_artifact() returns an Artifact object when 'to' is provided.
    downloaded_artifact = manager.download_artifact("my_artifact", to="/path/to/download")
    print(f"Downloaded artifact: {downloaded_artifact.name}, version: {downloaded_artifact.version}")

    # Alternatively, use the context manager to deal with the artifact directly.
    # When 'to' is not provided, download_artifact() returns a TmpArtifact context manager
    # that has an 'artifact' property with the artifact metadata.
    tmp_artifact = manager.download_artifact("my_artifact")
    print(f"Temporary artifact: {tmp_artifact.artifact.name}, version: {tmp_artifact.artifact.version}")
    with tmp_artifact as tmp_download_dir:
        # Open the file and read its contents, no need to worry about cleanup.
        with open(f"{tmp_download_dir}/file.txt", "r") as f:
            pass


Using the WandB Artifact Manager
--------------------------------
The ``WandbArtifactManager`` uses the Weights & Biases backend to manage artifacts. Before using this
manager, ensure that you have initialized a wandb run (with ``wandb.init(...)``). The example below logs
a file artifact and then downloads it.

.. code-block:: python

    import wandb
    from scaffold.data.artifact_manager.wandb import WandbArtifactManager

    # Initialize wandb.
    wandb.init(project="my-project")

    # Create a WandB artifact manager instance.
    manager = WandbArtifactManager(project="my-project", collection="my_collection")

    # Log a file artifact.
    # log_files() returns an Artifact object with metadata about the logged artifact.
    artifact = manager.log_files("example_artifact", "/path/to/local/file.txt", "this is a sample description")
    print(f"Logged artifact: {artifact.name}, version: {artifact.version}, collection: {artifact.collection}")

    # Download the artifact to a local directory.
    # download_artifact() returns an Artifact object when 'to' is provided.
    downloaded_artifact = manager.download_artifact("example_artifact", to="/path/to/download")
    print(f"Downloaded artifact: {downloaded_artifact.name}, version: {downloaded_artifact.version}")

    # Alternatively, use the context manager to deal with the artifact directly.
    # When 'to' is not provided, download_artifact() returns a TmpArtifact context manager
    # that has an 'artifact' property with the artifact metadata.
    tmp_artifact = manager.download_artifact("example_artifact")
    print(f"Temporary artifact: {tmp_artifact.artifact.name}, version: {tmp_artifact.artifact.version}")
    with tmp_artifact as tmp_download_dir:
        # Open the file and read its contents, no need to worry about cleanup.
        with open(f"{tmp_download_dir}/file.txt", "r") as f:
            pass


Directory Logging Example
-------------------------
You can also log an entire directory as an artifact using the provided ``DirectoryLogger`` context manager.
In the example below, a temporary directory is created for logging, files are written into it, and then the
artifact is automatically logged when the context is exited. Later, the artifact is downloaded and verified.

.. code-block:: python

    # Log an entire folder as an artifact.
    # log_folder() returns a DirectoryLogger context manager.
    logger = manager.log_folder("my_awesome_artifact", "my_collection")
    with logger as tmp_dir:
         # Write files to the temporary folder.
         with open(f"{tmp_dir}/example.txt", "w") as f:
             f.write("Example content")
    # After the context exits, the artifact is logged and the logger.artifact property
    # contains the Artifact object with metadata about the logged artifact.
    print(f"Logged artifact: {logger.artifact.name}, version: {logger.artifact.version}")

    # Download the logged folder artifact.
    # download_artifact() returns an Artifact object when 'to' is provided.
    downloaded_artifact = manager.download_artifact("my_awesome_artifact", "my_collection", to="/path/to/download")
    print(f"Downloaded artifact: {downloaded_artifact.name}, version: {downloaded_artifact.version}")

    # You can also use the context manager:
    # When 'to' is not provided, download_artifact() returns a TmpArtifact context manager
    # that has an 'artifact' property with the artifact metadata.
    tmp_artifact = manager.download_artifact("my_awesome_artifact", "my_collection")
    print(f"Temporary artifact: {tmp_artifact.artifact.name}, version: {tmp_artifact.artifact.version}")
    with tmp_artifact as tmp_download_dir:
        # Open the file and read its contents, no need to worry about cleanup.
        with open(f"{tmp_download_dir}/example.txt", "r") as f:
            pass


Naming, Writing and Removing Versions
-------------------------------------
Besides logging and downloading, ``FileSystemArtifactManager`` can name a version without
transferring anything, hand out a version to write into directly, and remove one again.
``WandbArtifactManager`` raises ``NotImplementedError`` for all of these.

``resolve`` turns "latest" into a concrete version. Resolve once and pass the result on, so
every step of a pipeline reads the same version even if a new one is logged while it runs.

.. code-block:: python

    manager = FileSystemArtifactManager(url="gs://mybucket/artifacts")

    artifact = manager.resolve("my_dataset")                 # the highest-numbered version
    pinned = manager.resolve("my_dataset", version="v3")
    print(manager.list_versions("my_dataset"))               # ["v0", "v1", ...]

    # Where the version's contents live, for data too large to download.
    url = manager.artifact_url(artifact)

``log_files`` uploads from a local path, which does not work for data too large to build
locally first. ``next_version`` assigns a version instead, and you write into its URL.
Because there is no upload step, the description is set on its own.

.. code-block:: python

    artifact = manager.next_version("my_dataset")
    df.write_parquet(f"{manager.artifact_url(artifact)}/part-0.parquet")
    manager.set_description("my_dataset", "one row per event, partitioned by day")

Note that backends hold a reservation differently. On a local filesystem the version
directory is created, so the number stays taken even if you write nothing into it, and
``resolve`` can return an empty version. On an object store there are no directories, so a
version nobody wrote into is absent and the next caller is handed the same number. Write
into a reserved version promptly, and treat the number as used either way. Reserving is not
atomic, so concurrent writers need their own artifact names.

``remove_version`` deletes one version and everything under it, for a run that writes a
version per epoch and accumulates versions nothing reads. It refuses the newest version,
because removing it would free a number that ``next_version`` hands out again.

.. code-block:: python

    from scaffold.data.artifact_manager.base import Artifact

    for old in manager.list_versions("checkpoints")[:-3]:
        manager.remove_version(Artifact(name="checkpoints", collection="default", version=old))


Model Logger
============

Overview
--------
The ``ModelLogger`` class provides a simple interface for logging and retrieving a PyTorch model's state,
including optimizer and scheduler states, as an artifact. The class leverages a temporary local directory
to save state dictionaries before logging them to the configured artifact store via an ``ArtifactManager``.
This approach enables model state retrieval without needing to reinitialize the model class.

Usage Example: Logging a Model State
--------------------------------------
The example below demonstrates how to log a model’s state (including optimizer state) as an artifact.
In this example, a file system artifact store (using a cloud bucket URL) is used, but any implementation
of ``ArtifactManager`` (e.g. WandbArtifactManager) can be used instead.

.. code-block:: python

    import torch
    import torch.nn as nn
    import torch.optim as optim
    from scaffold.data.artifact_manager.model_logger import ModelLogger
    from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager

    # Define a simple model and optimizer.
    model = nn.Linear(10, 2)
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Initialize the artifact manager using a cloud artifact store (e.g. a gs:// bucket).
    manager = FileSystemArtifactManager(url="gs://mybucket/artifacts")

    # Initialize the ModelLogger with the artifact manager.
    model_logger = ModelLogger(artifact_manager=manager)

    # Log the model state under the artifact id "my_model_state".
    # log_state_to_artifact() returns the Artifact it wrote, so the version is available too.
    artifact = model_logger.log_state_to_artifact("my_model_state", model, "this is a sample description that will be logged", optimizers=[optimizer])
    print(f"Logged model state {artifact.name} at version {artifact.version}")

Usage Example: Retrieving a Model State
-----------------------------------------
Below is an example of how to retrieve a previously logged model state artifact and load it onto a device.

.. code-block:: python

    import torch
    from scaffold.data.artifact_manager.model_logger import ModelLogger
    from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager

    # Initialize the artifact manager using a cloud artifact store.
    manager = FileSystemArtifactManager(url="gs://mybucket/artifacts")

    # Initialize the ModelLogger.
    model_logger = ModelLogger(artifact_manager=manager)

    # Retrieve the model state from the artifact store (e.g., on CPU).
    state = model_logger.retrieve_state_from_artifact("my_model_state", device="cpu")
    print("Retrieved model state:", state)

Notes
-----
- The model state is saved as a file named ``state.pt`` within the artifact.
- The ``save_state`` method unpacks distributed models (if necessary) and saves the unwrapped model
  along with any optimizer or scheduler state dictionaries.
- When retrieving the model state, you can specify the target device (e.g. ``"cpu"`` or ``"cuda"``)
  to map the checkpoint appropriately.
