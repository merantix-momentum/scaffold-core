<p align="center">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/_static/scaffold_logo_black.png" width="200">
      <source media="(prefers-color-scheme: light)" srcset="docs/_static/scaffold_logo_white.png" width="200">
      <img alt="Scaffold Logo" src="https://docs.scaffold.merantix-momentum.cloud/_static/scaffold_logo_white.png" width="200">
    </picture>
    <p align="center">Scaffold Core</p>
</p>


Scaffold is the Momentum breeding ground for utilities supporting our tech stack. As tools move into and out of our tech stack matching technology specific utilities will be developed within this project to make building machine learning projects a joy.

These utilities can encompass anything from simple python wrappers, small convenience functions or reoccurring boilerplate code to entirely new features integrating several technologies into a single workflow. Since all of these are rooted in our tech stack, they are necessarily opinionated and represent our view on how to best use our tooling.


Installation
------------

You can install the latest stable version of Scaffold via pip/Poetry/uv/....
Scaffold provides optional features via extras.

Without any extras:


    pip install mxm-scaffold

Install all, or pick specific extras:


    pip install mxm-scaffold[all]
    pip install mxm-scaffold[flyte,torch]

Documentation
-------------

If you work at Merantix Momentum, you can visit additional documentation via https://docs.scaffold.merantix-momentum.cloud/.

The documentation is built & deployed for the main-branch and tags.
[Please find more information about documentation here](<https://docs.scaffold.merantix-momentum.cloud/usage/document.html>).

Alternatively, build the publicly available documentation locally:

    cd scaffold/docs
    make html

Contribute
---------------------

We use poetry for resolving and installing dependencies. [Check the documentation for more information on how to contribute](<https://docs.scaffold.merantix-momentum.cloud/usage/contribute.html>).
