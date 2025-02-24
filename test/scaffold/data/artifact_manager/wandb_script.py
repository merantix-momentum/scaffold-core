import tempfile

import wandb

from scaffold.data.artifact_manager.wandb import WandbArtifactManager
from scaffold.data.fs import join_path

# Create a temporary directory for source files.
src_dir = tempfile.TemporaryDirectory()

# Start a wandb run.
test_run = wandb.init(project="miha-sandbox")
artifact_manager = WandbArtifactManager(project="miha-sandbox")
collection = "test_artifacts"

# Define file artifacts as tuples: (filename, artifact_name, version, content)
file_descriptions = [
    ("foo.txt", "foo", "v0", "Test: Foo"),
    ("bar.txt", "bar", "v0", "Test: Bar"),
    ("baz.txt", "bar", "v1", "Test: Baz"),
]

# --- Log individual file artifacts ---
for filename, artifact_name, version, content in file_descriptions:
    file_path = join_path(src_dir.name, filename)
    with open(file_path, "w") as f:
        f.write(content)
    # Log the file; note that log_files() returns None.
    artifact_manager.log_files(artifact_name=artifact_name, local_path=file_path, collection=collection)

# --- Download each artifact and verify contents ---
download_base = join_path(src_dir.name, "downloaded")
for filename, artifact_name, version, content in file_descriptions:
    # Download the artifact to a subdirectory (download_artifact returns a path because 'to' is provided)
    download_path = artifact_manager.download_artifact(
        artifact=artifact_name, collection=collection, version=version, to=download_base
    )
    downloaded_file = join_path(download_path, filename)
    with open(downloaded_file, "r") as f:
        read_content = f.read()
    assert read_content == content, f"For artifact '{artifact_name}', expected '{content}' but got '{read_content}'"

# --- Log a folder artifact ---
# Here we log the entire contents of src_dir as an artifact named "folder"
artifact_manager.log_files("my_folder_artifact", src_dir.name, collection)
# Download the folder artifact.
download_folder = artifact_manager.download_artifact(
    "my_folder_artifact", collection, "v0", join_path(src_dir.name, "downloaded_folder")
)
# The downloaded structure is expected to be: <downloaded_folder>/folder/<filename>
for filename, _, _, content in file_descriptions:
    file_in_folder = join_path(download_folder, filename)
    with open(file_in_folder, "r") as f:
        read_content = f.read()
    assert read_content == content, f"In folder artifact, expected '{content}' in '{filename}'"

# --- Existence Checks ---
assert artifact_manager.exists("foo"), "Artifact 'foo' should exist"
assert artifact_manager.exists("bar"), "Artifact 'bar' should exist"
assert artifact_manager.exists_in_collection("foo", collection), "Artifact 'foo' should exist in collection"
assert artifact_manager.exists_in_collection("bar", collection), "Artifact 'bar' should exist in collection"
assert not artifact_manager.exists_in_collection(
    "foo", "other_collection"
), "Artifact 'foo' should not exist in other_collection"

# --- Log a folder using DirectoryLogger context manager ---
with artifact_manager.log_folder("test_folder_artifact", collection) as folder:
    # 'folder' is a temporary directory for logging.
    for filename, _, _, content in file_descriptions:
        file_in_folder = join_path(folder, filename)
        with open(file_in_folder, "w") as f:
            f.write(content)
# After context exit, the folder artifact is logged.
download_test_folder = artifact_manager.download_artifact(
    "test_folder_artifact", collection, "v0", join_path(src_dir.name, "downloaded_test_folder")
)
# Check that each file in "test_folder_artifact" is present and correct.
for filename, _, _, content in file_descriptions:
    file_path = join_path(download_test_folder, filename)
    with open(file_path, "r") as f:
        read_content = f.read()
    assert read_content == content, f"In 'test_folder_artifact' artifact, expected '{content}' in '{filename}'"

# --- Test temporary download (without specifying destination) ---
with artifact_manager.download_artifact("test_folder_artifact", collection, "v0") as temp_path:
    for filename, _, _, content in file_descriptions:
        file_path = join_path(temp_path, filename)
        with open(file_path, "r") as f:
            read_content = f.read()
        assert read_content == content, f"In temporary download, expected '{content}' in '{filename}'"

# Finish the wandb run and clean up.
wandb.finish()
src_dir.cleanup()
