.. _flyte-launcher:

Flyte Launcher Reference
=========================

The Scaffold Flyte Launcher is a `Hydra launcher plugin <https://hydra.cc/docs/1.1/advanced/plugins/overview/#launcher>`_
that collapses the build → register → execute cycle of a Flyte workflow into a single command.
This page documents what it does and how all its options work.


How invocation works
--------------------

When you run :code:`python workflow.py` from the :code:`__main__` block, the
:code:`HydraConf(mode=RunMode.MULTIRUN)` entry in the store switches Hydra to multirun mode.
Multirun mode is what activates a Hydra launcher plugin — without it, the launcher is never called
and the workflow runs locally via :code:`main()`.

.. code-block:: python

    if __name__ == "__main__":
        workflow_store(HydraConf(mode=RunMode.MULTIRUN))
        workflow_store.add_to_hydra_store(overwrite_ok=True)
        launcher_store.add_to_hydra_store(overwrite_ok=True)
        main()

What happens when :code:`execution_environment=remote`:

1. Hydra renders the full config and calls the launcher's :code:`launch()` method.
2. The launcher identifies the main :code:`@workflow` in the script (the one not used as a sub-workflow).
3. It builds the Docker image(s) for the tasks (unless :code:`build_images=False`).
4. It serializes and registers the workflow and all tasks with the Flyte backend.
5. If :code:`run=True` (default), it immediately executes the registered workflow.

When :code:`execution_environment=local`, the launcher runs the workflow as a standard Python call —
the same as running without MULTIRUN. This is useful for testing the full launcher code path
without requiring a Flyte backend.


Configuration reference
-----------------------

The launcher is configured via :code:`FlyteLauncherConf` in :code:`launcher_conf.py`. See
:ref:`deployment` for the full setup. The key fields:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Field
     - Default
     - Description
   * - :code:`execution_environment`
     - :code:`remote`
     - :code:`remote` or :code:`local`. Use :code:`local` to test the launcher code path without Flyte.
   * - :code:`endpoint`
     - :code:`localhost:30081`
     - Flyte admin endpoint. Forward with :code:`kubectl port-forward svc/flyteadmin 30081:81 -n flyte`.
   * - :code:`build_images`
     - :code:`True`
     - Build and push Docker images before registration. Set :code:`False` to reuse the last pushed image.
   * - :code:`fast_serialization`
     - :code:`False`
     - Inject local source code into an existing container instead of rebuilding. Fast iteration,
       but the container must already exist with all dependencies installed.
   * - :code:`run`
     - :code:`True`
     - Execute the workflow immediately after registration. Set :code:`False` to register only.
   * - :code:`workflow.version`
     - auto (git hash)
     - Version string for the registered workflow. By default derived from the git branch and commit hash.
   * - :code:`workflow.cron_schedule`
     - :code:`None`
     - Cron expression to schedule the workflow (e.g. :code:`"0 5 * * *"` for 5am daily).
       See :ref:`advanced` for details.
   * - :code:`notifications`
     - :code:`[]`
     - List of :code:`FlyteNotificationConf` objects. See :ref:`integrations`.


Reusing a registered workflow version
--------------------------------------

To execute an already-registered workflow without rebuilding images:

.. code-block:: console

    python workflow.py hydra.launcher.build_images=false hydra.launcher.workflow.version=<version>

The version string is logged at the end of every registration and is also visible in the Flyte UI.


Projects and domains
--------------------

Flyte organizes workflows by **project** (a logical grouping, e.g. one ML use case) and
**domain** (environment: development, staging, production).

The launcher registers to :code:`development` domain by default. The conventional mapping is:

- **development** — feature branch runs from a developer's machine
- **staging** — registered by CI/CD on merge to main
- **production** — registered by CI/CD on a tagged release

The workflow version string automatically encodes the git branch name and commit hash, making it
easy to identify exactly what code a given registered version contains.

Override domain and project via :code:`workflow` config fields:

.. code-block:: python

    FlyteWorkflowConf(project="my-project", domain=FlyteDomainEnum.staging, ...)


Monitoring executions
---------------------

The Flyte UI shows registered workflows, execution history, task outputs and logs.

Alternatively, use :code:`kubectl` to inspect the underlying pods:

.. code-block:: console

    kubectl get pods -n default-development
    kubectl logs -n default-development <pod-name> --follow


FlyteRemote — programmatic execution
--------------------------------------

To trigger an already-registered workflow from Python (e.g. from a backend service or a notebook),
use :code:`FlyteRemoteHelper`:

.. literalinclude:: /../test/docs_examples/snippets/execute_registered_workflows.py
    :caption: execute_registered_workflows.py
    :language: python

The launchplan name is logged at the end of every registration and can also be found in the Flyte UI
by clicking *Launch Workflow*.
