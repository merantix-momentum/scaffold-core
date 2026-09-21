import logging
import typing as t

from scaffold.constants import ARTIFACT_DESCRIPTION_FILE, ARTIFACT_META_DIR
from scaffold.data.artifact_manager.base import Artifact, ArtifactManager, TmpArtifact
from scaffold.data.fs import get_fs_from_url, join_path

logger = logging.getLogger(__name__)


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
        collection = collection or self.active_collection
        artifact_dir = join_path(self.url, collection, artifact_name)
        return self.fs.exists(artifact_dir)

    def _artifact_dir(self, artifact_name: str, collection: t.Optional[str] = None) -> str:
        """The directory holding every version of one artifact."""
        return join_path(self.url, collection or self.active_collection, artifact_name)

    def _version_numbers(self, base_artifact_path: str) -> t.List[int]:
        """The version numbers under an artifact directory, unsorted, empty if there are none."""
        if not self.fs.exists(base_artifact_path):
            return []
        try:
            entries = self.fs.ls(base_artifact_path, detail=True)
        except FileNotFoundError:
            return []
        return [
            int(ver[1:])
            for entry in entries
            if (ver := entry["name"].split("/")[-1]).startswith("v") and ver[1:].isdigit()
        ]

    def artifact_url(self, artifact: Artifact) -> str:
        """Where a version's contents live, under this manager's root.

        Args:
            artifact (Artifact): The artifact to locate, at a concrete version.

        Returns:
            str: The URL of that version's contents.
        """
        return join_path(self.url, artifact.collection, artifact.name, artifact.version)

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
        """
        collection = collection or self.active_collection
        base_artifact_path = self._artifact_dir(artifact_name, collection)
        if version is not None and version != "latest":
            if not self.fs.exists(join_path(base_artifact_path, version)):
                raise FileNotFoundError(
                    f"Artifact '{artifact_name}' has no version '{version}' in collection '{collection}'"
                )
            return Artifact(name=artifact_name, collection=collection, version=version)
        numbers = self._version_numbers(base_artifact_path)
        if not numbers:
            raise FileNotFoundError(f"Artifact '{artifact_name}' has no versions in collection '{collection}'")
        return Artifact(name=artifact_name, collection=collection, version=f"v{max(numbers)}")

    def next_version(self, artifact_name: str, collection: t.Optional[str] = None) -> Artifact:
        """Reserve the next version of an artifact for a write that happens in place.

        Use this when the data is too large to build locally and upload with
        :meth:`log_files`: it assigns the next version number, and the caller writes into
        :meth:`artifact_url` directly.

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
        collection = collection or self.active_collection
        base_artifact_path = self._artifact_dir(artifact_name, collection)
        numbers = self._version_numbers(base_artifact_path)
        artifact = Artifact(
            name=artifact_name,
            collection=collection,
            version=f"v{max(numbers) + 1}" if numbers else "v0",
        )
        self.fs.mkdirs(self.artifact_url(artifact), exist_ok=True)
        return artifact

    def remove_version(self, artifact: Artifact) -> None:
        """Delete one version's directory and everything under it, irreversibly.

        The newest version is refused. :meth:`next_version` assigns ``max(numbers) + 1``, so
        removing the highest hands that number out again and the next write would land on a
        version some record already names.

        Args:
            artifact (Artifact): The version to remove, at a concrete version.

        Raises:
            FileNotFoundError: If the version is not there.
            ValueError: If it is the newest version of its artifact.
        """
        url = self.artifact_url(artifact)
        if not self.fs.exists(url):
            raise FileNotFoundError(f"{artifact.collection}/{artifact.name}:{artifact.version} is not there")
        numbers = self._version_numbers(self._artifact_dir(artifact.name, artifact.collection))
        if numbers and artifact.version == f"v{max(numbers)}":
            raise ValueError(
                f"{artifact.collection}/{artifact.name}:{artifact.version} is the newest version, and removing it "
                "would free a number that next_version hands out again. Remove older versions instead."
            )
        self.fs.rm(url, recursive=True)

    def set_description(self, artifact_name: str, description: str, collection: t.Optional[str] = None) -> None:
        """Record an artifact's description, which belongs to the artifact and not to a version.

        :meth:`log_files` writes the description as part of logging. A write that happens
        in place has no such step, so the description is exposed on its own.

        Args:
            artifact_name (str): The artifact name.
            description (str): The description to record.
            collection (Optional[str]): The collection name. Defaults to the active collection.
        """
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
        collection = collection or self.active_collection
        version_nums = self._version_numbers(self._artifact_dir(artifact_name, collection))
        new_version = f"v{max(version_nums) + 1}" if version_nums else "v0"
        artifact = Artifact(name=artifact_name, collection=collection, version=new_version)
        target_dir = self.artifact_url(artifact)

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
            if not self.fs.exists(target_dir):
                self.fs.mkdirs(target_dir, exist_ok=True)
            self.fs.put(local_path, target_dir, recursive=True)
            logged_location = target_dir

        logger.info(f"Logged artifact '{artifact_name}' to {logged_location}")

        return artifact

    def list_artifacts(self, collection: str = None) -> t.List[str]:
        """Get sorted versions for an artifact.

        Args:
            collection (str): Collection name.

        Returns:
            List[str]: List of artifact strings.
        """
        if collection is None:
            collection = self.active_collection

        base_path = join_path(self.url, collection)
        if not self.fs.exists(base_path):
            return []

        try:
            entries = self.fs.ls(base_path, detail=True)
            entries = [entry["name"].split("/")[-1] for entry in entries if entry.get("type") == "directory"]
            return entries
        except Exception:
            return []

    def list_versions(self, artifact_name: str, collection: str = None) -> t.List[str]:
        """Get sorted versions for an artifact.

        Args:
            artifact_name (str): Artifact name.
            collection (str): Collection name.

        Returns:
            List[str]: List of version strings sorted by version number (e.g., ["v0", "v1", "v2"]).
        """
        if collection is None:
            collection = self.active_collection

        return [f"v{n}" for n in sorted(self._version_numbers(self._artifact_dir(artifact_name, collection)))]

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
            ValueError: If the artifact has no versions, or not the one asked for.
        """
        collection = collection or self.active_collection
        try:
            artifact = self.resolve(artifact_name, collection, version)
        except FileNotFoundError as error:
            # Callers catch ValueError from this method, so keep that type here.
            raise ValueError(str(error)) from error
        if to is not None:
            self.fs.get(join_path(self.artifact_url(artifact), "*"), to, recursive=True)
            return artifact
        else:
            return TmpArtifact(self, collection, artifact_name, artifact.version)
