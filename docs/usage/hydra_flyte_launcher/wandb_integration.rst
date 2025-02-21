WandB integration
=================

To enable the logging of metrics and artifacts from Flyte workflows to WandB some additional setup is required
to facilitate authentication with our WandB deployment.

First, a secret containing user handles and Api-Keys can be generated with the `mx g WandBAccess` generator and
a subsequent `devspace deploy --deployments=wandb_access` call.

Secondly, your API-key has to be exposed by setting several environment variables. We recommend doing this once
in your `.zshrc` (or `.bashrc` accordingly) as this does not change across projects:

.. code-block:: bash

    export WANDB_USERNAME=<your Github handle>  # the Github handle allows logging from jobs triggered by git commit / cloudbuild
    export WANDB_API_KEY=<your Wandb api key>

Additionally, augment the decorators of tasks using wandb logging with the following request:

.. code-block:: python

    secret_requests=[Secret(key=scaffold.wandb.helper.WANDB_KEY, group=scaffold.wandb.helper.WANDB_SECRET)],

If you call wandb.init() explicitly, rather than using the :code:`WandBCallBack` also add this line prior to the call:

.. code-block:: python

    scaffold.wandb.helper.wandb_environment_setup(username=<your github handle>)