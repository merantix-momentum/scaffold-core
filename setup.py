#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import re
import subprocess
import sys

SOURCE_DIR = "scaffold"

# Read package information from other files so that just one version has to be maintained.
with open("pyproject.toml", "rb") as f:
    init_contents = f.read().decode("utf-8")

    def get_var(var_name: str) -> str:
        """Parsing of scaffold project infos defined in __init__.py"""
        pattern = re.compile(r"%s\s+=\s+(.*)" % var_name)
        match = pattern.search(init_contents).group(1)
        return str(ast.literal_eval(match))

    version = get_var("version")


def assert_version(ver: str) -> None:
    """Assert version follows semantics such as 0.0.1 or 0.0.1-dev123. Notice English letters are not allowed after
    'dev'.
    """
    pattern = (
        r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))"
        + "?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$"
    )
    # taken from: https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    assert bool(re.match(pattern, ver)), ValueError(
        f"Version string '{ver}' does not conform with regex '{pattern}', which is required by pypi metadata "
        "normalization."
    )


def normalize_version(_version: str, _version_tag: str) -> str:
    """Normalize version string according to tag build or dev build, to conform with the standard of PEP 440."""
    if "dev" in _version_tag:
        # remove alphabetic characters after keyword 'dev', which is forbidden PEP 440.
        short_sha = _version_tag[3:]  # substring after the word 'dev'
        numberic_sha = int(short_sha, 16)
        _version += f".dev{numberic_sha}"
    else:
        # In tag build, use the $TAG_NAME as the version string.
        _version = _version_tag.replace("v", "")
    assert_version(_version)
    return _version


# add tag to version if provided
if "--version_tag" in sys.argv:
    v_idx = sys.argv.index("--version_tag")
    version_tag = sys.argv[v_idx + 1]
    version = normalize_version(version, version_tag)
    sys.argv.remove("--version_tag")
    sys.argv.pop(v_idx)


if __name__ == "__main__":
    # Kinda hacky way to inject our modified package version to the build process.
    subprocess.run(
        (
            f"sed -r -i.bak 's/^version.*$/version = \"{version}\"/' pyproject.toml && "
            "/opt/poetry/bin/poetry build && "
            "mv pyproject.toml.bak pyproject.toml"
        ),
        shell=True,
        check=True,
    )
