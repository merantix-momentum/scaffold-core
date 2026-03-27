import subprocess
import sys
from pathlib import Path

import pytest

SNIPPETS_DIR = Path(__file__).parent / "snippets"


# ── Subprocess integration tests ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "filename,expected_fragments",
    [
        (
            "full_example.py",
            [
                "Loading train data from gs://example/data",
                "Training resnet18 on 3 samples",
                "gs://example/models",
                "Evaluating resnet18 from gs://example/models on 3 samples",
            ],
        ),
        (
            "quickstart.py",
            [
                "Training resnet18 on gs://example/data, saving to gs://example/models",
            ],
        ),
    ],
)
def test_local_execution(filename: str, expected_fragments: list[str]) -> None:
    """Run example scripts with execution_environment=local and verify log output."""
    filepath = (SNIPPETS_DIR / filename).resolve()
    result = subprocess.run(
        [sys.executable, str(filepath), "hydra.launcher.execution_environment=local"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        cwd=SNIPPETS_DIR,
    )
    assert result.returncode == 0, f"Script failed:\n{result.stdout}"
    for frag in expected_fragments:
        assert frag in result.stdout, f"Missing expected output fragment: {frag!r}"
