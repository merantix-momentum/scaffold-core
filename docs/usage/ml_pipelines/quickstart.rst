.. _quickstart:

Quickstart
==========

This page walks through a minimal pipeline — a single training task — to introduce the full
pattern without getting distracted by multi-step complexity.
For a pipeline with multiple tasks and more config structure, see :ref:`full-example`.

.. literalinclude:: /../test/docs_examples/snippets/quickstart.py
    :caption: workflow.py
    :language: python

Running the pipeline
--------------------

**Locally:**

.. code-block:: console

    python workflow.py

This executes :code:`main()` directly, which calls :code:`run_local_workflow`. Flyte tasks and
the workflow run as ordinary Python functions in the current process — no containers, no Flyte backend.

**Remotely (Flyte):**

.. code-block:: console

    python workflow.py

The :code:`__main__` block sets :code:`HydraConf(mode=RunMode.MULTIRUN)` before calling :code:`main()`.
MULTIRUN mode is what activates the Flyte launcher — without it, the launcher is never invoked.
See :ref:`flyte-launcher` for details on what happens next.

Overriding config from the CLI
-------------------------------

Because the config is registered with Hydra, all standard Hydra overrides work:

.. code-block:: console

    # Use resnet50 instead of the default resnet18
    python workflow.py train.model=resnet50

    # Override a nested field
    python workflow.py train.model.learning_rate=1e-4

    # Show the rendered config without running
    python workflow.py --cfg job

Pattern walkthrough
--------------------

**Step 1 — Configure Logic**

:code:`builds()` creates a structured config dataclass from a regular class. With
:code:`populate_full_signature=True` the config inherits the full signature including type hints,
which Hydra uses for validation. :code:`MISSING` marks required fields that have no default.

Multiple named variants are registered in a config group using a sub-store:

.. code-block:: python

    model_store = workflow_store(group="model")
    model_store(ModelConf(name="resnet18"), name="resnet18")
    model_store(ModelConf(name="resnet50"), name="resnet50")

The :code:`hydra_defaults` list in :code:`WorkflowConf` selects :code:`resnet18` by default and
places it at :code:`train.model` in the rendered config.

**Step 2 — Implement Logic**

Plain Python. No Flyte, no hydra, no Scaffold. This is intentional — functions are fully testable
in isolation and :code:`zen_call` handles the bridge to the config system.

**Step 3 — Configure Task and Workflow**

:code:`builds(train, ...)` creates a config for the task. The named config
:code:`workflow_store(..., name="default")` provides the concrete values (paths, etc.) that fill
in the :code:`MISSING` fields.

**Step 4 — Implement Task and Workflow**

:code:`@runtime_task` is a drop-in for :code:`@task` that additionally:

- Calls :code:`apply_runtime_cfg(runtime_cfg)` at the start of every remote execution to restore
  logging and other runtime settings inside the container
- Automatically excludes :code:`runtime_cfg` from Flyte's cache key, so changing log verbosity
  never invalidates a cached task result

:code:`zen_call(fn, cfg)` instantiates all config fields (calling :code:`instantiate()` on any
:code:`builds()` sub-config) and passes the results as keyword arguments to :code:`fn`.
In this example, :code:`cfg.model` is a :code:`ModelConf` — zen_call turns it into a :code:`Model` instance.

The :code:`@workflow` receives one :code:`DictConfig` per task plus :code:`runtime_cfg`, all
resolved from the top-level config by :code:`run_local_workflow` (locally) or by the launcher (remotely).

**Step 5 — Run**

:code:`run_local_workflow` maps config keys to workflow inputs by name and executes the workflow.
The :code:`__main__` block adds the :code:`HydraConf(mode=RunMode.MULTIRUN)` entry to the store
and flushes both stores before calling :code:`main()`.

.. note::
    The :code:`launcher_conf.py` file is imported at the top of the workflow file. It defines the
    project-specific Docker image configuration and is kept separate so it can be shared across
    multiple workflow files. See :ref:`deployment` for its contents and all available options.
