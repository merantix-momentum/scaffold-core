.. _full-example:

Full Example: Training Pipeline
================================

This example builds a three-task training pipeline — :code:`prepare_data → train → evaluate` —
and introduces the patterns you'll reach for in real workflows: config groups for swappable
components, named configs for environments, and :code:`zen_exclude` for inter-task data.

.. literalinclude:: /../test/docs_examples/snippets/full_example.py
    :caption: workflow.py
    :language: python

Running it
----------

.. code-block:: console

    # Local execution with default config
    python workflow.py

    # Local execution with debug config (100-sample limit, debug output path)
    python workflow.py --config-name debug

    # Switch to resnet50 for both train and evaluate
    python workflow.py train.model=resnet50 evaluate.model=resnet50

    # Remote execution (Flyte) — MULTIRUN is set automatically in __main__
    python workflow.py

Key patterns
------------

Config groups and the defaults list
''''''''''''''''''''''''''''''''''''

The :code:`model_store` registers two model variants under the :code:`model` group:

.. code-block:: python

    model_store(ModelConf(name="resnet18", learning_rate=1e-3), name="resnet18")
    model_store(ModelConf(name="resnet50", learning_rate=5e-4), name="resnet50")

:code:`WorkflowConf` selects :code:`resnet18` by default and places it at :code:`train.model`
and :code:`evaluate.model` in the rendered config:

.. code-block:: python

    hydra_defaults=[
        "_self_",
        {"model@train.model": "resnet18"},
        {"model@evaluate.model": "resnet18"},
        {"override hydra/launcher": "flyte"},
    ],

The :code:`@` syntax is standard hydra package override notation — it controls *where* in the
config tree the selected group option is placed. Switching both tasks to resnet50 from the CLI:

.. code-block:: console

    python workflow.py "model@train.model=resnet50" "model@evaluate.model=resnet50"


Named configs
'''''''''''''

:code:`workflow_store(..., name="default")` and :code:`workflow_store(..., name="debug")` register
two concrete configs that fill in all :code:`MISSING` values. :code:`@hydra.main(config_name="default")`
selects the default; :code:`--config-name debug` selects debug.

This is the idiomatic way to manage environment-specific configs (dev paths, production paths,
smaller data limits for fast iteration) without touching the workflow code.


zen_exclude — inter-task outputs
'''''''''''''''''''''''''''''''''

Some task inputs aren't part of the config — they come from the output of a previous task.
:code:`zen_exclude` tells :code:`zen_call` to skip those fields when building the function call
from the config, so they can be injected at runtime instead:

.. code-block:: python

    TrainConf = builds(
        train,
        model=MISSING,
        output_path=MISSING,
        populate_full_signature=True,
        zen_exclude=["data"],   # <— passed from prepare_data_task output
    )

In the task body, the excluded argument is passed explicitly:

.. code-block:: python

    @runtime_task(...)
    def train_task(cfg: DictConfig, runtime_cfg: DictConfig, data: list[str]) -> str:
        return zen_call(train, cfg, data=data)


Per-task resource configuration
''''''''''''''''''''''''''''''''

:code:`@runtime_task` accepts the same keyword arguments as :code:`@task`, so each task can
request different resources:

.. code-block:: python

    @runtime_task(requests=Resources(mem="4Gi", cpu="2"))
    def train_task(...):
        ...

    @runtime_task(requests=Resources(mem="2Gi", cpu="1"))
    def evaluate_task(...):
        ...

See :ref:`deployment` for how to assign tasks to different Docker images when they have
different dependency requirements.
