import hydra
from omegaconf import DictConfig


@hydra.main(config_path="./conf", config_name="main_hydra_conf.yaml")
def main(cfg: DictConfig) -> None:
    """Great Docs."""
    print(f"Doing things with {cfg.experiment_name=} and {cfg.model.learning_rate=}!")


if __name__ == "__main__":
    main()

# >>> python3 main_hydra.py
# Doing things with cfg.experiment_name='training' and cfg.model.learning_rate=0.001!
