# Enables postponed evaluation of type hints. See https://www.python.org/dev/peps/pep-0563/
# This is especially useful when using type hints for modules that we want to import lazily.
from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from scaffold.data.artifact_manager.base import ArtifactManager, DirectoryLogger

# Enables the usage for type hints. Will not be executed during runtime, because we want to use lazy imports.
if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)

STATE_FILENAME = "state.pt"


class ModelLogger:
    """Class to be used for logging a model or state dicts as an artifact.
    Will always use a temporary dir locally to save artifacts before logging that dir.
    """

    def __init__(self, artifact_manager: ArtifactManager) -> None:
        """
        Initializes the ModelLogger.

        Args:
            artifact_manager (ArtifactManager): ArtifactManager to use for logging artifacts.
        """
        self.artifact_manager = artifact_manager

    @staticmethod
    def save_state(
        dict_dp: str,
        model: torch.nn.Module,
        optimizers: List[torch.optim.Optimizer] = None,
        schedulers: List[torch.optim.lr_scheduler._LRScheduler] = None,
        **kwargs,
    ) -> None:
        """Saves the model and optimizer state dicts, and optionally some keyword arguments, into one dictionary
        that can later be loaded to retrieve the exact state of the model training.

        Notes:
            We intentionally do not save the model.state_dict() here since we need to support easy
            model loading from a single afid in the evaluator without initializing the model class first.

        Args:
            dict_dp (str): Directory where the state dict pickle file should be saved.
            model (torch.nn.Module): Model to save the state dict off.
            optimizers (List[torch.optim.Optimizer]): All optimizers to save the state dicts off.
            kwargs: Additional key value pairs to save to the state dict
        """
        import torch

        # If the model is distributed, we want to unwrap it first, so that the checkpoint does not depend on
        # being loaded as a distributed model. When later loading the state, we use the state dict to load
        # the weights, which makes it agnostic towards the exact type of the model.
        state = {
            "model": model.module if isinstance(model, torch.nn.parallel.DistributedDataParallel) else model,
            **kwargs,
        }
        if optimizers is not None:
            state.update({"optimizer_state_dicts": [o.state_dict() for o in optimizers]})
        if schedulers is not None:
            scheduler_state_dicts = []
            for s in schedulers:
                # Lightning wraps the schedulers with extra parameters we would also like to save (e.g. "interval").
                # We overwrite the key "scheduler" where the actual class lives, with its state dict, and keep the rest.
                s = deepcopy(s)
                s["scheduler"] = s["scheduler"].state_dict()
                scheduler_state_dicts.append(s)
            state.update({"scheduler_state_dicts": scheduler_state_dicts})

        dict_dp = Path(dict_dp)
        dict_dp.mkdir(exist_ok=True)
        torch.save(state, dict_dp / STATE_FILENAME)

    def log_state_to_artifact(
        self,
        afid: str,
        model: torch.nn.Module,
        optimizers: List[torch.optim.Optimizer] = None,
        collection: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Logs the model and optimizer state dicts under the specified artifact id.

        Args:
            afid (str): Artifact id to log under on the given artifact store or None to generate a new one.
            model (torch.nn.Module): Model to save the state dict off.
            optimizers (List[torch.optim.Optimizer]): All optimizers to save the state dicts off.
            collection (Optional[str]): Collection to log the artifact to.
            kwargs: Additional key value pairs to save to the state dict
        """
        with DirectoryLogger(self.artifact_manager, afid, collection=collection) as dp:
            self.save_state(Path(dp), model, optimizers, **kwargs)

        return afid

    def retrieve_state_from_artifact(
        self, afid: str, collection: Optional[str] = None, version: int = None, device: Optional[str] = None
    ) -> Dict:
        """
        Returns a dictionary containing the model and optimizer state from the artifact store at the artifact_path.

        Args:
            afid: Artifact id of the model. Must have been logged via :py:meth:`log_state_to_artifact`
            device: Device to load the model to. "cpu", "cuda" or None, which is the default that
                will use the gpu if available

        Returns:
            State dictionary containing the model and optimizer state. See :py:meth:`log_state_to_artifact` for the
            key-value pairs.
        """
        import torch

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        with self.artifact_manager.download_artifact(artifact=afid, collection=collection, version=version) as artdir:
            model = torch.load(Path(artdir) / STATE_FILENAME, map_location=torch.device(device), weights_only=False)
        return model
