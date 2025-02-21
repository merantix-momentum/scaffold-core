
Introduction
============
The purpose of this documentation is to gradually build up your understanding of `Hydra <https://hydra.cc/>`_ and `Flyte <https://flyte.org/>`_ and how we use them to build a pipeline.
We will also go over the high level motivation for these tools.

We will not go into full detail of both tools here, but just illustrate the concepts we are using and motivate the ideas for how to combine them.
Hydra and flyte both have a lot of moving parts, and you likely will not need all of them.
This guide should bring you closer to understanding why and how specifically we use both tools, so that you are able to customize your usage based on a good starting point.

Why is this relevant to Momentum?
---------------------------------
As we gradually progress to push more and more proof of concepts into production, it becomes crucial that the ML-systems we build can be delivered in an automated, robust, reliable, and also fast way.
Many ML models are developed, tested, and deployed with manual steps involved.
Results are often not reproducible.
For classical software, this would be unimaginable nowadays.
Imagine that introducing a minor change into one of our internal python packages would require manually testing whether the package still works,
manually building the python package, and then manually uploading the python package to our internal pypi server.
The maintenance cost would be prohibitively high.

When ML projects move from the PoC to the production stage, the same applies to them.
At Momentum we want to apply best practices from software engineering to ML-systems.
We want to be able to reproduce our results and bring changes to our customers quickly.

To do so, in an ML-system, as opposed to classical software, we do not only have to version the code and have a CICD pipeline that tests and builds the code.
Additionally, in an ML system, one needs to version the configuration of the training code and also the data.
One does not only have to build and deliver a python package but build and deploy a system that can train and deploy ML models.

Using `Hydra <https://hydra.cc/>`_ for configuration of our ML-systems allows us to version the configuration of the training pipelines.
We use `Flyte <https://flyte.org/>`_ to build the workflows that process and validate data, train, evaluate, and validate models and then deploys them and validates the deployment.
Our hydra flyte launcher allows us to package, register, and execute such ml workflows from the CLI on the developer machine but also from CICD workflows.
This, all together, allows us to build systems where everything is automated from version control to deployed model:
Change the learning rate in github, CICD (cloudbuild) tests, packages, registers, and runs a new version of the Flyte training workflow.
This training workflow trains and deploys a new model, all from a single change of a config file in github.

Together, these tools allow us to build automated, reproducible ML-systems that allow us to bring new features into the hands of our customers quickly and reliably.

When should you use the flyte launcher?
---------------------------------------
The end goal of using flyte is to bring the deployment of machine learning workflows closer to the current best practice of continuous integration and delivery (CI/CD).
We refer to this concept as continuous delivery for machine learning (`CD4ML <https://martinfowler.com/articles/cd4ml.html>`_). The goal is to achieve a state that Google calls MLOPs level 2 in `this article <https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning#mlops_level_2_cicd_pipeline_automation>`_.
There are multiple aspects that are needed to make this a reality.
Even if you do not go all the way, these are the separate reasons for using the flyte launcher:

* Start workloads in the cloud (on kubernetes) from the CLI or a UI and move away from manual debug pods and execution
* Treat pipelines and their configuration as versioned artifacts, which can be delivered to a client or a research partner
* Reproduce workflow runs from previous versions
* Execute or register recurring workflows automatically within CI tools (e.g. cloudbuild)
* **Combine all of the above** in order to build a automated, tested and continuously delivered system, which does not require any manual steps between code changes and deploying to production

We build the flyte launcher, so the building, registration and execution of these pipelines is possible within one CLI call.
This process would usually require 5-6 steps using the native flyte way of doing things.


Simple python script starting point
-----------------------------------

We will use a very simple python script as a basis that we will build on in the next steps.

.. literalinclude:: /../test/docs_examples/snippets/main.py
    :caption: main.py
    :language: python

As our use case grows and becomes more complex, we usually encounter the need for at least some of the features which were mentioned in the previous section.
For configuration via the CLI, tools like `argparse <https://docs.python.org/3/library/argparse.html>`_ are commonly used, but they can be quite verbose and the combination with file based configuration is manual.
We will start by making use of `Hydra <https://hydra.cc/>`_ for configuration and a CLI, and will later add Flyte for remote execution.
