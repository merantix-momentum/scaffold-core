import logging

import flytekitplugins.omegaconf  # noqa F401
import hydra
from flytekit import task, workflow
from omegaconf import DictConfig

logging.disable(logging.CRITICAL)  # Remove logs when comparing expected output


@task
def my_task(cfg: DictConfig) -> None:
    """Runs within one container"""
    print(f"Doing things with {cfg.experiment_name=} and {cfg.model.learning_rate=}!")


@workflow
def pipeline(cfg: DictConfig) -> None:
    """Defines how tasks are executed and linked.
    This code is not executed (when running on kubernetes), but follows python syntax.
    """
    my_task(cfg=cfg)


@hydra.main(config_path="./conf", config_name="main_hydra_flyte_conf.yaml")
def main(cfg: DictConfig) -> None:
    """Parses the config locally and triggers the hydra flyte launcher."""
    pipeline(cfg=cfg)


if __name__ == "__main__":
    main()
