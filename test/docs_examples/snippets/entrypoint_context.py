from contextlib import AbstractContextManager

import hydra
from omegaconf import DictConfig

from scaffold.conf.scaffold.entrypoint import EntrypointConf
from scaffold.entrypoints.entrypoint import Entrypoint


class MyContext(AbstractContextManager):
    def __init__(self, message: str) -> None:
        """Context init"""
        self.message = message

    def __enter__(self) -> "MyContext":
        """Runs on start"""
        print("Context started!")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Runs on end"""
        print(str(self.message))
        print("Context ended!")


class MinimalExampleEntrypoint(Entrypoint[EntrypointConf]):
    def run(self) -> str:
        """Do your things."""
        print("Doing things!")
        return "Success!"


@hydra.main(config_path="./conf", config_name="entrypoint_context_conf.yaml")
def main(cfg: DictConfig) -> None:
    """Great Docs."""
    entrypoint = MinimalExampleEntrypoint(cfg, contexts=[MyContext("We are done!")])
    entrypoint()


if __name__ == "__main__":
    main()
