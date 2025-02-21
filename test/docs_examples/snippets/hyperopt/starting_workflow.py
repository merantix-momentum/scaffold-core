from datetime import datetime
from typing import Tuple

import flytekitplugins.omegaconf  # noqa F401
import hydra
from flytekit import task, workflow
from flytekit.core.node_creation import create_node
from omegaconf import DictConfig


@task(...)
def create_config(cfg: DictConfig = DictConfig({})) -> Tuple[DictConfig, DictConfig, DictConfig]:  # noqa B008 B006
    """Separate config for different tasks"""
    return cfg.transform_bundle, cfg.train_bundle, cfg.evaluator_bundle


@task(...)
def transform_task(cfg: DictConfig) -> None:
    """Apply data transform"""
    print(f"Applying datatransform based on {cfg=}!")


@task(...)
def train_task(cfg: DictConfig) -> None:
    """Run training"""
    print(f"Running training with {cfg.model_params=} and {cfg.train_params}")


@task(...)
def evaluator_task(cfg: DictConfig) -> None:
    """Evaluate final model"""
    print(f"Assessing model {cfg.model_id=} on {cfg.test_set=}")


@workflow
def pipeline(cfg: DictConfig = DictConfig({}), kickoff_time: datetime = datetime.now()) -> str:  # noqa B008 B006
    """The main workflow"""
    transform_cfg, train_cfg, eval_cfg = create_config(cfg=cfg)
    first_node = create_node(transform_task, cfg=transform_cfg)
    second_node = create_node(train_task, cfg=train_cfg)
    third_node = create_node(evaluator_task, cfg=eval_cfg)

    first_node >> second_node
    second_node >> third_node


@hydra.main(config_path="./", config_name="workflow_bundle")
def main(cfg: DictConfig) -> None:
    """Hydra main"""
    pipeline(cfg=cfg)


if __name__ == "__main__":
    main()
