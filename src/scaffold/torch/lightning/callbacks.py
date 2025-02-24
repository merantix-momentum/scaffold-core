# Enables postponed evaluation of type hints. See https://www.python.org/dev/peps/pep-0563/
# This is especially useful when using type hints for modules that we want to import lazily.
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import torch
from pytorch_lightning import LightningModule, Trainer
from pytorch_lightning.callbacks import Callback
from pytorch_lightning.utilities import rank_zero_info, rank_zero_only

from scaffold.conf.scaffold.lightning.callbacks import LightningCheckpointerConf
from scaffold.data.artifact_manager.artifact_id_manager import validate_or_generate_target_afid
from scaffold.data.artifact_manager.artifact_logger import ModelLogger, STATE_FILENAME
from scaffold.data.artifact_manager.base import ArtifactManager
from scaffold.torch.distributed.ddp import is_distributed

logger = logging.getLogger(__name__)


class LightningCheckpointer(Callback):
    def __init__(
        self,
        artifact_manager: ArtifactManager,
        target_afid: Optional[str] = None,
        target_afid_best: Optional[str] = None,
        resume_checkpoint_afid: Optional[str] = None,
        resume_checkpoint_version: Optional[int] = None,
        only_log_current_best: bool = True,
    ):
        """Initializing the custom checkpointer.

        Notes:
            This method will create a local directory under /tmp (or equivalent depending on the OS) to save the
            best model checkpoint.

        Args:
            artifact_manager (ArtifactManager): ArtifactManager to use for logging.
            target_afid (str): Afid to log the state of the model and optimizers at the end of every epoch.
            target_afid_best (str): If set, will save the best model with this afid name. If None, will create a new
                random afid with the prefix 'best_model'
            resume_checkpoint_afid (str): Afid to load a model, optimizer and progress state from at the start of
                training.
            resume_checkpoint_version (int): Artifact version to load from. If None, will load the latest version.
            only_log_current_best (bool): If True, will only log a state, if the validation loss of an epoch
                is the lowest recorded one until then. If False, a state will be logged every epoch.
        """

        self.artifact_manager = artifact_manager
        self.model_logger = ModelLogger(artifact_manager=artifact_manager)
        self.only_log_current_best = only_log_current_best
        self.resume_checkpoint_afid = resume_checkpoint_afid
        self.resume_checkpoint_version = resume_checkpoint_version

        self.target_afid = validate_or_generate_target_afid(artifact_manager=artifact_manager, afid=target_afid)
        self.target_afid_best = validate_or_generate_target_afid(
            artifact_manager=artifact_manager, afid=target_afid_best, prefix="best_model"
        )
        self.best_state_dir = Path(TemporaryDirectory(prefix=f"{self.target_afid_best}__").name)
        self.best_state_path = self.best_state_dir / STATE_FILENAME

        self.lowest_avg_val_loss = None

    def _log_state_with_new_afid(
        self, model: torch.nn.Module, optimizers: List[torch.optim.Optimizer], current_epoch: int, **kwargs
    ) -> str:
        """Generates a new random state afid and logs it to the artifact store.

        Args:
            model (torch.nn.Module): Model to save the state off.
            optimizers (List[torch.optim.Optimizer]): All optimizers to save the state off.
            current_epoch (str): Current epoch.
            kwargs: Additional key value pairs to save to the state.
        """
        rank_zero_info(f"Saving state to afid {self.target_afid}")
        return self.model_logger.log_state_to_artifact(
            self.target_afid,
            model,
            optimizers,
            current_epoch=current_epoch,
            **kwargs,
        )

    @staticmethod
    def _get_avg_val_loss(callback_metrics: dict) -> float:
        try:
            return callback_metrics["avg_val_loss"]
        except KeyError as e:
            rank_zero_info("Please make sure to call self.log('avg_val_loss', avg_val_loss) in your lightning module.")
            raise e

    def on_train_start(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """If an afid for a checkpoint was given, load the full state into the trainer and lightning module."""
        if self.resume_checkpoint_afid is not None:
            rank_zero_info(f"Loading state from afid {self.resume_checkpoint_afid}")
            state = self.model_logger.retrieve_state_from_artifact(
                afid=self.resume_checkpoint_afid, version=self.resume_checkpoint_version
            )
            # These attributes are read only on the trainer, so we have to assign to train_loop
            # See https://github.com/PyTorchLightning/pytorch-lightning/pull/7437/files for more info
            trainer.fit_loop.global_step = state.get("global_step", 0)
            trainer.fit_loop.current_epoch = state.get("current_epoch", 0)

            if trainer.max_epochs is not None and trainer.current_epoch > trainer.max_epochs:
                raise ValueError(
                    f"Trainer(max_epochs={trainer.max_epochs}),"
                    f" but the loaded checkpoint has current_epoch={trainer.current_epoch}!"
                )

            # Instead of overwriting the model object, we create and load the state dict.
            # This makes sure, that the model architecture did not change.
            if is_distributed():
                # In the distributed case, the model torch module is nested, so we need to assign it
                # so the previously saved state dict keys align properly.
                pl_module.model.module.load_state_dict(state["model"].state_dict())
            else:
                pl_module.model.load_state_dict(state["model"].state_dict())
            if "optimizer_state_dicts" in state:
                for optim, optim_state in zip(trainer.optimizers, state["optimizer_state_dicts"]):
                    optim.load_state_dict(optim_state)
            if "scheduler_state_dicts" in state:
                schedulers = [asdict(config) for config in trainer.strategy.lr_scheduler_configs]
                for scheduler, scheduler_state in zip(schedulers, state["scheduler_state_dicts"]):
                    for key in scheduler.keys():
                        # We need to make sure, that id(scheduler.optimzer) stays the same.
                        if key == "scheduler":
                            scheduler[key].load_state_dict(scheduler_state[key])
                        else:
                            scheduler[key] = scheduler_state[key]

    @rank_zero_only
    def on_validation_epoch_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Saving state dicts of models and optimizers after every validation run."""

        avg_val_loss = self._get_avg_val_loss(trainer.callback_metrics)
        schedulers = [asdict(config) for config in trainer.strategy.lr_scheduler_configs]
        log_state_kwargs = {
            "model": pl_module.model,
            "optimizers": trainer.optimizers,
            "schedulers": schedulers,
            "current_epoch": trainer.current_epoch,
            "global_step": trainer.global_step,
            "avg_val_loss": avg_val_loss,
        }
        if self.lowest_avg_val_loss is None or avg_val_loss < self.lowest_avg_val_loss:
            # We always log a copy, so we can save the best under self.best_state_dir
            self.model_logger.save_state(self.best_state_dir, **log_state_kwargs)
            if self.only_log_current_best:
                self._log_state_with_new_afid(**log_state_kwargs)
            self.lowest_avg_val_loss = avg_val_loss

        if not self.only_log_current_best:
            self._log_state_with_new_afid(**log_state_kwargs)

    @rank_zero_only
    def on_train_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Log the best state dicts under the target afid"""
        # It's possible that training end before anything was saved
        if self.best_state_path.is_file():
            rank_zero_info(f"Saving best state dicts to target_afid_best {self.target_afid_best}")
            self.artifact_manager.log_files(
                artifact_name=self.target_afid_best,
                local_path=self.best_state_dir,
            )

    @rank_zero_only
    def load_best_state(self) -> dict:
        """Convenience function to load the current local best state."""
        if self.best_state_path.is_file():
            # torch.load can lead to deadlocks when trying to load a state that contains a distributed model.
            # This is the case when torch.load() is not called on all ranks.
            # That is why we make sure to only save non distributed model objects.
            return torch.load(self.best_state_path, weights_only=False)

    @classmethod
    def from_config(cls, cfg: LightningCheckpointerConf) -> "LightningCheckpointer":
        """Instantiate a LightningCheckpointer from a configuration.

        Args:
            cfg: Configuration for the LightningCheckpointer.
        """
        from hydra.utils import instantiate

        artifact_manager = instantiate(cfg.artifact_manager)
        return cls(
            artifact_manager=artifact_manager,
            target_afid=cfg.target_afid,
            target_afid_best=cfg.target_afid_best,
            resume_checkpoint_afid=cfg.resume_checkpoint_afid,
            resume_checkpoint_version=cfg.resume_checkpoint_version,
            only_log_current_best=cfg.only_log_current_best,
        )
