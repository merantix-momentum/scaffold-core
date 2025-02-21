from flytekit import task, workflow
from omegaconf import DictConfig


@task(
    retries=2,
    cache=True,
    cache_version="1",
)
def hello_torch(hyperparam: float) -> float:
    """Dummy torch task to check plugins"""
    return 3.0


@workflow
def plugins_workflow(cfg: DictConfig) -> float:
    """Dummy workflow to test two plugins"""
    res = hello_torch(hyperparam=5.0)
    return res
