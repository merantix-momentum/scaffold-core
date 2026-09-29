import logging
import re
import typing as t

from scaffold.constants import ARTIFACT_DESCRIPTION_FILE, ARTIFACT_META_DIR
from scaffold.data.artifact_manager.base import Artifact, ArtifactManager, TmpArtifact
from scaffold.data.fs import get_fs_from_url, join_path

logger = logging.getLogger(__name__)

# Versions are numbered directories under the artifact. Leading zeros are rejected so that
# each number has exactly one directory name.
VERSION_PATTERN = re.compile(r"v(0|[1-9][0-9]*)")


class FileSystemArtifactManager(ArtifactManager):
    """Artifact manager backed by a file system using fsspec.

    This implementation logs and retrieves artifacts from a specified URL.
    """

    def __init__(self, url: str, collection: str = "default", **fs_kwargs: t.Any) -> None:
        """Initialize a FileSystemArtifactManager.

        Args:
            url (str): The base URL of the artifact store.
            collection (str): The default collection name. Defaults to "default".
            **fs_kwargs (Any): Additional keyword arguments for the file system.
        """
        super().__init__(collection=collection)
        self.url = url.rstrip("/")
        self.fs = get_fs_from_url(self.url, **fs_kwargs)

    def list_collection_names(self) -> t.Iterable[str]:
        """List all collections in the artifact store.

        Returns:
            Iterable[str]: A list of collection names.
        """
        try:
            items = self.fs.ls(self.url, detail=True)
        except FileNotFoundError:
            return []
        return [item["name"].split("/")[-1] for item in items if item.get("type") == "directory"]

    def exists_in_collection(self, artifact_name: str, collection: t.Optional[str] = None) -> bool:
        """Check if an artifact exists in a specific collection.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            bool: True if the artifact exists, False otherwise.
        """
        collection = self._collection(collection)
        return self.fs.exists(self._artifact_dir(artifact_name, collection))

    def _artifact_dir(self, artifact_name: str, collection: str) -> str:
        """The directory holding every version of one artifact."""
        return join_path(self.url, collection, artifact_name)

    def _version_numbers(self, artifact_name: str, collection: str) -> t.List[int]:
        """The version numbers of an artifact, unsorted, empty if there are none."""
        try:
            entries = self.fs.ls(self._artifact_dir(artifact_name, collection), detail=True)
        except FileNotFoundError:
            return []
        names = (entry["name"].split("/")[-1] for entry in entries)
        return [int(name[1:]) for name in names if VERSION_PATTERN.fullmatch(name)]

    def _check_version(self, version: str) -> None:
        """Reject a version string that does not name a numbered version directory.

        Args:
            version (str): The version string to check.

        Raises:
            ValueError: If the version is not of the form ``v<number>``.
        """
        if not VERSION_PATTERN.fullmatch(version):
            raise ValueError(f"'{version}' is not a version. Versions are numbered, such as 'v0' or 'v3'.")

    def artifact_url(self, artifact_name: str, version: str, collection: t.Optional[str] = None) -> str:
        """Where a version's contents live, under this manager's root.

        The version does not have to exist yet, so this also locates a version returned by
        :meth:`reserve_version` before anything is written into it.

        Args:
            artifact_name (str): The artifact name.
            version (str): A concrete version such as ``"v3"``.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            str: The URL of that version's contents.

        Raises:
            ValueError: If the version is not of the form ``v<number>``, which would point
                at something that is not a version, such as the metadata directory.
        """
        self._check_version(version)
        collection = self._collection(collection)
        return join_path(self._artifact_dir(artifact_name, collection), version)

    def resolve(
        self,
        artifact_name: str,
        collection: t.Optional[str] = None,
        version: t.Optional[str] = None,
    ) -> Artifact:
        """Name a concrete version of an artifact, without transferring anything.

        Versions are numbered directories under the artifact, so the most recent one is the
        highest number present.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            version (Optional[str]): A version such as ``"v3"``. None or ``"latest"`` resolves
                to the highest-numbered version.

        Returns:
            Artifact: The resolved artifact, whose version is never ``"latest"``.

        Raises:
            FileNotFoundError: If the artifact has no versions, or not the one asked for.
            ValueError: If the version is neither ``"latest"`` nor of the form ``v<number>``.
        """
        collection = self._collection(collection)
        if version is None or version == "latest":
            numbers = self._version_numbers(artifact_name, collection)
            if not numbers:
                raise FileNotFoundError(f"Artifact '{artifact_name}' has no versions in collection '{collection}'")
            version = f"v{max(numbers)}"
        elif not self.fs.exists(self.artifact_url(artifact_name, version, collection)):
            raise FileNotFoundError(
                f"Artifact '{artifact_name}' has no version '{version}' in collection '{collection}'"
            )
        return Artifact(name=artifact_name, collection=collection, version=version)

    def reserve_version(self, artifact_name: str, collection: t.Optional[str] = None) -> Artifact:
        """Reserve the next version of an artifact for a write that happens in place.

        Use this when the data is too large to build locally and upload with
        :meth:`log_files`: it assigns the next version number, and the caller writes into
        :meth:`artifact_url` directly. :meth:`log_files` reserves its version the same way.

        What a reservation holds depends on the backend. On a local filesystem ``mkdirs``
        creates the directory, so the number stays taken even if nothing is written into it
        and :meth:`resolve` can return an empty version. An object store has no directories,
        so a version nobody wrote into is absent and the next caller is handed the same
        number. Write promptly either way.

        Reserving is not atomic. Two callers reading the same highest version are both given
        the one after it, so give concurrent writers their own artifact names or serialize
        them.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            Artifact: The next version, ready to be written into.
        """
        collection = self._collection(collection)
        numbers = self._version_numbers(artifact_name, collection)
        version = f"v{max(numbers) + 1}" if numbers else "v0"
        self.fs.mkdirs(self.artifact_url(artifact_name, version, collection), exist_ok=True)
        return Artifact(name=artifact_name, collection=collection, version=version)

    def remove_version(self, artifact_name: str, version: str, collection: t.Optional[str] = None) -> None:
        """Delete one version's directory and everything under it, irreversibly.

        The newest version is refused. :meth:`reserve_version` assigns ``max(numbers) + 1``,
        so removing the highest hands that number out again and the next write would land on
        a version some record already names.

        Args:
            artifact_name (str): The artifact name.
            version (str): The version to remove, such as ``"v3"``.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Raises:
            FileNotFoundError: If the version is not there.
            ValueError: If it is the newest version of its artifact, or is not of the form
                ``v<number>``.
        """
        collection = self._collection(collection)
        artifact = self.resolve(artifact_name, collection, version)
        if artifact == self.resolve(artifact_name, collection):
            raise ValueError(
                f"Version '{artifact.version}' is the newest version of artifact '{artifact_name}' in collection "
                f"'{collection}', and removing it would free a number that reserve_version hands out again. "
                "Remove older versions instead."
            )
        self.fs.rm(self.artifact_url(artifact_name, artifact.version, collection), recursive=True)

    def set_description(self, artifact_name: str, description: str, collection: t.Optional[str] = None) -> None:
        """Record an artifact's description, which belongs to the artifact and not to a version.

        :meth:`log_files` writes the description as part of logging. A write that happens
        in place has no such step, so the description is exposed on its own.

        Args:
            artifact_name (str): The artifact name.
            description (str): The description to record.
            collection (Optional[str]): The collection name. Defaults to the active collection.
        """
        collection = self._collection(collection)
        meta_dir = join_path(self._artifact_dir(artifact_name, collection), ARTIFACT_META_DIR)
        self.fs.mkdirs(meta_dir, exist_ok=True)
        with self.fs.open(join_path(meta_dir, ARTIFACT_DESCRIPTION_FILE), "w") as f:
            f.write(description)

    def log_files(
        self,
        artifact_name: str,
        local_path: str,
        description: str,
        collection: t.Optional[str] = None,
        artifact_path: t.Optional[str] = None,
    ) -> Artifact:
        """Log a file or folder as an artifact.

        This method uploads the file (or folder) located at `local_path` to the artifact store.
        If `artifact_path` is provided, the file is uploaded to a subpath within the artifact;
        otherwise, the entire folder is uploaded.

        Args:
            artifact_name (str): The artifact name.
            local_path (str): The local path to the file or folder.
            description:
                Description of the artifact.
                Will be logged at <artifact_root>/ARTIFACT_META_DIR/ARTIFACT_DESCRIPTION_FILE
                and serves to reduce undocumented artifact clutter.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            artifact_path (Optional[str]): The subpath within the artifact for single file uploads.
        Returns:
            Artifact: The logged artifact with its metadata (name, collection, version).
        """
        collection = self._collection(collection)
        artifact = self.reserve_version(artifact_name, collection)
        target_dir = self.artifact_url(artifact_name, artifact.version, collection)

        self.set_description(artifact_name, description, collection)

        if artifact_path:
            # Upload a single file to target_dir/artifact_path.
            target_file = join_path(target_dir, artifact_path)
            fs = get_fs_from_url(target_file)
            parent_dir = fs._parent(target_file)
            self.fs.mkdirs(parent_dir, exist_ok=True)
            self.fs.put(local_path, target_file, recursive=False)
            logged_location = target_file
        else:
            # Upload an entire folder.
            self.fs.put(local_path, target_dir, recursive=True)
            logged_location = target_dir

        logger.info(f"Logged artifact '{artifact_name}' to {logged_location}")

        return artifact

    def list_artifacts(self, collection: str = None) -> t.List[str]:
        """List the names of the artifacts in a collection.

        Args:
            collection (str): Collection name. Defaults to the active collection.

        Returns:
            List[str]: The artifact names, empty if the collection does not exist.
        """
        collection = self._collection(collection)
        try:
            entries = self.fs.ls(join_path(self.url, collection), detail=True)
        except FileNotFoundError:
            return []
        return [entry["name"].split("/")[-1] for entry in entries if entry.get("type") == "directory"]

    def list_versions(self, artifact_name: str, collection: str = None) -> t.List[str]:
        """Get sorted versions for an artifact.

        Args:
            artifact_name (str): Artifact name.
            collection (str): Collection name. Defaults to the active collection.

        Returns:
            List[str]: List of version strings sorted by version number (e.g., ["v0", "v1", "v2"]).
        """
        collection = self._collection(collection)
        return [f"v{n}" for n in sorted(self._version_numbers(artifact_name, collection))]

    def download_artifact(
        self,
        artifact_name: str,
        collection: t.Optional[str] = None,
        version: t.Optional[str] = None,
        to: t.Optional[str] = None,
    ) -> t.Union[Artifact, TmpArtifact]:
        """Download an artifact from the artifact store.

        If a destination path `to` is provided, the contents of the artifact version are copied
        there. Otherwise, a TmpArtifact context manager is returned.

        Args:
            artifact_name (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            version (Optional[str]): The version of the artifact. If None or "latest", the latest version is used.
            to (Optional[str]): The destination path. If not provided, a temporary directory is used.

        Returns:
            Union[Artifact, TmpArtifact]: If `to` is provided, returns an Artifact with metadata.
                Otherwise, returns a TmpArtifact context manager that also has an `artifact` property.

        Raises:
            FileNotFoundError: If the artifact has no versions, or not the one asked for.
            ValueError: If the version is neither ``"latest"`` nor of the form ``v<number>``.
        """
        artifact = self.resolve(artifact_name, collection, version)
        if to is not None:
            url = self.artifact_url(artifact_name, artifact.version, artifact.collection)
            self.fs.get(join_path(url, "*"), to, recursive=True)
            return artifact
        else:
            return TmpArtifact(self, artifact.collection, artifact_name, artifact.version)
