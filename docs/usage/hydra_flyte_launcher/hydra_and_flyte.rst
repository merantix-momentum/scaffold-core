
Hydra + Flyte
=============

In this section we will cover and motivate some design choices for using hydra and flyte together.

We will not jump into the full infrastructure setup or launch flyte pipelines in a kubernetes environment yet, but will only show flyte piplines which run locally as python code.
For setting up the flyte infrastructure see the `documentation <https://merantix-momentum.slite.com/app/docs/rir8Hd-S9GHStK#b3dff650>`_.
For running a full pipeline in kubernetes, you can take a look at the :ref:`full-example-workflow`.

.. note::
    Make sure to install :code:`scaffold[all]` or :code:`scaffold[flyte]` in order for this to work.
    This does not only install public flyte dependencies, but also our private :code:`flytekitplugins-hydra` package, which is needed for `DictConfig` type hints (more details below).

.. _minimal-usage:

Minimal Usage (Single Task)
---------------------------
For running anything in flyte, you at least need one :code:`workflow` which contains at least one :code:`task`.
Before going into more complex cases, we will explain the core ideas for how to use hydra and flyte with the following example:

.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_flyte_conf.yaml
    :caption: conf/main_hydra_flyte_conf.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/main_hydra_flyte.py
    :caption: main_hydra_flyte.py
    :language: python

Running this code will produce the exact same output as before.

**Steps that are triggered when executing this code:**

#. The :code:`main()` function is locally executed and :code:`hydra.main()` is triggered, which will render the full config. The body of :code:`main()` is not reached yet.
#. Flyte recognizes that a workflow and tasks are used, and "compiles" the pipeline, while checking type consistency between all workflows and tasks.
#. If the file is executed via :code:`python main_hydra_flyte.py` the whole workflow and all tasks will be called as normal python functions **locally**.
#. The file can be executed to run on a **remote** cluster via :code:`python main_hydra_flyte.py -m`:

   #. The launcher will identify the "main workflow" (The only workflow not contained in any other workflow) and recursively detect all flyte tasks and sub-workflows.
   #. We don't want to run the module locally but want to register it in the flyte backend running in kubernetes. Each :code:`task` will run in a single docker container (managed by something called a kubernetes pod). The :code:`workflow` itself will not get a pod, but just defines how tasks are linked.
   #. Instead of going into the body of :code:`main()`, the flyte launcher locally builds the docker images for each task (they use the same by default), copies over the current code, and pushes the images to the artifact registry.
   #. Then the workflow is registered with the flyte backend as a workflow version, pointing to the docker images it needs in order to run every task.
   #. The launcher (by default) executes the workflow immediately.

Ideas that motivated this setup
'''''''''''''''''''''''''''''''

#. **A single CLI command for execution**:
   It should be simple and fast to launch a workflow either locally or in the cloud.
#. **Same code for running locally or on kubernetes**:
   We would like to execute the same file when running in any environment, so that we do not have to adapt the logic in two different files every time.
   (**Limitation**: When different resources per task are needed (e.g. a spark cluster or a different GPU machine) this is of course not possible to perfectly replicate locally.)
#. **Hydra launcher plugin**:
   We would like to use the hydra launcher plugin in order to encapsulate all the logic that is needed to launch a flyte workflow in kubernetes.
   Users do not have to change any python code in order to change the execution environment from local to cloud, and can trigger and configure the launch via the CLI.
   Use :code:`execution_environment` argument to specify how you want to execute your code.
#. **Configuring every workflow and task with one hydra DictConfig**:
   Since hydra provides :code:`DictConfig` objects it makes sense to have a workflow config that has sub configs for every task.
   This also simplifies the function signature of tasks as well as the versioning of workflow configurations, since we do not have to keep track of a large number of unconnected function arguments.
   Additionally flyte provides a caching mechanism that prevents tasks from being executed again when the inputs to the task functions don't change (checkout the info below for more details).
   We want to keep all task configurations separate so that some tasks can be cached and some are executed if something changed.
#. **Flexibility and control**:
   The user is able to change every step of the pipeline if needed, while having a solid starting point which is informed by best practices.
   We do not want to enforce a specific flyte workflow structure, but want to standardize and easy the launching process.


.. note::
    Flyte can `cache outputs of tasks <https://docs.flyte.org/en/latest/user_guide/development_lifecycle/caching.html#caching>`_.
    When run in kubernetes as opposed to locally, the different task functions will be run in different docker containers in different pods and potentially even on different nodes.
    Flyte needs to be able to transfer the inputs and outputs from one task to another.
    To do that, it serializes the return values into a database or blob storage.
    Since out of the box Flyte doesn't know how to serialize DictConfig objects, we provide a custom type transformer plugin `flytekitplugins-omegaconf <https://pypi.org/project/flytekitplugins-omegaconf/>`_ that enables Flyte to do this.


Running Multiple Tasks
----------------------
When running multiple tasks, we want to keep them logically separate.

A straight forward way to achieve this is to introduce another task that splits up the config into task specific sub configs.
This way, every tasks gets cached individually if any of the task sub-configs change.
We can't just separate the configs inside the :code:`workflow`, because this code will never actually run in a flyte deployment.


.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_flyte_two_tasks_conf.yaml
    :caption: conf/main_hydra_flyte_two_tasks_conf.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/main_hydra_flyte_two_tasks.py
    :caption: main_hydra_flyte_two_tasks.py
    :language: python


Defining workflows with multiple inputs
----------------------------------------
Sometimes we want to create workflows, that take in not just a configuration but also some data to be processed.
This can be the case if we want to run a flyte workflow multiple times on different data, for example if we trigger
such a workflow execution from a backend.
The example below demonstrates a clean separation between configuration of a pipeline,
and the input data that should be processed.



.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_flyte_multiple_inputs.yaml
    :caption: conf/main_hydra_flyte_multiple_inputs.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/main_hydra_flyte_extra_inputs.py
    :caption: main_hydra_flyte_extra_inputs.py
    :language: python


Executing workflows
-----------------------
Launching via scaffolds Hydra Flyte Launcher will by default always register a new version of the workflow.
If you want to launch an existing workflow, you can do so using the following overwrites:

.. code-block:: bash

    python3 main_hydra_flyte.py \
        hydra.launcher.build_images=false \
        hydra.launcher.workflow.version=<registered-workflow-version> \
        model.learning_rate=0.01 ...

This reduces the total amount of registered workflow versions and no docker images have to be built or pushed.
Registering a new version should only be needed if code or the docker images that are used change.
Executing a workflow from python or with extra arguments (see section above) with values, which are different than the defaults
defined in code, can not be done with the Hydra Flyte Launcher and need Flyte Remote.
One alternative is to execute a workflow via the flyte UI where you can manually specify the values of the arguments.

However, the best way is often via `FlyteRemote <https://docs.flyte.org/projects/flytekit/en/latest/remote.html>`_ .
Scaffold also comes with a simple utility class that can be used to interact with the FlyteRemote module:

.. literalinclude:: /../test/docs_examples/snippets/execute_registered_workflows.py
    :caption: execute_registered_workflows.py
    :language: python
