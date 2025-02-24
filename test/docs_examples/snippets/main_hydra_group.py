import hydra
from omegaconf import DictConfig


@hydra.main(config_path="./conf", config_name="main_hydra_group.yaml")
def main(cfg: DictConfig) -> None:
    """Great Docs."""
    print(f"Doing things with {cfg.experiment_name=} and {cfg.model.learning_rate=}!")


if __name__ == "__main__":
    main()
