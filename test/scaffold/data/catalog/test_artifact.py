from unittest.mock import MagicMock, patch

import pytest

from scaffold.data.catalog.artifact import Artifact, FileSystemArtifactManagerDataset, WandBArtifactManagerDataset


class TestWandBArtifactManagerDataset:
    def test_init(self):
        ds = WandBArtifactManagerDataset(entity="my-entity", project="my-project", collection_name="my-collection")
        assert ds.entity == "my-entity"
        assert ds.project == "my-project"
        assert ds.collection_name == "my-collection"
        assert ds._manager is None

    @patch("scaffold.data.catalog.artifact.WandbArtifactManager")
    def test_call(self, mock_manager_cls):
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager

        ds = WandBArtifactManagerDataset(entity="my-entity", project="my-project", collection_name="my-collection")

        # First call should create the manager
        manager = ds()
        assert manager == mock_manager
        mock_manager_cls.assert_called_once_with(entity="my-entity", project="my-project", collection="my-collection")

        # Second call should return the same manager
        manager2 = ds()
        assert manager2 == manager
        assert mock_manager_cls.call_count == 1


class TestFileSystemArtifactManagerDataset:
    def test_init(self):
        ds = FileSystemArtifactManagerDataset(url="/tmp/artifacts", collection_name="my-collection")
        assert ds.url == "/tmp/artifacts"
        assert ds.collection_name == "my-collection"
        assert ds._manager is None

    @patch("scaffold.data.catalog.artifact.FileSystemArtifactManager")
    def test_call(self, mock_manager_cls):
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager

        ds = FileSystemArtifactManagerDataset(url="/tmp/artifacts", collection_name="my-collection")

        # First call should create the manager
        manager = ds()
        assert manager == mock_manager
        mock_manager_cls.assert_called_once_with(url="/tmp/artifacts", collection="my-collection")

        # Second call should return the same manager
        manager2 = ds()
        assert manager2 == manager
        assert mock_manager_cls.call_count == 1


class TestArtifact:
    @pytest.fixture
    def mock_manager_dataset(self):
        manager_ds = WandBArtifactManagerDataset(
            entity="test-entity", project="test-project", collection_name="test-collection"
        )
        mock_manager = MagicMock()
        manager_ds._manager = mock_manager
        return manager_ds, mock_manager

    def test_init(self, mock_manager_dataset):
        manager_ds, _ = mock_manager_dataset
        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        assert artifact.artifact_name == "my-artifact"
        assert artifact.manager == manager_ds
        assert artifact.version is None

    def test_getitem(self, mock_manager_dataset):
        manager_ds, _ = mock_manager_dataset
        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)

        # Test getting a specific version
        res = artifact["v1"]
        assert res == artifact
        assert artifact.version == "v1"

    def test_sorted_versions(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2", "v3"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        versions = artifact.sorted_versions()

        assert versions == ["v1", "v2", "v3"]
        manager.list_versions.assert_called_once_with("my-artifact")

    def test_latest(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2", "v3"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        res = artifact.latest

        assert res == artifact
        assert artifact.version == "v3"

    def test_push(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        res = artifact.push("/path/to/files")

        assert res == artifact
        manager.log_files.assert_called_once_with("my-artifact", "/path/to/files")
        # Should update version to latest after push
        assert artifact.version == "v2"

    def test_call_download_with_version(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds, version="v1")
        artifact("/download/path")

        manager.download_artifact.assert_called_once_with("my-artifact", version="v1", to="/download/path")

    def test_call_download_no_version(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        artifact("/download/path")

        # Should fetch latest version if none specified
        assert artifact.version == "v2"
        manager.download_artifact.assert_called_once_with("my-artifact", version="v2", to="/download/path")

    def test_iter(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        versions = list(artifact)

        assert versions == ["v1", "v2"]

    def test_len(self, mock_manager_dataset):
        manager_ds, manager = mock_manager_dataset
        manager.list_versions.return_value = ["v1", "v2", "v3"]

        artifact = Artifact(artifact_name="my-artifact", manager=manager_ds)
        assert len(artifact) == 3
