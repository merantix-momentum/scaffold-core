import logging
import os
import re
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from scaffold.data.fs import join_path

logger = logging.getLogger(__name__)


class TmpArtifact:
    """Context manager for temporary artifact download.

    This class downloads an artifact to a temporary directory when entering
    a context, and cleans up the directory upon exit.
    """

    def __init__(self, artifact_manager: "ArtifactManager", collection: str, artifact: str, version: str) -> None:
        """Initialize a temporary artifact context.

        Args:
            artifact_manager (ArtifactManager): The artifact manager to use.
            collection (str): The collection name.
            artifact (str): The artifact name.
            version (str): The artifact version.
        """
        self.artifact_manager = artifact_manager
        self.tempdir = tempfile.mkdtemp()
        self.collection = collection
        self.artifact = artifact
        self.version = version

    def __enter__(self) -> str:
        """Download the artifact into a temporary directory.

        Returns:
            str: The path to the temporary directory containing the artifact.
        """
        self.artifact_manager.download_artifact(self.artifact, self.collection, self.version, to=self.tempdir)
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

    def __init__(self, artifact_manager: "ArtifactManager", artifact: str, collection: Optional[str] = None) -> None:
        """Initialize a DirectoryLogger.

        Args:
            artifact_manager (ArtifactManager): The artifact manager to use.
            artifact (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the artifact manager's active collection.
        """
        self.artifact_manager = artifact_manager
        self.artifact = artifact
        self.collection = collection or artifact_manager.active_collection
        self.tempdir = tempfile.mkdtemp()

    def __enter__(self) -> str:
        """Create and return a directory for logging files.

        Returns:
            str: The path to the logging directory.
        """
        self.artifact_dir = join_path(self.tempdir, self.artifact)
        os.makedirs(self.artifact_dir, exist_ok=False)
        return self.artifact_dir

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Log the folder if non-empty and clean up the temporary directory."""
        if os.listdir(self.artifact_dir):
            self.artifact_manager.log_files(self.artifact, self.artifact_dir, self.collection)
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
    def exists_in_collection(self, artifact: str, collection: Optional[str] = None) -> bool:
        """Check if artifact exists in specified collection."""
        raise NotImplementedError

    @abstractmethod
    def log_files(
        self,
        artifact_name: str,
        local_path: Path,
        collection: Optional[str] = None,
        artifact_path: Optional[Path] = None,
    ) -> None:
        """
        Upload a file or folder into (current) collection, increment version automatically

        Args:
            artifact_name: Name of artifact to log
            local_path: Local path to the file or folder to log
            collection: Name of collection to log to, defaults to the active collection
            artifact_path: path under which to log the files within the artifact, defaults to "./"
        """
        raise NotImplementedError

    @abstractmethod
    def download_artifact(
        self, artifact: str, collection: Optional[str] = None, version: Optional[str] = None, to: Optional[str] = None
    ) -> Union[str, TmpArtifact]:
        """
        Download artifact contents (from current collection) to specific location and return a source listing them.

        If no target location is specified, a context manager for a temporary directory is created and the path to it
        is returned. Retrieve latest version unless specified.
        """
        raise NotImplementedError

    def exists(self, artifact: str) -> bool:
        """Check if artifact exists in specified collection."""
        return any([self.exists_in_collection(artifact, collection) for collection in self.list_collection_names()])

    def log_folder(self, artifact: str, collection: Optional[str] = None) -> DirectoryLogger:
        """Create a context manager for logging a directory of files as a single artifact."""
        return DirectoryLogger(self, artifact, collection)
