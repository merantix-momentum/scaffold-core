import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from scaffold.constants import ARTIFACT_AGENTSMD_FILE, ARTIFACT_META_DIR
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

    # Logging no longer writes an AGENTS.md; it is set explicitly via set_agentsmd.
    agentsmd_file = join_path(manager.url, collection, artifact_name, ARTIFACT_META_DIR, ARTIFACT_AGENTSMD_FILE)
    assert not fs.exists(agentsmd_file)

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


def write_into(manager, artifact, filename, content):
    with manager.fs.open(join_path(manager.artifact_url(artifact.name, artifact.version), filename), "w") as f:
        f.write(content)


def test_resolve_names_a_concrete_version_without_transferring_anything(artifact_manager, temp_src_dir):
    """A concrete version and its location are available without downloading anything."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    first = artifact_manager.log_files("data", temp_src_dir)
    second = artifact_manager.log_files("data", temp_src_dir)

    assert artifact_manager.resolve("data") == second
    assert artifact_manager.resolve("data", version="latest") == second
    assert artifact_manager.resolve("data", version="v0") == first
    assert artifact_manager.artifact_url("data", "v0").endswith(f"{first.collection}/data/v0")
    assert artifact_manager.fs.exists(artifact_manager.artifact_url("data", "v0"))


def test_resolve_refuses_what_is_not_there_rather_than_guessing(artifact_manager, temp_src_dir):
    """A missing version and a missing artifact each raise instead of falling back."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)

    with pytest.raises(FileNotFoundError, match="v7"):
        artifact_manager.resolve("data", version="v7")
    with pytest.raises(FileNotFoundError, match="no versions"):
        artifact_manager.resolve("never-logged")


def test_download_raises_the_same_error_as_resolve_for_what_is_not_there(artifact_manager, temp_src_dir):
    """download_artifact resolves first, so a missing artifact or version is a FileNotFoundError."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)

    with pytest.raises(FileNotFoundError, match="v7"):
        artifact_manager.download_artifact("data", version="v7", to=temp_src_dir)
    with pytest.raises(FileNotFoundError, match="no versions"):
        artifact_manager.download_artifact("never-logged")


def test_reserve_version_hands_out_a_place_to_write_in(artifact_manager):
    """A dataset too large to build locally is written into its version in place."""
    artifact_manager, _ = artifact_manager
    first = artifact_manager.reserve_version("store")
    write_into(artifact_manager, first, "part.bin", "rows")
    second = artifact_manager.reserve_version("store")
    write_into(artifact_manager, second, "part.bin", "more rows")

    assert (first.name, first.version) == ("store", "v0")
    assert artifact_manager.list_versions("store") == ["v0", "v1"]
    assert artifact_manager.resolve("store") == second


def test_a_version_nobody_wrote_into_is_handed_out_again(artifact_manager):
    """An object store has no empty directories, so a number is only taken once it is used."""
    artifact_manager, store_type = artifact_manager
    if store_type != "cloud":
        pytest.skip("a real filesystem does keep the empty directory")

    assert artifact_manager.reserve_version("store").version == "v0"
    reused = artifact_manager.reserve_version("store")
    assert reused.version == "v0"

    write_into(artifact_manager, reused, "part.bin", "rows")

    assert artifact_manager.reserve_version("store").version == "v1"


def test_a_reserved_version_and_a_logged_one_share_one_counter(artifact_manager, temp_src_dir):
    """reserve_version and log_files draw from one sequence, so neither overwrites the other."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")

    first = artifact_manager.reserve_version("mixed")
    write_into(artifact_manager, first, "part.bin", "rows")
    logged = artifact_manager.log_files("mixed", temp_src_dir)
    third = artifact_manager.reserve_version("mixed")

    assert (first.version, logged.version, third.version) == ("v0", "v1", "v2")


def test_agentsmd_can_be_set_without_logging_files(artifact_manager):
    """The AGENTS.md belongs to the artifact, so an in-place write can set it on its own."""
    artifact_manager, _ = artifact_manager
    artifact_manager.reserve_version("store")
    artifact_manager.set_agentsmd("store", "written in place")

    agentsmd = join_path(
        artifact_manager.url, artifact_manager.active_collection, "store", ARTIFACT_META_DIR, ARTIFACT_AGENTSMD_FILE
    )
    with artifact_manager.fs.open(agentsmd) as f:
        assert f.read().decode() == "written in place"
    assert artifact_manager.read_agentsmd("store") == "written in place"


def test_agentsmd_can_be_set_from_a_local_file(artifact_manager, temp_src_dir):
    """A Path is read and its contents uploaded, rather than the path itself being written."""
    artifact_manager, _ = artifact_manager
    local = Path(temp_src_dir) / "AGENTS.md"
    local.write_text("# store\none row per event", encoding="utf-8")
    artifact_manager.reserve_version("store")

    artifact_manager.set_agentsmd("store", local)

    assert artifact_manager.read_agentsmd("store") == "# store\none row per event"


def test_setting_agentsmd_from_a_path_that_is_not_a_file_is_refused(tmp_path, temp_src_dir):
    """A directory or missing path raises instead of silently writing nothing."""
    artifact_manager = FileSystemArtifactManager(url=str(tmp_path))
    with pytest.raises(ValueError, match="is not a file"):
        artifact_manager.set_agentsmd("store", Path(temp_src_dir))
    with pytest.raises(ValueError, match="is not a file"):
        artifact_manager.set_agentsmd("store", Path(temp_src_dir) / "missing.md")


def test_setting_agentsmd_again_replaces_it(artifact_manager):
    """There is one AGENTS.md per artifact, not one per version."""
    artifact_manager, _ = artifact_manager
    artifact_manager.reserve_version("store")
    artifact_manager.set_agentsmd("store", "first")
    artifact_manager.reserve_version("store")
    artifact_manager.set_agentsmd("store", "second")

    assert artifact_manager.read_agentsmd("store") == "second"


def test_reading_agentsmd_that_was_never_set_returns_none(artifact_manager, temp_src_dir):
    """An artifact logged without an AGENTS.md reads back as None."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)

    assert artifact_manager.read_agentsmd("data") is None


def test_a_version_can_be_removed_so_a_run_that_keeps_checkpointing_does_not_grow(artifact_manager):
    """Removing a version drops its contents and leaves the rest of the artifact standing."""
    artifact_manager, _ = artifact_manager
    written = []
    for _ in range(3):
        version = artifact_manager.reserve_version("detector")
        write_into(artifact_manager, version, "state.bin", "weights")
        written.append(version)

    artifact_manager.remove_version("detector", "v0")

    assert artifact_manager.list_versions("detector") == ["v1", "v2"]
    assert not artifact_manager.fs.exists(artifact_manager.artifact_url("detector", "v0"))
    assert artifact_manager.resolve("detector") == written[2]


def test_removing_the_newest_version_is_refused_because_its_number_would_be_reused(artifact_manager):
    """reserve_version is max + 1, so freeing the top would put two writes at one address."""
    artifact_manager, _ = artifact_manager
    for _ in range(2):
        write_into(artifact_manager, artifact_manager.reserve_version("detector"), "state.bin", "weights")

    for newest in ["v1", "latest"]:
        with pytest.raises(ValueError, match="newest version"):
            artifact_manager.remove_version("detector", newest)

    assert artifact_manager.list_versions("detector") == ["v0", "v1"]


def test_removing_a_version_that_is_not_there_says_so(artifact_manager):
    """A request for a version that was never written reports that, rather than passing."""
    artifact_manager, _ = artifact_manager
    write_into(artifact_manager, artifact_manager.reserve_version("detector"), "state.bin", "weights")

    with pytest.raises(FileNotFoundError):
        artifact_manager.remove_version("detector", "v7")


def test_every_method_taking_a_version_accepts_only_numbered_ones(artifact_manager, temp_src_dir):
    """The metadata directory sits beside the versions and is not one of them, and v01 would alias v1."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)

    for not_a_version in [ARTIFACT_META_DIR, "latest-1", "v", "v1.2", "V0", "v01", "v0\n"]:
        for call in [
            lambda: artifact_manager.resolve("data", version=not_a_version),
            lambda: artifact_manager.download_artifact("data", version=not_a_version),
            lambda: artifact_manager.artifact_url("data", not_a_version),
            lambda: artifact_manager.remove_version("data", not_a_version),
        ]:
            with pytest.raises(ValueError, match="is not a version"):
                call()


def test_removing_the_metadata_directory_as_if_it_were_a_version_is_refused(artifact_manager, temp_src_dir):
    """rm on the metadata directory would take the AGENTS.md with it."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)
    artifact_manager.set_agentsmd("data", "desc")

    with pytest.raises(ValueError, match="is not a version"):
        artifact_manager.remove_version("data", ARTIFACT_META_DIR)

    agentsmd = join_path(
        artifact_manager.url, artifact_manager.active_collection, "data", ARTIFACT_META_DIR, ARTIFACT_AGENTSMD_FILE
    )
    assert artifact_manager.fs.exists(agentsmd)


def test_every_method_taking_a_collection_rejects_one_that_would_nest(artifact_manager, temp_src_dir):
    """A collection passed per call is held to the same rule as the active collection."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)

    for bad in ["a/b", "", "../default"]:
        for call in [
            lambda: artifact_manager.log_files("data", temp_src_dir, collection=bad),
            lambda: artifact_manager.log_folder("data", collection=bad),
            lambda: artifact_manager.reserve_version("data", collection=bad),
            lambda: artifact_manager.set_agentsmd("data", "desc", collection=bad),
            lambda: artifact_manager.read_agentsmd("data", collection=bad),
            lambda: artifact_manager.resolve("data", collection=bad),
            lambda: artifact_manager.download_artifact("data", collection=bad),
            lambda: artifact_manager.artifact_url("data", "v0", collection=bad),
            lambda: artifact_manager.remove_version("data", "v0", collection=bad),
            lambda: artifact_manager.list_versions("data", collection=bad),
            lambda: artifact_manager.list_artifacts(collection=bad),
            lambda: artifact_manager.exists_in_collection("data", collection=bad),
        ]:
            with pytest.raises(ValueError, match="Invalid collection name"):
                call()


def test_the_constructor_rejects_a_collection_that_would_nest(temp_store_dir):
    """The initial active collection goes through the same check as a later assignment."""
    with pytest.raises(ValueError, match="Invalid collection name"):
        FileSystemArtifactManager(url=temp_store_dir, collection="a/b")


def test_exists_skips_directories_that_are_not_collections(artifact_manager, temp_src_dir):
    """A stray directory in the store root does not make exists() raise."""
    artifact_manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")
    artifact_manager.log_files("data", temp_src_dir)
    stray = join_path(artifact_manager.url, "not.a.collection")
    artifact_manager.fs.mkdirs(stray, exist_ok=True)
    with artifact_manager.fs.open(join_path(stray, "file.txt"), "w") as f:
        f.write("x")

    assert artifact_manager.exists("data")
    assert not artifact_manager.exists("never-logged")


@pytest.mark.parametrize(
    "contents",
    [
        ["weights.bin"],
        ["weights.bin", "record.json"],
        ["model/weights.bin", "model/config.json"],
        ["model/weights.bin", "record.json"],
        ["a/b/c/d.txt"],
    ],
    ids=["one file", "two files", "one directory", "directory and file", "deeply nested"],
)
def test_a_version_downloads_with_the_layout_it_was_logged_with(contents, temp_src_dir, artifact_manager):
    """Whatever shape a version holds, downloading it reproduces that shape exactly."""
    manager, _ = artifact_manager
    with manager.log_folder("bundle", "my_collection") as folder:
        for relative_path in contents:
            os.makedirs(os.path.dirname(join_path(folder, relative_path)), exist_ok=True)
            with open(join_path(folder, relative_path), "w") as f:
                f.write(relative_path)

    download_dir = join_path(temp_src_dir, "downloaded")
    fs_local = get_fs_from_url(download_dir)
    fs_local.mkdirs(download_dir, exist_ok=True)
    manager.download_artifact("bundle", "my_collection", version="v0", to=download_dir)

    for relative_path in contents:
        downloaded = join_path(download_dir, relative_path)
        assert fs_local.exists(downloaded), f"{relative_path} is not where it was logged"
        with fs_local.open(downloaded, "rt") as f:
            assert f.read() == relative_path


def test_a_folder_given_as_a_path_object_is_logged_like_a_string_one(temp_src_dir, artifact_manager):
    """ArtifactManager.log_files annotates local_path as a Path, so both forms have to work."""
    manager, _ = artifact_manager
    with open(join_path(temp_src_dir, "a.txt"), "w") as f:
        f.write("x")

    artifact = manager.log_files("from_path", Path(temp_src_dir))

    assert manager.fs.exists(join_path(manager.artifact_url(artifact.name, artifact.version), "a.txt"))


def test_a_single_file_without_an_artifact_path_lands_at_the_version_root(temp_src_dir, artifact_manager):
    """A file logged without artifact_path keeps its name inside the version, on every store."""
    manager, _ = artifact_manager
    src_file = join_path(temp_src_dir, "a.txt")
    with open(src_file, "w") as f:
        f.write("x")

    artifact = manager.log_files("single_file", src_file)

    assert manager.fs.exists(join_path(manager.artifact_url(artifact.name, artifact.version), "a.txt"))


def test_a_single_file_logged_without_an_artifact_path_downloads_again(temp_src_dir, artifact_manager):
    """A single logged file comes back from the latest version, on every store."""
    manager, _ = artifact_manager
    src_file = join_path(temp_src_dir, "my_model.pth")
    with open(src_file, "w") as f:
        f.write("weights")

    manager.log_files("model", src_file)

    with manager.download_artifact("model") as download_dir, open(join_path(download_dir, "my_model.pth")) as f:
        assert f.read() == "weights"
