import typing as t

from scaffold.data.artifact_manager.base import ArtifactManager, TmpArtifact
from scaffold.data.fs import get_fs_from_url, join_path


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

    def exists_in_collection(self, artifact: str, collection: t.Optional[str] = None) -> bool:
        """Check if an artifact exists in a specific collection.

        Args:
            artifact (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.

        Returns:
            bool: True if the artifact exists, False otherwise.
        """
        collection = collection or self.active_collection
        artifact_dir = join_path(self.url, collection, artifact)
        return self.fs.exists(artifact_dir)

    def log_files(
        self,
        artifact_name: str,
        local_path: str,
        collection: t.Optional[str] = None,
        artifact_path: t.Optional[str] = None,
    ) -> None:
        """Log a file or folder as an artifact.

        This method uploads the file (or folder) located at `local_path` to the artifact store.
        If `artifact_path` is provided, the file is uploaded to a subpath within the artifact;
        otherwise, the entire folder is uploaded.

        Args:
            artifact_name (str): The artifact name.
            local_path (str): The local path to the file or folder.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            artifact_path (Optional[str]): The subpath within the artifact for single file uploads.
        """
        collection = collection or self.active_collection
        base_artifact_path = join_path(self.url, collection, artifact_name)
        # Determine new version; start at "v0"
        if self.fs.exists(base_artifact_path):
            try:
                entries = self.fs.ls(base_artifact_path, detail=True)
                version_nums: t.List[int] = []
                for entry in entries:
                    ver = entry["name"].split("/")[-1]
                    if ver.startswith("v") and ver[1:].isdigit():
                        version_nums.append(int(ver[1:]))
                new_version = f"v{max(version_nums) + 1}" if version_nums else "v0"
            except Exception:
                new_version = "v0"
        else:
            new_version = "v0"
        target_dir = join_path(base_artifact_path, new_version)

        if artifact_path:
            # Upload a single file to target_dir/artifact_path.
            target_file = join_path(target_dir, artifact_path)
            fs = get_fs_from_url(target_file)
            parent_dir = fs._parent(target_file)
            self.fs.mkdirs(parent_dir, exist_ok=True)
            self.fs.put(local_path, target_file, recursive=False)
        else:
            # Upload an entire folder.
            if not self.fs.exists(target_dir):
                self.fs.mkdirs(target_dir, exist_ok=True)
            self.fs.put(local_path, target_dir, recursive=True)

    def download_artifact(
        self,
        artifact: str,
        collection: t.Optional[str] = None,
        version: t.Optional[str] = None,
        to: t.Optional[str] = None,
    ) -> t.Union[str, TmpArtifact]:
        """Download an artifact from the artifact store.

        If a destination path `to` is provided, the contents of the artifact version are copied
        there. Otherwise, a TmpArtifact context manager is returned.

        Args:
            artifact (str): The artifact name.
            collection (Optional[str]): The collection name. Defaults to the active collection.
            version (Optional[str]): The version of the artifact. If None or "latest", the latest version is used.
            to (Optional[str]): The destination path. If not provided, a temporary directory is used.

        Returns:
            Union[str, TmpArtifact]: The destination path or a TmpArtifact context manager.
        """
        collection = collection or self.active_collection
        base_artifact_path = join_path(self.url, collection, artifact)
        if version is None or version == "latest":
            if not self.fs.exists(base_artifact_path):
                raise ValueError(f"Artifact {artifact} not found in collection {collection}")
            entries = self.fs.ls(base_artifact_path, detail=True)
            version_nums: t.List[int] = []
            for entry in entries:
                ver = entry["name"].split("/")[-1]
                if ver.startswith("v") and ver[1:].isdigit():
                    version_nums.append(int(ver[1:]))
            if not version_nums:
                raise ValueError(f"No version found for artifact {artifact} in collection {collection}")
            version = f"v{max(version_nums)}"
        remote_artifact_path = join_path(base_artifact_path, version)
        if to is not None:
            self.fs.get(join_path(remote_artifact_path, "*"), to, recursive=True)
            return to
        else:
            return TmpArtifact(self, collection, artifact, version)
