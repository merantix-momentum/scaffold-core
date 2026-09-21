import logging
import os
import re
import shutil
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, NoReturn, Optional, Union

from scaffold.data.fs import join_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Artifact:
    """Immutable dataclass representing an artifact with its metadata."""

    name: str
    collection: str
    version: str


class TmpArtifact:
    """Context manager for temporary artifact download.

    This class downloads an artifact to a temporary directory when entering
    a context, and cleans up the directory upon exit.
    """

    def __init__(self, artifact_manager: "ArtifactManager", collection: str, artifact_name: str, version: str) -> None:
        """Initialize a temporary artifact context.

        Args:
            artifact_manager (ArtifactManager): The artifact manager to use.
            collection (str): The collection name.
            artifact_name (str): The artifact name.
            version (str): The artifact version.
        """
        self.artifact_manager = artifact_manager
        self.tempdir = tempfile.mkdtemp()
        self.artifact = Artifact(name=artifact_name, collection=collection, version=version)

    def __enter__(self) -> str:
        """Download the artifact into a temporary directory.

        Returns:
            str: The path to the temporary directory containing the artifact.
        """
        self.artifact_manager.download_artifact(
            self.artifact.name, self.artifact.collection, self.artifact.version, to=self.tempdir
        )
        return self.tempdir

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clean up the temporary directory."""
        shutil.rmtree(self.tempdir)


class DirectoryLogger:
    """Context manager for logging a directory as an artifact.

    This class creates a temporary directory where files can be written.
    When exiting the context, if the directory contains files, it is logged
    as an artifact.
    """

    def __init__(
        self,
        artifact_manager: "ArtifactManager",
        artifact_name: str,
        artifact_description: str,
        collection: Optional[str] = None,
    ) -> None:
        """Initialize a DirectoryLogger.

        Args:
            artifact_manager (ArtifactManager): The artifact manager to use.
            artifact_name (str): The artifact name.
            artifact_description:
                Description of the artifact.
                Will be logged at <artifact_root>/ARTIFACT_META_DIR/ARTIFACT_DESCRIPTION_FILE
                and serves to reduce undocumented artifact clutter.
            collection (Optional[str]): The collection name. Defaults to the artifact manager's active collection.
        """
        self.artifact_manager = artifact_manager
        self._artifact_name = artifact_name
        self._collection = collection or artifact_manager.active_collection
        self._artifact_description = artifact_description
        self.tempdir = tempfile.mkdtemp()
        # None until __exit__, and still None if nothing was written: an empty directory
        # is not logged and so has no version.
        self.artifact: Optional[Artifact] = None

    def __enter__(self) -> str:
        """Create and return a directory for logging files.

        Returns:
            str: The path to the logging directory.
        """
        self.artifact_dir = join_path(self.tempdir, self._artifact_name)
        os.makedirs(self.artifact_dir, exist_ok=False)
        return self.artifact_dir

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Log the folder if non-empty, recording the version, and clean up."""
        if os.listdir(self.artifact_dir):
            self.artifact = self.artifact_manager.log_files(
                self._artifact_name, self.artifact_dir, self._artifact_description, self._collection
            )
        shutil.rmtree(self.tempdir)


class ArtifactManager(ABC):
    def __init__(self, collection: str = "default"):
        """Artifact manager interface for various backends."""
        self._active_collection = collection

    @property
    def active_collection(self) -> str:
        """
        Collections act as folders of artifacts.

        It is ultimately up to the user how to structure their artifact store and the collections therein. All
        operations accessing artifacts allow explicit specification of the collection to use.
        Therefore, users could use collections to separate different artifact types or different experiments / runs.
        The manager maintains an 'active' collection which it logs to by default. This can be set at the run start
        when the manager is initialized and then remain unchanged for the duration of the run.

        To avoid incompatibility between different backends, collections cannot be nested (e.g. as subfolders on a
        filesystem) as in particular the WandB backend has no real notion of nested folder structures.
        """
        return self._active_collection

    @active_collection.setter
    def active_collection(self, value: str) -> None:
        """
        Sets the active collections that is being logged to by default.

        The provided value is verified to ensure that no nested collections are used.
        """
        if not re.match(r"^[a-zA-Z0-9\-_:]+$", value):
            raise ValueError(
                "Invalid collection name - must not be empty and can only contain alphanumerics, dashes, underscores "
                "and colons."
            )
        self._active_collection = value

    @abstractmethod
    def list_collection_names(self) -> Iterable:
        """Return list of all collections in the artifact store"""
        raise NotImplementedError

    @abstractmethod
    def exists_in_collection(self, artifact_name: str, collection: Optional[str] = None) -> bool:
        """Check if artifact exists in specified collection."""
        raise NotImplementedError

    @abstractmethod
    def log_files(
        self,
        artifact_name: str,
        local_path: Path,
        description: str,
        collection: Optional[str] = None,
        artifact_path: Optional[Path] = None,
    ) -> Artifact:
        """
        Upload a file or folder into (current) collection, increment version automatically

        Args:
            artifact_name: Name of artifact to log
            local_path: Local path to the file or folder to log
            description: Description of the artifact, will be logged to improve documentation.
            collection: Name of collection to log to, defaults to the active collection
            artifact_path: path under which to log the files within the artifact, defaults to "./"
        Returns:
            Artifact: The logged artifact with its metadata (name, collection, version).
        """
        raise NotImplementedError

    @abstractmethod
    def download_artifact(
        self,
        artifact_name: str,
        collection: Optional[str] = None,
        version: Optional[str] = None,
        to: Optional[str] = None,
    ) -> Union[Artifact, TmpArtifact]:
        """
        Download artifact contents (from current collection) to specific location and return a source listing them.

        If no target location is specified, a context manager for a temporary directory is created and the path to it
        is returned. Retrieve latest version unless specified.

        Args:
            artifact_name: The artifact name.
            collection: The collection name. Defaults to the active collection.
            version: The artifact version. If None, the latest version is used.
            to: The destination path. If not provided, a TmpArtifact context manager is returned.

        Returns:
            Union[Artifact, TmpArtifact]: If `to` is provided, returns an Artifact with metadata.
                Otherwise, returns a TmpArtifact context manager that also has an `artifact` property.
        """
        raise NotImplementedError

    def exists(self, artifact_name: str) -> bool:
        """Check if artifact exists in specified collection."""
        return any(
            [self.exists_in_collection(artifact_name, collection) for collection in self.list_collection_names()]
        )

    def _unsupported(self, what: str) -> NoReturn:
        """Refuse an operation this backend cannot offer, naming the backend.

        Args:
            what (str): What was asked for, as a verb phrase.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(f"{type(self).__name__} cannot {what}")

    def list_versions(self, artifact_name: str, collection: Optional[str] = None) -> List[str]:
        """The versions of an artifact, oldest first.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            List[str]: Version strings such as ``["v0", "v1"]``, empty if there are none.
        """
        self._unsupported("list the versions of an artifact")

    def resolve(
        self,
        artifact_name: str,
        collection: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Artifact:
        """Name a concrete version of an artifact, without transferring anything.

        Resolve once and pass the result on, so every step of a pipeline reads the same
        version even if a new one is logged while it runs.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            version (Optional[str]): A version such as ``"v3"``. None or ``"latest"`` resolves
                to the most recent one.

        Returns:
            Artifact: The resolved artifact, whose version is never ``"latest"``.

        Raises:
            FileNotFoundError: If the artifact has no versions, or not the one asked for.
        """
        self._unsupported("resolve an artifact version")

    def artifact_url(self, artifact: Artifact) -> str:
        """Where a version's contents live, for a reader that opens them in place.

        Only backends that store artifacts at an addressable location can answer this. Use
        it for data too large to copy; :meth:`download_artifact` covers everything else.

        Args:
            artifact (Artifact): The artifact to locate, at a concrete version.

        Returns:
            str: The URL of that version's contents.
        """
        self._unsupported("report where an artifact lives without downloading it")

    def next_version(self, artifact_name: str, collection: Optional[str] = None) -> Artifact:
        """Assign the next version of an artifact, for a write that happens in place.

        Use this when the data is too large to build locally and upload with
        :meth:`log_files`: it assigns the version, and the caller writes into
        :meth:`artifact_url` directly.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            Artifact: The next version, ready to be written into.
        """
        self._unsupported("assign a version for a write that happens in place")

    def remove_version(self, artifact: Artifact) -> None:
        """Delete one version of an artifact and everything under it, irreversibly.

        This removes one version, not the artifact, so an artifact whose versions have all
        been removed stays distinguishable from one that never existed.

        Backends that number versions sequentially must refuse the newest one. Removing it
        frees a number that :meth:`next_version` hands out again, so the next write would
        land on a version another record already names.

        Args:
            artifact (Artifact): The version to remove, at a concrete version.

        Raises:
            FileNotFoundError: If the version is not there.
            ValueError: If it is the newest version of its artifact.
        """
        self._unsupported("remove a version of an artifact")

    def set_description(self, artifact_name: str, description: str, collection: Optional[str] = None) -> None:
        """Record an artifact's description, which belongs to the artifact and not a version.

        :meth:`log_files` writes the description as part of logging. A write that happens
        in place has no such step, so the description is available on its own.

        Args:
            artifact_name (str): The artifact name.
            description (str): The description to record.
            collection (Optional[str]): The collection name. Defaults to the active collection.
        """
        self._unsupported("record an artifact description on its own")

    def log_folder(
        self, artifact_name: str, artifact_description: str, collection: Optional[str] = None
    ) -> DirectoryLogger:
        """Create a context manager for logging a directory of files as a single artifact."""
        return DirectoryLogger(self, artifact_name, artifact_description, collection)
