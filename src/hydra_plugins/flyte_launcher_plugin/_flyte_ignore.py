import os
from pathlib import Path

from docker.utils.build import PatternMatcher
from flytekit.tools.ignore import Ignore


class FlyteIgnore(Ignore):
    def __init__(self, root: Path, ignore_path: Path):
        """Altered version of Flytes DockerIgnore allowing custom path. Relies on Dockers PatternMatcher."""
        super().__init__(root)
        self.pm = self._parse(ignore_path)

    def _parse(self, path: Path) -> PatternMatcher:
        """Parse a file in the style of dockerignore and return a PatternMatcher"""
        patterns = []
        dockerignore = os.path.join(self.root, path)
        if os.path.isfile(dockerignore):
            with open(dockerignore, "r") as f:
                patterns = [line.strip() for line in f.readlines() if line and not line.startswith("#")]
        return PatternMatcher(patterns)

    def _is_ignored(self, path: str) -> bool:
        """Check if a path is ignored by the ignore file"""
        return self.pm.matches(path) and path != ""
