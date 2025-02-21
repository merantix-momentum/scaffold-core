# Enables postponed evaluation of type hints. See https://www.python.org/dev/peps/pep-0563/
# This is especially useful when using type hints for modules that we want to import lazily.
from __future__ import annotations

import logging
from argparse import Namespace
from typing import Any, Dict, Union

from pytorch_lightning.loggers.logger import Logger
from pytorch_lightning.utilities import rank_zero_only

logger = logging.getLogger(__name__)


class HyperoptLightningLogger(Logger):
    def __init__(self):
        """Lightning wrapper around hyperopt logging."""
        super().__init__()
        from scaffold.flyte.hyperopt.loggers import get_hyperopt_logger

        self.logger = get_hyperopt_logger()

    @property
    def name(self) -> str:
        """The experiment name."""
        return f"Logging with {self.logger.__class__}"

    @property
    def version(self) -> str:
        """The experiment version."""
        return self.logger.get_description()

    @rank_zero_only
    def log_hyperparams(self, params: Union[Dict[str, Any], Namespace]) -> None:
        """
        Logging of hyperparameters for experiment.

        Args:
            params (argparse.Namespace): The parameters to be logged.
        """
        pass

    @rank_zero_only
    def log_metrics(self, metrics: Dict[str, Any], step: int) -> None:
        """
        Logging of metrics.

        Args:
            metrics (Dict): Dictionary of metric names and values to be logged
            step (int): The step counter of optimisation iterations
        """
        for metric, value in metrics.items():
            if metric == self.logger.metric:
                self.logger.log_metric(metric, step, value)
                return
        self.logger.logger.warning(
            f"Could not find relevant hyperopt metric {self.logger.metric} in submitted values:\n {metrics}"
        )

    @rank_zero_only
    def finalize(self, status: str) -> None:
        """
        Finalisation of experiment run.

        Args:
            status (str): The experiment outcome (success, failed, etc.).
        """
        pass
