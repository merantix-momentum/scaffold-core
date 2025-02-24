
Fast Prototyping
=================================

To facilitate rapid scripting and cloud execution of prototypes, our Hydra Flyte Launcher can be used to execute
workflows defined as stand-alone scripts without specification of a hydra config, access to a github repository or
building specific images.

Executing workflows without a custom config
-------------------------------------------
If you do not need to define any parameters to be specified at run invocation, it is sufficient to call the launcher
with the skeleton structured config class defined in scaffold. Simply alter the configuration location in your workflow
decorator to:

.. code-block:: python

    @hydra.main(version_base=None, config_name="hydra/launcher/flyte")
    def main(cfg: DictConfig) -> None:
        ...

No further yaml configs need to be defined. However, be aware that the default value for the docker image points to the
flyte image in the central devops repository. If images with additional dependencies are required, these have to be
specified through overrides, either in a :code:`flyte_launcher.yaml` or manual via:

.. code-block:: console

    python flyte_workflows/.../workflow.py -m hydra.launcher.workflow.default_image.target_image=<image-location>

Executing workflows without a github repo
-----------------------------------------
Typically, workflow versions are named based on the github branch in which they were defined. It is possible to register
scripts outside of repositories in which case version names will be generated randomly. Alternatively, a version name can
be specified in the :code:`flyte_launcher.yaml` or on the command line - however, this name has to be unique whenever
the launcher is executed!

.. code-block:: console

    python flyte_workflows/.../workflow.py -m hydra.launcher.workflow.target_image_version=<version-name>

Executing workflows without building docker images
--------------------------------------------------
Since building and uploading a docker container with all requirements can be time-consuming, it is possible to merely
copy your source code into an existing container and execute the workflow in this environment.

This mode is triggered by setting:

.. code-block:: console

    python flyte_workflows/.../workflow.py -m hydra.launcher.build_images=False

When images are not being build from scratch, flyte uses the container under
:code:`<target_image>:<target_image_version>` as an environment to execute your code in
(Note: as described above, the default configs point towards an image with only flytekit installed).

If images are being build, the :code:`base_image` and :code:`base_image_version` are passed into the Dockerfile
instructions as arguments to identify the image to build upon. The created images are then registered under
:code:`<target_image>:<target_image_version>` and used as new environments for workflow execution.
