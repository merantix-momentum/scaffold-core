import subprocess
from pathlib import Path

import pytest

CONFIG_OUTPUT = "Doing things with cfg.experiment_name='training' and cfg.model.learning_rate=0.001!\n"
CONFIG_OUTPUT_2 = CONFIG_OUTPUT + "Let me tell you about cfg.another_key='yet_another_value'!\n"


@pytest.mark.parametrize(
    "filename,output",
    [
        ("main.py", "Doing things!\n"),
        ("main_hydra.py", CONFIG_OUTPUT),
        ("main_hydra_group.py", CONFIG_OUTPUT),
        ("main_hydra_from_package.py", CONFIG_OUTPUT),
        ("main_hydra_flyte.py", CONFIG_OUTPUT),
        ("main_hydra_flyte_two_tasks.py", CONFIG_OUTPUT_2),
    ],
)
def test_base_hydra(filename: str, output: str) -> None:
    """Testing the base example script"""
    filepath = (Path(__file__).parent / "snippets" / filename).resolve()
    _output = subprocess.check_output(["python3", filepath], text=True)
    assert _output == output
