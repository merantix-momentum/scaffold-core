from typing import Any

import hydra


@hydra.main()
def main(cfg: Any) -> None:
    """Prints the given cfg"""
    print(cfg)


if __name__ == "__main__":
    main()
