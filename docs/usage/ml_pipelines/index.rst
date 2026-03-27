.. _ml-pipelines:

Machine Learning Pipelines
==========================

This section covers how we build, configure, and deploy machine learning pipelines using
`Hydra <https://hydra.cc/>`_ + `hydra-zen <https://mit-ll-responsible-ai.github.io/hydra-zen/>`_
for configuration, `Flyte <https://flyte.org/>`_ for orchestration, and Scaffold as the glue between them.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   quickstart
   full_example
   deployment
   flyte_launcher
   advanced
   integrations
   gotchas


Why these tools?
----------------

As ML projects move from proof-of-concept to production, managing configuration, reproducibility,
and cloud execution manually becomes prohibitively expensive. Classical software engineering has
solved this with version control and CI/CD — but ML systems have additional dimensions: you need
to version not just code but also configuration and data, and you need to build and deploy not just
a package but an entire training system.

Manual steps compound quickly. Imagine that every change to a learning rate required you to manually
rebuild a Docker image, push it, register the workflow, and trigger a run. The maintenance cost
would be unsustainable.

The combination of hydra-zen and Flyte solves this:

- **hydra-zen** keeps all configuration in Python — versioned, composable, type-checked.
  No scattered YAML files. Configs are first-class code artifacts that live next to the logic they
  configure and travel with it through version control.
- **Flyte** orchestrates multi-task pipelines in Kubernetes pods, provides caching, and gives you
  a UI to monitor executions, inspect outputs, and re-run specific tasks. Pipelines and their
  configuration become versioned, reproducible artifacts that can be delivered to a client or
  research partner, or replayed exactly months later.
- **Scaffold's Flyte launcher** collapses the five manual steps of building images, serializing,
  registering, and executing a workflow into one CLI call — from a developer machine or from a
  CI/CD pipeline.

Together these tools let you reach a state where a single config change in version control triggers
CI/CD to test, build, register, and run a new version of the training workflow automatically — what
Google refers to as
`MLOps level 2 <https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning#mlops_level_2_cicd_pipeline_automation>`_
and Martin Fowler calls `CD4ML <https://martinfowler.com/articles/cd4ml.html>`_.


When should you use Flyte?
--------------------------

Local execution is always the starting point. Reach for Flyte when you need any of the following
— and especially when you need several of them together:

- **Scale** — a task needs more RAM, GPUs, or parallelism than your laptop can provide
- **Reproducibility** — every run is a versioned, inspectable artifact in the Flyte UI
- **Scheduling** — workflows that run on a cron schedule without manual intervention
- **Deliverability** — pipelines as versioned artifacts, shareable with clients or partners
- **CD4ML** — CI/CD automatically registers and runs a new workflow version on every merge


How it works at a glance
------------------------

A pipeline file follows a five-step structure:

1. **Configure Logic** — define your domain classes and create :code:`builds()` configs for them
2. **Implement Logic** — write plain Python functions (no Flyte or hydra dependencies)
3. **Configure Tasks and Workflow** — compose task and workflow configs; register named variants
4. **Implement Tasks and Workflow** — wrap functions in :code:`@runtime_task` and :code:`@workflow`
5. **Run** — :code:`main()` handles local execution; :code:`__main__` flushes stores and calls :code:`main()`

See :ref:`quickstart` for a minimal working example.
