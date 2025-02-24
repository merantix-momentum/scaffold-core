import hydra
from omegaconf import DictConfig

from scaffold.conf.scaffold.entrypoint import EntrypointConf
from scaffold.entrypoints.entrypoint import Entrypoint


class MinimalExampleEntrypoint(Entrypoint[EntrypointConf]):
    def run(self) -> str:
        """Do your things."""
        print("Doing things!")
        return "Success"


@hydra.main(config_path="./conf", config_name="entrypoint_conf.yaml")
def main(cfg: DictConfig) -> None:
    """Great Docs."""
    entrypoint = MinimalExampleEntrypoint(cfg)
    entrypoint()


if __name__ == "__main__":
    main()
