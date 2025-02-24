.. scaffold documentation master file:

Welcome to scaffold's documentation!
=========================================================================

Scaffold is the Momentum breeding ground for utilities supporting our tech stack. As tools move into and out of
our tech stack matching technology specific utilities will be developed within this project to make building machine
learning projects a joy.

These utilities can encompass anything from simple python wrappers, small convenience functions or reoccurring
boilerplate code to entirely new features integrating several technologies into a single workflow. Since all of these
are rooted in our tech stack, they are necessarily opinionated and represent our view on how to best use our tooling.

Current technologies and features
---------------------------------

Scaffold currently offers support for the current aspects of machine learning projects:

* Configuration management (Hydra)
* CLI execution and support (Hydra)
* Model training (Pytorch Lightning)
* Workflow orchestration/execution (Flyte)
* Code organisation (Entrypoints)
* Experiment tracking (Wandb)
* Plotting (Matplotlib)

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   usage/installation
   usage/contribute
   usage/subpackages
   usage/hydra_flyte_launcher/hydra_flyte_launcher
   usage/examples
   usage/document
