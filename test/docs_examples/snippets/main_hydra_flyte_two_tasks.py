import logging
from typing import Tuple

import flytekitplugins.omegaconf  # noqa F401
import hydra
from flytekit import task, workflow
from hydra_zen import builds, make_config, store
from omegaconf import DictConfig

logging.disable(logging.CRITICAL)  # Remove logs when comparing expected output


MyTaskConf = make_config(experiment_name="training", model=builds(dict, learning_rate=0.001)())
MyTask2Conf = make_config(another_key="yet_another_value")
PipelineConf = make_config(my_task_conf=MyTaskConf(), my_task_2_conf=MyTask2Conf())

store(PipelineConf, name="pipeline")
store.add_to_hydra_store()


@task
def create_config(cfg: DictConfig) -> Tuple[DictConfig, DictConfig]:  # noqa B008 B006
    """Separates individual task configs."""
    return cfg.my_task_conf, cfg.my_task_2_conf


@task(cache=False, cache_version="1.0")  # if cache == True then this function will not run the second time
def my_task(cfg: DictConfig) -> None:
    """Runs within one container"""
    print(f"Doing things with {cfg.experiment_name=} and {cfg.model.learning_rate=}!")


@task(cache=False, cache_version="1.0")  # if cache == True then this function will not run the second time
def my_task_2(cfg: DictConfig) -> None:
    """Runs within a second container"""
    print(f"Let me tell you about {cfg.another_key=}!")


@workflow
def pipeline(cfg: DictConfig) -> None:
    """Defines how tasks are executed and linked.
    This code is not executed (when running on kubernetes), but follows python syntax.
    """
    my_task_conf, my_task_2_conf = create_config(cfg=cfg)
    my_task(cfg=my_task_conf)
    my_task_2(cfg=my_task_2_conf)


@hydra.main(config_name="pipeline", version_base=None)
def main(cfg: DictConfig) -> None:
    """Parses the config locally and triggers the hydra flyte launcher."""
    pipeline(cfg=cfg)


if __name__ == "__main__":
    main()
