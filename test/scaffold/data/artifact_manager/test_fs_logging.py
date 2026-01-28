import shutil
import tempfile
import uuid

import pytest

from scaffold.data.artifact_manager.base import Artifact
from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager
from scaffold.data.fs import get_fs_from_url, join_path

CLOUD_TMP_BUCKET = "gs://mxm-octo-tmp"


@pytest.fixture
def temp_store_dir():
    # Create a temporary directory (a local URL)
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def temp_src_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


# This fixture is parameterized to run tests for both a local and a cloud store.
@pytest.fixture(params=["local", "cloud"])
def store_info(request, temp_store_dir) -> tuple[str, str]:
    store_type = request.param
    if store_type == "local":
        yield temp_store_dir, store_type
    else:
        # Create a unique subdirectory in the bucket "gs://mxm-octo-tmp"
        cloud_url = join_path(CLOUD_TMP_BUCKET, "scaffold_test_run", uuid.uuid4().hex)
        fs = get_fs_from_url(cloud_url)
        try:
            # Attempt a simple operation (listing the bucket root) to test access.
            fs.listdir(CLOUD_TMP_BUCKET)
        except Exception:
            pytest.skip("Skipping cloud tests: no bucket access available.")
        yield cloud_url, store_type
        fs.rm(cloud_url, recursive=True)


@pytest.fixture
def artifact_manager(store_info):
    url, store_type = store_info
    manager = FileSystemArtifactManager(url=url)
    return manager, store_type


def test_join_path_local():
    result = join_path("/tmp/", "folder/", "subfolder/")
    assert result == "/tmp/folder/subfolder", f"Got {result}"


def test_join_path_gbucket():
    result = join_path("gs://mybucket/", "folder/", "subfolder/")
    assert result == "gs://mybucket/folder/subfolder", f"Got {result}"


def test_log_file(temp_src_dir, artifact_manager):
    """Test logging individual files using log_files."""
    manager, store_type = artifact_manager
    collection = "my_collection"
    artifact_name = "foo_file"

    # Create a source file using join_path (temp_src_dir is provided by tempfile)
    src_file = join_path(temp_src_dir, "foo.txt")
    with open(src_file, "w") as f:
        f.write("Test: Foo")

    artifact = manager.log_files(artifact_name, src_file, collection, artifact_path="foo.txt")
    assert isinstance(artifact, Artifact)
    assert artifact.name == artifact_name
    assert artifact.collection == collection
    assert artifact.version == "v0"
    target_file = join_path(manager.url, collection, artifact_name, "v0", "foo.txt")
    fs = get_fs_from_url(manager.url)
    assert fs.exists(target_file)
    with fs.open(target_file, "rt") as f:
        content = f.read()
    assert content == "Test: Foo"

    # Log a second file for the same artifact; expect version "v1"
    src_file2 = join_path(temp_src_dir, "bar.txt")
    with open(src_file2, "w") as f:
        f.write("Test: Bar")
    artifact2 = manager.log_files(artifact_name, src_file2, collection, artifact_path="bar.txt")
    assert isinstance(artifact2, Artifact)
    assert artifact2.name == artifact_name
    assert artifact2.collection == collection
    assert artifact2.version == "v1"
    target_file2 = join_path(manager.url, collection, artifact_name, "v1", "bar.txt")
    assert fs.exists(target_file2)
    with fs.open(target_file2, "rt") as f:
        content2 = f.read()
    assert content2 == "Test: Bar"


def test_exists(temp_src_dir, artifact_manager):
    """Test artifact existence checks via fsspec calls."""
    manager, store_type = artifact_manager
    collection = "my_collection"
    for filename, artifact in [("foo.txt", "foo"), ("bar.txt", "bar")]:
        src_file = join_path(temp_src_dir, filename)
        with open(src_file, "w") as f:
            f.write("Test")
        manager.log_files(artifact, src_file, collection, artifact_path=filename)
    assert manager.exists("foo")
    assert manager.exists("bar")
    assert manager.exists_in_collection("foo", collection)
    assert manager.exists_in_collection("bar", collection)
    assert not manager.exists_in_collection("foo", "default")


def test_get_file(temp_src_dir, artifact_manager):
    """Test downloading logged files using download_artifact without os module calls."""
    manager, store_type = artifact_manager
    collection = "my_collection"
    artifact_name = "bar_file"
    file_descriptions = [
        ("bar.txt", "Test: Bar"),
        ("baz.txt", "Test: Baz"),
    ]
    for filename, content in file_descriptions:
        src_file = join_path(temp_src_dir, filename)
        with open(src_file, "w") as f:
            f.write(content)
        manager.log_files(artifact_name, src_file, collection, artifact_path=filename)

    # Download version "v0" (first version)
    download_dir = join_path(temp_src_dir, "downloaded")
    fs_local = get_fs_from_url(download_dir)
    fs_local.mkdirs(download_dir, exist_ok=True)
    downloaded_artifact = manager.download_artifact(artifact_name, collection, version="v0", to=download_dir)
    assert isinstance(downloaded_artifact, Artifact)
    assert downloaded_artifact.name == artifact_name
    assert downloaded_artifact.collection == collection
    assert downloaded_artifact.version == "v0"
    target_file = join_path(download_dir, "bar.txt")
    assert fs_local.exists(target_file)
    with fs_local.open(target_file, "rt") as f:
        content_bar = f.read()
    assert content_bar == "Test: Bar"

    # Download version "v1" (second version)
    download_dir2 = join_path(temp_src_dir, "downloaded2")
    fs_local.mkdirs(download_dir2, exist_ok=True)
    downloaded_artifact2 = manager.download_artifact(artifact_name, collection, version="v1", to=download_dir2)
    assert isinstance(downloaded_artifact2, Artifact)
    assert downloaded_artifact2.name == artifact_name
    assert downloaded_artifact2.collection == collection
    assert downloaded_artifact2.version == "v1"
    target_file2 = join_path(download_dir2, "baz.txt")
    assert fs_local.exists(target_file2)
    with fs_local.open(target_file2, "rt") as f:
        content_baz = f.read()
    assert content_baz == "Test: Baz"


def test_log_folder_and_download(temp_src_dir, artifact_manager):
    """Test logging a folder via log_folder and then downloading its contents."""
    manager, store_type = artifact_manager
    collection = "my_collection"
    test_files = [
        ("foo.txt", "Test: Foo"),
        ("bar.txt", "Test: Bar"),
        ("baz.txt", "Test: Baz"),
    ]
    logger = manager.log_folder("my_artifact", collection)
    with logger as folder:
        for filename, content in test_files:
            file_path = join_path(folder, filename)
            with open(file_path, "w") as f:
                f.write(content)
    # Verify artifact property is available after context exit
    assert logger.artifact is not None
    assert isinstance(logger.artifact, Artifact)
    assert logger.artifact.name == "my_artifact"
    assert logger.artifact.collection == collection
    assert logger.artifact.version == "v0"
    assert manager.exists_in_collection("my_artifact", collection)
    downloaded_artifact = manager.download_artifact("my_artifact", collection, version="v0", to=temp_src_dir)
    assert isinstance(downloaded_artifact, Artifact)
    assert downloaded_artifact.name == "my_artifact"
    assert downloaded_artifact.collection == collection
    assert downloaded_artifact.version == "v0"
    local_downloaded_path = temp_src_dir
    fs_local = get_fs_from_url(local_downloaded_path)
    for filename, content in test_files:
        downloaded_file = join_path(local_downloaded_path, filename)
        assert fs_local.exists(downloaded_file)
        with fs_local.open(downloaded_file, "rt") as f:
            read_content = f.read()
        assert read_content == content


def test_download_tmp(temp_src_dir, artifact_manager):
    """Test temporary download of an artifact via the context manager interface."""
    manager, store_type = artifact_manager
    collection = "my_artifact_collection"
    test_files = {"foo.txt": "Test: Foo", "bar.txt": "Test: Bar", "baz.txt": "Test: Baz"}
    with manager.log_folder("my_artifact", collection) as tmp_dir:
        for filename, content in test_files.items():
            with open(join_path(tmp_dir, filename), "w") as f:
                f.write(content)
    tmp_artifact = manager.download_artifact("my_artifact", collection, version="v0")
    # Verify TmpArtifact has artifact property
    assert hasattr(tmp_artifact, "artifact")
    assert isinstance(tmp_artifact.artifact, Artifact)
    assert tmp_artifact.artifact.name == "my_artifact"
    assert tmp_artifact.artifact.collection == collection
    assert tmp_artifact.artifact.version == "v0"
    with tmp_artifact as tmp_download_dir:
        fs_temp = get_fs_from_url(tmp_download_dir)
        # List files in temp_path using fs.ls
        files_list = fs_temp.ls(tmp_download_dir)
        for file_path in files_list:
            base = file_path.split("/")[-1]
            with fs_temp.open(file_path, "rt") as f:
                file_content = f.read()
            assert file_content == test_files.get(base)
