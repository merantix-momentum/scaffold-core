"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import datetime
import os
import sys
import typing as t
from importlib import metadata

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import PythonPythonMapper

sys.path.insert(0, os.path.abspath(os.path.join(__file__, os.pardir)))


# -- Project information -----------------------------------------------------

project = "scaffold"
copyright = f"{datetime.datetime.now().year}, Merantix Momentum GmbH"
author = "Merantix Momentum GmbH"

# The full version, including alpha/beta/rc tags
release = metadata.version("mxm-scaffold")

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "autoapi.extension",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# configure sphinx-versions (sphinxcontrib-versioning => scv)
# to build versioned documentation only for branch "main"
scv_whitelist_branches = (r"^main$",)
scv_root_ref = "main"
# sort by semantic versioning format
scv_sort = ("semver",)
# display branches before tags
scv_priority = "branches"

todo_include_todos = False
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

html_theme = "sphinx_rtd_theme"

# Material theme options (see theme.conf for more information)
html_theme_options = {
    "github_repository": "merantix-momentum/scaffold",
    "path_to_documentation_dir": "docs",
    "github_sphinx_locale": "",
    "github_branch": "main",
    "mx_top_bar": {},
    "show_mx_top_bar": True,
}

html_logo = "_static/scaffold_logo_blue.png"
html_favicon = "_static/mx_favicon.svg"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Document Python Code
autoapi_type = "python"
autoapi_dirs = ["../src/scaffold", "../src/hydra_plugins"]
autoapi_python_class_content = "both"
autoapi_member_order = "groupwise"
autoapi_options = [
    "members",
    "undoc-members",
    # "private-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]


def skip_util_classes(
    app: Sphinx, what: str, name: str, obj: PythonPythonMapper, skip: bool, options: t.List[str]
) -> bool:
    """Called for each object to decide whether it should be skipped."""
    if what == "attribute" and name.endswith(".logger"):
        skip = True
    if name.startswith("scaffold.integration_test"):
        skip = True
    return skip


def setup(sphinx: Sphinx) -> None:
    """Set up sphinx by registering custom skip function."""
    sphinx.connect("autoapi-skip-member", skip_util_classes)
