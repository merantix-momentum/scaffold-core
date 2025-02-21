Contribute
====================

To contribute to developing this package, check out its Github repository and push commits there.


Dependency Management
---------------------

We use poetry for resolving and installing dependencies.
For an overview of poetry basic commands, visit the `official documentation: <https://python-poetry.org/docs>`_

#. `Install poetry <https://python-poetry.org/docs/#installation>`_
#. Install the dependencies: ``poetry install --all-extras``. Poetry creates a virtual environment for you.
#. You can activate the venv using ``poetry shell`` or temporarily ``poetry run [command]``.
#. When adding new dependencies, use ``poetry add [my-package]`` or
   add them manually to ``pyproject.toml`` and update the lockfile ``poetry lock --no-update``.
#. Commit ``poetry.lock`` in a PR.
   Once merged to main, GithubActions will build the image with the new dependencies.

Tests
-----

You can run tests by executing ``poetry run pytest -n auto``.

Build the documentation locally
-------------------------------

Running ``poetry run sphinx-build ./docs ./docs/build`` from the root directory will generate the documentation.
Currently, this only works on python3.9.
You can use poetry with python3.10 by running ``poetry env use 3.10`` before ``poetry install --all-extras``.
