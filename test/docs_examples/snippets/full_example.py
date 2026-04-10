import logging
from typing import Optional

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


class Dataset:
    def __init__(self, path: str, split: str = "train", limit: Optional[int] = None):
        self.path = path
        self.split = split
        self.limit = limit


class Model:
    def __init__(self, name: str, learning_rate: float = 1e-3):
        self.name = name
        self.learning_rate = learning_rate


DatasetConf = builds(Dataset, path=MISSING, populate_full_signature=True)
ModelConf = builds(Model, name=MISSING, populate_full_signature=True)

model_store = workflow_store(group="model")
model_store(ModelConf(name="resnet18", learning_rate=1e-3), name="resnet18")
model_store(ModelConf(name="resnet50", learning_rate=5e-4), name="resnet50")


# ── 2. Implement Logic ────────────────────────────────────────────────────────


def prepare_data(dataset: Dataset) -> list[str]:
    logger.info(f"Loading {dataset.split} data from {dataset.path}")
    records = ["sample_1", "sample_2", "sample_3"]
    return records[: dataset.limit] if dataset.limit else records


def train(model: Model, output_path: str, data: list[str]) -> str:
    logger.info(f"Training {model.name} on {len(data)} samples → {output_path}")
    return output_path


def evaluate(model: Model, checkpoint_path: str, data: list[str]) -> dict:
    logger.info(f"Evaluating {model.name} from {checkpoint_path} on {len(data)} samples")
    return {"accuracy": 0.95}


# ── 3. Configure Tasks and Workflow ───────────────────────────────────────────


PrepareDataConf = builds(prepare_data, dataset=MISSING, populate_full_signature=True)
TrainConf = builds(
    train,
    model=MISSING,
    output_path=MISSING,
    populate_full_signature=True,
    zen_exclude=["data"],  # data is passed at runtime from prepare_data_task
)
EvaluateConf = builds(
    evaluate,
    model=MISSING,
    populate_full_signature=True,
    zen_exclude=["checkpoint_path", "data"],  # both passed at runtime from upstream tasks
)

WorkflowConf = make_config(
    hydra_defaults=[
        "_self_",
        {"model@train.model": "resnet18"},
        {"model@evaluate.model": "resnet18"},
        {"override hydra/launcher": "flyte"},
    ],
    prepare_data=PrepareDataConf,
    train=TrainConf,
    evaluate=EvaluateConf,
)

workflow_store(
    make_config(
        bases=(WorkflowConf,),
        prepare_data=PrepareDataConf(dataset=DatasetConf(path="gs://example/data")),
        train=TrainConf(output_path="gs://example/models"),
        evaluate=EvaluateConf(),
    ),
    name="default",
)
workflow_store(
    make_config(
        bases=(WorkflowConf,),
        prepare_data=PrepareDataConf(dataset=DatasetConf(path="gs://example/data", limit=100)),
        train=TrainConf(output_path="gs://example/debug"),
        evaluate=EvaluateConf(),
    ),
    name="debug",
)


# ── 4. Implement Tasks and Workflow ──────────────────────────────────────────


@runtime_task(requests=Resources(mem="2Gi", cpu="1"))
def prepare_data_task(cfg: DictConfig, runtime_cfg: DictConfig) -> list[str]:
    return zen_call(prepare_data, cfg)


@runtime_task(requests=Resources(mem="4Gi", cpu="2"))
def train_task(cfg: DictConfig, runtime_cfg: DictConfig, data: list[str]) -> str:
    return zen_call(train, cfg, data=data)


@runtime_task(requests=Resources(mem="2Gi", cpu="1"))
def evaluate_task(cfg: DictConfig, runtime_cfg: DictConfig, checkpoint_path: str, data: list[str]) -> dict:
    return zen_call(evaluate, cfg, checkpoint_path=checkpoint_path, data=data)


@workflow
def training_pipeline(
    prepare_data: DictConfig,
    train: DictConfig,
    evaluate: DictConfig,
    runtime_cfg: DictConfig,
) -> dict:
    data = prepare_data_task(cfg=prepare_data, runtime_cfg=runtime_cfg)
    checkpoint = train_task(cfg=train, runtime_cfg=runtime_cfg, data=data)
    return evaluate_task(cfg=evaluate, runtime_cfg=runtime_cfg, checkpoint_path=checkpoint, data=data)


# ── 5. Run ────────────────────────────────────────────────────────────────────


@hydra.main(config_name="default", config_path=None, version_base="1.3")
def main(cfg: DictConfig) -> None:
    run_local_workflow(training_pipeline, cfg)


if __name__ == "__main__":
    workflow_store(HydraConf(mode=RunMode.MULTIRUN))
    workflow_store.add_to_hydra_store(overwrite_ok=True)
    launcher_store.add_to_hydra_store(overwrite_ok=True)
    main()
