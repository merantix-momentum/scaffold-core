import pathlib
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlparse

from aim.ext.cleanup import AutoClean
from aim.storage.artifacts.artifact_storage import AbstractArtifactStorage

from scaffold.data.fs import get_fs_from_url


class FsspecArtifactStorage(AbstractArtifactStorage):
    """Fsspec storage backend for Aim."""

    def __init__(self, storage_root: str, max_upload_workers: int = 4):
        """
        Args:
            storage_root: URL with an optional prefix (e.g., 'gs://my-bucket/path/prefix').
            fs: Optional filesystem object to be used. It will be created based on the storage root if not specified.

        Note: Make sure to have the correct fsspec dependencies
        installed for the protocol you want to use (e.g., 'gcsfs' for 'gs://').
        """
        super().__init__(storage_root)
        self._storage_root_str = storage_root
        parsed_url = urlparse(storage_root)
        self._storage_root = pathlib.Path(parsed_url.netloc) / pathlib.Path(parsed_url.path.lstrip("/"))
        self.scheme = parsed_url.scheme + "://"

        self.thread_pool = ThreadPoolExecutor(max_workers=max_upload_workers, thread_name_prefix="fs-upload")

        # make sure all threads finish uploading before shutting down
        self._resources = FsspecArtifactStorageAutoClean(self)

    def upload_artifact(self, file_path: str, artifact_path: str, block: bool = False):
        """
        Using fsspec, upload a local file to the artifact storage in a non-blocking manner by default.

        Args:
            file_path: Local path to the file to upload.
            artifact_path: Path to the artifact in storage, relative to the storage root specified in the constructor.
            block: If True, the method will block until the upload is complete.
        """

        dest_path = pathlib.Path(self._storage_root) / artifact_path.lstrip("/")
        fs = get_fs_from_url(self._storage_root_str)
        fs.makedirs(self.scheme + dest_path.parent.as_posix(), exist_ok=True)
        future = self.thread_pool.submit(fs.put_file, file_path, self.scheme + dest_path.as_posix())

        if block:
            future.result()

    def download_artifact(self, artifact_path: str, dest_dir: Optional[str] = None) -> str:
        """
        Using fsspec, download an artifact to a local directory.

        Args:
            artifact_path: path to the artifact in storage, relative to the storage root specified in the constructor.
            dest_dir: Local directory to download the artifact to. If None, a temporary directory is created.
        Returns:
              The local path to the downloaded artifact.
        """

        dest_dir = pathlib.Path(tempfile.mkdtemp() if not dest_dir else dest_dir)

        source_path = pathlib.Path(self._storage_root) / artifact_path.lstrip("/")
        dest_path = dest_dir / source_path.name

        fs = get_fs_from_url(self._storage_root_str)
        fs.get_file(self.scheme + source_path.as_posix(), dest_path.as_posix())

        return dest_path.as_posix()

    def delete_artifact(self, artifact_path: str):
        path = pathlib.Path(self._storage_root) / artifact_path.lstrip("/")
        fs = get_fs_from_url(self._storage_root_str)
        fs.rm_file(self.scheme + path.as_posix())


class FsspecArtifactStorageAutoClean(AutoClean["FsspecArtifactStorage"]):
    """Makes sure all upload threads finish before the FsspecArtifactStorage is destroyed."""

    def __init__(self, instance: "FsspecArtifactStorage"):
        super().__init__(instance)
        self._thread_pool = instance.thread_pool

    def _close(self):
        # wait for all threads to finish
        self._thread_pool.shutdown(wait=True)
