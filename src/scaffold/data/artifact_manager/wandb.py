import logging
import typing as t

import wandb

from scaffold.data.artifact_manager.base import ArtifactManager, TmpArtifact
from scaffold.data.fs import get_fs_from_url

logger = logging.getLogger(__name__)


class WandbArtifactManager(ArtifactManager):
    """Artifact manager that uses Weights & Biases (WandB) as the backend.

    This manager logs artifacts to WandB. In WandB, collections correspond to artifact types.
    Each artifact can contain multiple files, and versions are managed implicitly.

    Note:
        It is assumed that wandb.init() has been called before using this manager.
    """

    def __init__(
        self, entity: t.Optional[str] = None, project: t.Optional[str] = None, collection: str = "default"
    ) -> None:
        """Initialize the WandbArtifactManager.

        Args:
            entity (Optional[str]): If not provided, it's inferred from the active run / API settings.
            project (Optional[str]): If not provided, it's inferred from the active run / API settings.
            collection (str): The default collection (artifact type) name. Defaults to "default".

        Raises:
            ValueError: If neither a project nor an active project can be identified.
        """
        super().__init__(collection=collection)
        if project is not None:
            self.project = project
        elif wandb.run is not None:
            self.project = wandb.run.project
            logger.info(f"Using project {self.project} from active wandb run.")
        elif wandb.Api().settings["project"] is not None:
            self.project = wandb.Api().settings["project"]
            logger.info(f"Using project {self.project} from wandb settings.")
        else:
            raise ValueError("No project name was provided and no active project could be identified.")

        if entity is not None:
            self.entity = entity
        elif wandb.run is not None and wandb.run.entity is not None:
            self.entity = wandb.run.entity
            logger.info(f"Using entity {self.entity} from active wandb run.")
        elif wandb.Api().settings["entity"] is not None:
            self.entity = wandb.Api().settings["entity"]
            logger.info(f"Using entity {self.entity} from wandb settings.")
        else:
            self.entity = wandb.Api().project(self.project).entity
            logger.info(f"Using entity {self.entity} from wandb project.")

    def list_collection_names(self) -> t.Iterable[str]:
        """List all collections (artifact types) managed by WandB.

        Returns:
            Iterable[str]: A list of collection names corresponding to WandB artifact types.
        """
        return [collection.name for collection in wandb.Api().artifact_types(project=self.project)]

    def exists_in_collection(self, artifact: str, collection: t.Optional[str] = None) -> bool:
        """Check if an artifact exists in the specified collection.

        Note:
            The WandB API does not provide a direct existence check, so this is implemented
            by listing all artifacts in the collection.

        Args:
            artifact (str): The artifact name.
            collection (Optional[str]): The collection (artifact type) name. Defaults to the active collection.

        Returns:
            bool: True if the artifact exists in the collection, False otherwise.
        """
        collection = collection or self.active_collection
        if collection not in self.list_collection_names():
            return False
        return artifact in [
            art.name for art in wandb.Api().artifact_type(type_name=collection, project=self.project).collections()
        ]

    def log_files(
        self,
        artifact_name: str,
        local_path: str,
        collection: t.Optional[str] = None,
        artifact_path: t.Optional[str] = None,
    ) -> None:
        """Log files or a directory as a WandB artifact.

        This method uploads the file or directory located at `local_path` to WandB. If `local_path` is a directory,
        it uses `add_dir`; otherwise, it uses `add_file`.

        Args:
            artifact_name (str): The artifact name.
            local_path (str): The local path to the file or directory to be logged.
            collection (Optional[str]): The collection (artifact type) name. Defaults to the active collection.
            artifact_path (Optional[str]): An optional subpath within the artifact.
        """
        collection = collection or self.active_collection
        artifact = wandb.Artifact(artifact_name, type=collection)
        fs = get_fs_from_url(local_path)
        if fs.isdir(local_path):
            artifact.add_dir(local_path, name=artifact_path)
        else:
            artifact.add_file(str(local_path), name=artifact_path)
        artifact.save()
        artifact.wait()

    def download_artifact(
        self,
        artifact: str,
        collection: t.Optional[str] = None,
        version: t.Optional[str] = None,
        to: t.Optional[str] = None,
    ) -> t.Union[str, TmpArtifact]:
        """Download a specific artifact to a local path.

        WandB artifacts are downloaded in a nested folder structure.

        Args:
            artifact (str): The name of the artifact to download.
            collection (Optional[str]): The collection (artifact type) name. Defaults to the active collection.
            version (Optional[str]): The version of the artifact to download. If None, 'latest' is used.
            to (Optional[str]): The local destination path where the artifact should be downloaded.
                If not provided, a TmpArtifact context manager is returned.

        Returns:
            Union[str, TmpArtifact]: The local path where the artifact was downloaded, or a
                TmpArtifact context manager if no destination is provided.
        """
        collection = collection or self.active_collection
        if version is None:
            version = "latest"
        if wandb.run is None:
            art = wandb.Api().artifact(f"{self.entity}/{self.project}/{artifact}:{version}", type=collection)
        else:
            art = wandb.run.use_artifact(f"{self.entity}/{self.project}/{artifact}:{version}", type=collection)

        if to is not None:
            art.download(to)
            return to
        else:
            return TmpArtifact(self, collection, artifact, version)
