import logging
import typing as t

import flytekitplugins.omegaconf  # noqa F401
import hydra
from flytekit import task, workflow
from omegaconf import DictConfig, OmegaConf

logging.disable(logging.CRITICAL)  # Remove logs when comparing expected output


@task(cache=True)
def prepare_config(cfg: DictConfig, overrides: t.Optional[t.Dict[str, t.List[int]]] = None) -> DictConfig:
    """Utility function to split the workflow config into components and apply overrides.

    Args:
        overrides: Overrides to apply to the config with keys in dot notation
        cfg (DictConfig): Workflow config of type TrainingWorkflowConf.

    Returns:
        t.Tuple[DictConfig, ...]: Updated config
    """

    if overrides is not None:
        for key, value in overrides.items():
            OmegaConf.update(cfg, key, value)

    return cfg


# The cache kicks in when either the configuration or the data to process changes
@task(cache=True, cache_version="1.0")
def clean_string_task(cfg: DictConfig, data_string: str) -> str:
    """Runs within one container"""
    if cfg.strip_string:
        data_string = data_string.strip()
    if cfg.make_lower_case:
        data_string = data_string.lower()
    return data_string


# Note: The t.Optional typehint with a None default value only works from flyte 1.10.1 onwards
@workflow
def pipeline(cfg: DictConfig, data_string: str, overrides: t.Optional[t.Dict[str, t.List[int]]] = None) -> None:
    """Defines how tasks are executed and linked.
    This code is not executed (when running on kubernetes), but follows python syntax.

    Args:
        cfg (DictConfig): Workflow config of type TrainingWorkflowConf.
        overrides: Overrides to apply to the config with keys in dot notation. Convenience for easier changing the cfg.
        data_string: The data to process, any string that will be cleaned.
    """
    cfg = prepare_config(cfg, overrides)
    clean_string_task(cfg=cfg, data_string=data_string)


@hydra.main(config_path="./conf", config_name="main_hydra_flyte_multiple_inputs.yaml")
def main(cfg: DictConfig) -> None:
    """Parses the config locally and triggers the hydra flyte launcher."""
    pipeline(cfg=cfg)


if __name__ == "__main__":
    main()
