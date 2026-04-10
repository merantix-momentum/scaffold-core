import logging

import hydra
from flytekit import Resources, workflow
from flytekitplugins.omegaconf import OmegaConfTransformerMode, set_transformer_mode
from hydra.conf import HydraConf
from hydra.types import RunMode
from hydra_zen import builds, make_config, ZenStore
from launcher_conf import launcher_store
from omegaconf import DictConfig, MISSING

from scaffold.flyte import run_local_workflow, runtime_task, zen_call

logger = logging.getLogger(__name__)

set_transformer_mode(mode=OmegaConfTransformerMode.DictConfig)

workflow_store = ZenStore(name="workflow")


# ── 1. Configure Logic ────────────────────────────────────────────────────────


class Model:
    def __init__(self, name: str, learning_rate: float = 1e-3):
        self.name = name
        self.learning_rate = learning_rate


ModelConf = builds(Model, name=MISSING, populate_full_signature=True)

model_store = workflow_store(group="model")
model_store(ModelConf(name="resnet18", learning_rate=1e-3), name="resnet18")
model_store(ModelConf(name="resnet50", learning_rate=5e-4), name="resnet50")


# ── 2. Implement Logic ────────────────────────────────────────────────────────


def train(model: Model, data_path: str, output_path: str) -> str:
    logger.info(f"Training {model.name} on {data_path}, saving to {output_path}")
    return output_path


# ── 3. Configure Task and Workflow ────────────────────────────────────────────


TrainConf = builds(train, model=MISSING, data_path=MISSING, output_path=MISSING, populate_full_signature=True)

WorkflowConf = make_config(
    hydra_defaults=[
        "_self_",
        {"model@train.model": "resnet18"},
        {"override hydra/launcher": "flyte"},
    ],
    train=TrainConf,
)

workflow_store(
    make_config(
        bases=(WorkflowConf,),
        train=TrainConf(data_path="gs://example/data", output_path="gs://example/models"),
    ),
    name="default",
)


# ── 4. Implement Task and Workflow ────────────────────────────────────────────


@runtime_task(requests=Resources(mem="4Gi", cpu="2"))
def train_task(cfg: DictConfig, runtime_cfg: DictConfig) -> str:
    return zen_call(train, cfg)


@workflow
def training_pipeline(train: DictConfig, runtime_cfg: DictConfig) -> str:
    return train_task(cfg=train, runtime_cfg=runtime_cfg)


# ── 5. Run ────────────────────────────────────────────────────────────────────


@hydra.main(config_name="default", config_path=None, version_base="1.3")
def main(cfg: DictConfig) -> None:
    run_local_workflow(training_pipeline, cfg)


if __name__ == "__main__":
    workflow_store(HydraConf(mode=RunMode.MULTIRUN))
    workflow_store.add_to_hydra_store(overwrite_ok=True)
    launcher_store.add_to_hydra_store(overwrite_ok=True)
    main()
