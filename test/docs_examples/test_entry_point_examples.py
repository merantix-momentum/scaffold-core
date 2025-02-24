import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "filename,output",
    [
        ("entrypoint.py", "Doing things!\n"),
        (
            "entrypoint_context.py",
            "Context started!\nContext started!\nDoing things!"
            + "\nWe are done!\nContext ended!\nConfig also!\nContext ended!\n",
        ),
    ],
)
def test_base_hydra(filename: str, output: str) -> None:
    """Testing the base example script"""
    filepath = (Path(__file__).parent / "snippets" / filename).resolve()
    _output = subprocess.check_output(["python3", filepath], text=True)
    assert _output == output
