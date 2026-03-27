.. _integrations:

Integrations
============

Secrets
-------

Tasks that need API keys or other credentials at runtime use Flyte's secrets mechanism.
The general pattern is:

1. Deploy a Kubernetes secret containing the credential (usually via a generator)
2. Request the secret in the :code:`@runtime_task` decorator
3. Retrieve it inside the task body

**WandB example:**

.. code-block:: console

    # Generate and deploy the secret (one-time, per cluster)
    mx g FlyteWandBSecret
    devspace deploy --deployments=wandb_access

Request the secret in the task decorator:

.. code-block:: python

    from flytekit import Secret
    import scaffold.wandb.helper

    @runtime_task(
        requests=Resources(...),
        secret_requests=[
            Secret(key=scaffold.wandb.helper.WANDB_KEY, group=scaffold.wandb.helper.WANDB_SECRET)
        ],
    )
    def train_task(cfg: DictConfig, runtime_cfg: DictConfig, ...) -> ...:
        ...

For local execution and CI/CD, set the API key via environment variables (add to :code:`.zshrc`):

.. code-block:: bash

    export WANDB_USERNAME=<your GitHub handle>
    export WANDB_API_KEY=<your WandB api key>

If calling :code:`wandb.init()` directly (rather than via :code:`WandBCallback`), call the
helper first to configure the environment from the secret:

.. code-block:: python

    scaffold.wandb.helper.wandb_environment_setup(username=<your github handle>)
    wandb.init(...)


Notifications
-------------

The launcher can send email or Slack notifications on specific workflow execution phases.
Configure them in :code:`launcher_conf.py`:

.. code-block:: python

    from hydra_plugins.flyte_launcher_plugin._flyte_launcher import (
        FlyteNotificationConfig, FlyteNotificationEnum, FlyteWorkflowExecutionPhaseEnum,
    )

    launcher_store(
        LauncherConf(
            ...,
            notifications=[
                FlyteNotificationConfig(
                    type=FlyteNotificationEnum.email,
                    phases=[
                        FlyteWorkflowExecutionPhaseEnum.SUCCEEDED,
                        FlyteWorkflowExecutionPhaseEnum.FAILED,
                    ],
                    recipients=["team@example.com"],
                ),
                FlyteNotificationConfig(
                    type=FlyteNotificationEnum.slack,
                    phases=[FlyteWorkflowExecutionPhaseEnum.FAILED],
                    recipients=["alerts@slack.example.com"],
                ),
            ],
        ),
        name="flyte",
        group="hydra/launcher",
    )

For more details, see the
`Flyte notifications documentation <https://docs.flyte.org/en/latest/deployment/configuration/notifications.html>`_.
