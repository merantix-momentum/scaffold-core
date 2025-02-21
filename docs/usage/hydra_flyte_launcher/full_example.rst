.. _full-example-workflow:

Full Example Workflow
=====================
In general we need three components for the flyte launcher to work

#. A :code:`workflow.py` file which defines a flyte :code:`@workflow` and at least one :code:`@task` and uses :code:`hydra.main` as illustrated in the previous steps
#. At least one :code:`Dockerfile` which will be built in order to launch the :code:`@task`
#. A hydra config file :code:`flyte_launcher.yaml` which configures the hydra launcher

In order to provide a good starting point which should be modified to your need, we provide a generator.


Create example files with the generator
---------------------------------------

We can use the workflow generator to create a simple flyte workflow::

   mx g Workflow

The generated workflow module contains a flyte workflow that accepts an input :code:`DictConfig` and a :code:`kickoff_time` argument.
It will simply separate the input config into two configs for training and evaluation. The following tasks should implement training and evaluation with their respective configs.
Note also the `flyte_launcher.yaml` configuration of the launcher itself where you can adapt the base docker image and other things.

Each workflow also gets its own environment defined by the Dockerfile, however there is nothing preventing you from nesting multiple workflows under
the same environment, which can be easily re-used.

Before interacting with a remote flyte deployment, we need to forward the flyteadmin service to our local machine::

    kubectl port-forward --address 0.0.0.0 svc/flyteadmin 30081:81 -n flyte

.. note::
    Your :code:`kubectl` needs to be authenticated to the cluster, e.g. by using :code:`mx switch_gcp_project <your-gcp-project-name>`


To execute the pipeline, execute::

   python workflows/<workflow name>/<workflow name>/workflow.py

This will build the necessary images for the tasks and workflows, will register and execute them, as described in :ref:`minimal-usage`.
To see the related image names and parameters check :code:`workflows/<workflow name>/<workflow name>/workflow_bundle.yaml`, :code:`workflows/<workflow name>/flyte_launcher.yaml` and :code:`workflows/<workflow name>/<workflow name>/workflow.py`.

Monitor the execution
---------------------
Flyte provides a UI which you can use to check the registered workflows and show executions outputs or errors.

Since flyte executes the workflows as pods in kubernetes, you can always check which pods are running using::

    kubectl get pods -n default-development

If you are not sure in which namespace the pods are running, you can also check::

    kubectl get pods --all-namespaces

and check the running logs of the pod using::

    kubectl logs -n default-development <your-pod-name> --follow


Flyte projects and domains
--------------------------

Flyte groups workflows into different projects and different domains.

If in your project there only is one use case to solve, only use the :code:`default` project.
The :code:`default` project can host multiple workflows.
If your project has multiple use cases, it might make sense to group them into flyte projects.

Every project has three domains: **development, staging, production**.
We decided that we want to associate these domains with feature branches, the main branches, and git tags/releases respectively.

The flyte launcher by default, when run form the CLI, always registers the workflow in the development domain and the workflow version includes your feature branch name as well as the git hash.
This allows us to easily determine what code a workflow version contains.


Hurray!
-------
.. note::
    You are now able to register and execute a workflow in the cloud and do so continuously via cloudbuild right from git version control!
    To use these capabilities to their full potential there are of course additional steps needed, e.g. building in testing steps into your pipeline that make sure everything is running as expected.
    The upcoming sections are optional and more "advanced" covering specific use cases!
