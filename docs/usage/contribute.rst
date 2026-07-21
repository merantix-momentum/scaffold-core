Contribute
====================

To contribute to developing this package, check out its GitHub repository and push commits there.

Dependency Management
---------------------

We use `uv <https://docs.astral.sh/uv/>`_ for resolving and installing dependencies.
For an overview of the basic uv commands, visit the `official documentation <https://docs.astral.sh/uv/getting-started/features/>`_.

#. `Install uv <https://docs.astral.sh/uv/getting-started/installation/>`_.
#. Install the dependencies with ``uv sync --all-extras --group docs``.
   uv creates a virtual environment in ``.venv``.
#. You can run commands in the virtual environment with ``uv run [command]``.
#. When adding new dependencies, use ``uv add [my-package]``.
   Use ``uv add --dev [my-package]`` for a development dependency or
   ``uv add --group docs [my-package]`` for a documentation dependency.
#. Commit ``pyproject.toml`` and ``uv.lock`` in a PR when dependencies change.
   Once merged into main, GitHub Actions will build the image with the new dependencies.

Tests
-----

You can run tests by executing ``uv run pytest -n auto``.

Build the documentation locally
-------------------------------

Running ``uv run sphinx-build -b html ./docs ./docs/_build/html`` from the repository root will generate the documentation.
Scaffold supports Python 3.11 and 3.12.