from omegaconf import DictConfig

from scaffold.flyte.hyperopt.loggers import get_hyperopt_logger


def train_task(cfg: DictConfig) -> None:
    """Run training"""
    logger = get_hyperopt_logger()
    for step in range(cfg.n_train_iter):
        ...
        logger.log_metric("train_performance", step, model.score(X_valid, y_valid))  # noqa F401
