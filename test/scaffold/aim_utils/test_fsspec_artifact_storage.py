import importlib
import sys


def test_register_fsspec_to_aim_no_crash():
    """importing and calling register_fsspec_to_aim should not crash if aim or fsspec are not installed"""

    # Remove aim and fsspec from sys.modules if present
    sys_modules_backup = sys.modules.copy()
    sys.modules["aim"] = None
    sys.modules["fsspec"] = None
    try:
        aim_core = importlib.import_module("scaffold.aim_utils.core")
        aim_core.register_fsspec_to_aim()  # Should not raise
    finally:
        sys.modules.clear()
        sys.modules.update(sys_modules_backup)


def test_registers_all_fsspec_protocols():
    """
    All the fsspec installation's available schemas should be available
    to the aim artifact manager after calling register_fsspec_to_aim
    """
    import fsspec
    from aim.storage.artifacts.artifact_registry import registry

    from scaffold.aim_utils.core import register_fsspec_to_aim

    register_fsspec_to_aim()
    for protocol in fsspec.available_protocols():
        assert protocol in registry.registry


def test_fsspec_artifact_storage_roundtrip(tmp_path):
    """The storage system works (basic put/get/delete roundtrip)"""
    from scaffold.aim_utils.fsspec_artifact_storage import FsspecArtifactStorage

    # Use local filesystem via fsspec for testing
    storage_root = f"file://{tmp_path}/storage"
    artifact_storage = FsspecArtifactStorage(storage_root)

    # Create a test file to upload
    src_file = tmp_path / "test.txt"
    content = b"hello world"
    src_file.write_bytes(content)

    # Upload the file
    artifact_path = "folder/test.txt"
    artifact_storage.upload_artifact(str(src_file), artifact_path, block=True)

    # Download the file to a new location
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    downloaded_path = artifact_storage.download_artifact(artifact_path, str(download_dir))

    # Check that the downloaded file matches the original
    assert (download_dir / "test.txt").read_bytes() == content
    assert downloaded_path == str(download_dir / "test.txt")

    # Delete the artifact
    artifact_storage.delete_artifact(artifact_path)

    # Ensure the file is deleted from storage
    import fsspec

    fs = fsspec.filesystem("file")
    storage_file_path = tmp_path / "storage" / "folder" / "test.txt"
    assert not fs.exists(str(storage_file_path))
