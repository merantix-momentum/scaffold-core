.. _advanced:

Advanced Patterns
=================

Dynamic workflows
-----------------

A `dynamic workflow <https://docs.flyte.org/en/latest/user_guide/advanced_composition/dynamic_workflows.html>`_
lets you write conditional or data-dependent control flow that Flyte evaluates at runtime rather
than at compile time.

.. note::
    Prefer static workflows when possible — dynamic workflows only fail at runtime, making
    errors harder to catch early. For running the same function many times with different inputs,
    a `map task <https://docs.flyte.org/en/latest/user_guide/advanced_composition/map_tasks.html>`_
    is usually the better choice.

Dynamic workflows are opaque to Flyte's task discovery. The launcher cannot automatically detect
tasks nested inside a :code:`@dynamic` function. Declare them explicitly with :code:`@mxm_register`
so the launcher can find and register them:

.. code-block:: python

    from flytekit import dynamic, workflow
    from scaffold.flyte.core import mxm_register

    @mxm_register(nodes=[my_task])
    @dynamic
    def dynamic_pipeline(cfg: DictConfig, runtime_cfg: DictConfig) -> None:
        my_task(cfg=cfg, runtime_cfg=runtime_cfg)

    @workflow
    def pipeline(cfg: DictConfig, runtime_cfg: DictConfig) -> None:
        dynamic_pipeline(cfg=cfg, runtime_cfg=runtime_cfg)

Note that a static :code:`@workflow` is still required as the entry point — the launcher always
needs a top-level workflow to identify.


Cron Jobs
---------

Workflows can run on a cron schedule by setting :code:`cron_schedule` on :code:`FlyteWorkflowConf`:

.. code-block:: python

    # launcher_conf.py
    launcher_store(
        FlyteLauncherConf(
            workflow=FlyteWorkflowConf(
                ...,
                cron_schedule="0 5 * * *",  # every day at 5am
            )
        ),
        name="flyte",
        group="hydra/launcher",
    )

The recommended pattern is to leave :code:`cron_schedule` unset in the config file and only apply
it in CI/CD for staging/production registrations, so development runs are never accidentally
scheduled:

.. code-block:: console

    # In your CI/CD pipeline (e.g. Cloud Build), targeting the staging domain:
    python workflow.py hydra.launcher.workflow.cron_schedule="0 5 * * *" \
                       hydra.launcher.workflow.domain=staging

**Managing a schedule after registration:**

To deactivate an active launchplan (after port-forwarding :code:`flyteadmin 30081:81`):

.. code-block:: console

    flytectl update launchplan -p default -d development \
        --version <version> <launchplan-name> --archive

Re-activate with :code:`--activate`. The launchplan name is logged at the end of registration
and shown in the Flyte UI under *Launch Workflow*.

.. note::
    Flyte requires workflows with a cron schedule to accept a :code:`kickoff_time` argument:

    .. code-block:: python

        from datetime import datetime

        @workflow
        def pipeline(cfg: DictConfig, runtime_cfg: DictConfig, kickoff_time: datetime = datetime.now()) -> ...:
            ...


Multi-input workflows
---------------------

Some workflows accept additional inputs beyond the config — for example, a data path or a request
payload passed at execution time rather than baked into the config. The workflow interface supports
this naturally:

.. code-block:: python

    @workflow
    def pipeline(cfg: DictConfig, data_string: str, runtime_cfg: DictConfig) -> str:
        ...

:code:`run_local_workflow` maps config keys to workflow inputs by name. Any workflow parameter
not found in the config is left to the workflow's default value (a warning is logged) and can be passed when
calling the workflow function. For local execution, pass the extra arguments directly to :code:`run_local_workflow`:

.. code-block:: python

    run_local_workflow(pipeline, cfg, data_string="my data")

For remote execution, we need to configure the launcher to not run the workflow directly after registration (as there we want to provide the extra arguments at execution time):

.. code-block:: python

    # launcher_conf.py
    launcher_store(
        FlyteLauncherConf(
            ...,
            run=False,  # Don't execute immediately after registration
        ),
        name="flyte",
        group="hydra/launcher",
    )

Then we can execute the workflow with the extra arguments using :code:`FlyteRemote`:

.. code-block:: python

    from scaffold.flyte.flyte_utils import FlyteRemoteHelper

    LAUNCHPLAN = "hydra_workflow_cfg_workflow_with_extra_inputs_default_0"
    ADMIN_ENDPOINT = "localhost:30081"
    DOMAIN = "development"

    dummy_string = "my data"

    # execute the workflow that was registered by flyte launcher before
    FlyteRemoteHelper(domain=DOMAIN, admin_endpoint=ADMIN_ENDPOINT).execute_flyte_launchplan(
        LAUNCHPLAN, {"data_string": dummy_string}
)
