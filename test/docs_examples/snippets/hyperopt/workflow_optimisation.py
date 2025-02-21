from datetime import datetime
from typing import Tuple

import flytekitplugins.omegaconf  # noqa F401
import hydra
from flytekit import task, workflow
from flytekit.core.node_creation import create_node
from omegaconf import DictConfig

import scaffold.conf.scaffold.hyperopt.optuna.pruner  # noqa F401
import scaffold.conf.scaffold.hyperopt.optuna.sampler  # noqa F401

# New imports
from scaffold.flyte.core import mxm_register
from scaffold.flyte.hyperopt.flyte_task import optimise


@task(...)
def create_config(cfg: DictConfig = DictConfig({})) -> Tuple[DictConfig, DictConfig, DictConfig]:  # noqa B008 B006
    """Separate config for tasks in main workflow"""
    return cfg.opt_bundle, cfg.sub_wf_bundle, cfg.evaluator_bundle


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


@task(...)
def create_subconfig(cfg: DictConfig = DictConfig({})) -> Tuple[DictConfig, DictConfig]:  # noqa B008 B006
    """Separate configs for sub-workflow"""
    return cfg.transform_bundle, cfg.train_bundle


@workflow
def target_wf(cfg: DictConfig) -> None:
    """Target task sequence to be optimised"""
    transform_cfg, train_cfg = create_subconfig(cfg=cfg)
    first_node = create_node(transform_task, cfg=transform_cfg)
    second_node = create_node(train_task, cfg=train_cfg)
    first_node >> second_node


@mxm_register(nodes=[target_wf])  # registration annotation
@workflow
def pipeline(cfg: DictConfig = DictConfig({}), kickoff_time: datetime = datetime.now()) -> None:  # noqa B008 B006
    """The main workflow"""
    opt_cfg, target_cfg, eval_cfg = create_config(cfg=cfg)
    # substituted optimisation step
    first_node = create_node(optimise, optimiser_cfg=opt_cfg, target_cfg=target_cfg)
    second_node = create_node(evaluator_task, cfg=eval_cfg)
    first_node >> second_node


@hydra.main(config_path="./", config_name="workflow_bundle")
def main(cfg: DictConfig) -> None:
    """Hydra main"""
    pipeline(cfg=cfg)


if __name__ == "__main__":
    main()
