.. _deployment:

Deployment Configuration
========================

This page covers what you need to configure to deploy a workflow to a remote Flyte cluster:
the launcher config, Docker images, and per-task image overrides.


Launcher config
---------------

The launcher config is defined in a separate :code:`launcher_conf.py` file that lives alongside
your workflow. It is imported by the workflow file and its store is flushed in :code:`__main__`:

.. literalinclude:: /../test/docs_examples/snippets/launcher_conf.py
    :caption: launcher_conf.py
    :language: python

The :code:`FlyteDockerImageConfig` fields:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Field
     - Description
   * - :code:`base_image`
     - The image to build *from* in the Dockerfile (:code:`ARG BASE_IMAGE`). Typically a project base
       image with all dependencies pre-installed.
   * - :code:`base_image_version`
     - Tag of the base image. Use a pinned commit hash when working off a feature branch that has not
       been merged to main yet, otherwise the default :code:`latest` tag may not contain your changes.
   * - :code:`target_image`
     - Registry path where the built image is pushed. Flyte pods use this image as their runtime environment.
   * - :code:`target_image_version`
     - Tag of the target image. Defaults to the workflow version (git hash) so each registration gets a
       distinct, traceable image.
   * - :code:`dockerfile_path`
     - Path to the Dockerfile, relative to the project root.
   * - :code:`docker_context`
     - Docker build context, relative to the project root. Usually :code:`"."`.
   * - :code:`flyte_image_name`
     - Internal name used to reference this image in task decorators. Must be :code:`"default"` for the
       default image; any string for extra images.

.. tip::
    The default :code:`target_image_version` interpolates to :code:`hydra.launcher.workflow.version`,
    so image versions and workflow versions always stay in sync. You rarely need to override this.


Skipping image builds
---------------------

Building images on every run is slow during active development. Two escape hatches:

**Reuse the last pushed image** — skip the build step entirely and use whatever image is already
in the registry under the current version tag:

.. code-block:: console

    python workflow.py hydra.launcher.build_images=false

**Fast serialization** — inject your local source code into an existing container without rebuilding.
The container must already exist with all dependencies installed. Useful when you only changed Python code:

.. code-block:: python

    # In launcher_conf.py
    launcher_store(LauncherConf(fast_serialization=True, ...), ...)

Or as an override:

.. code-block:: console

    python workflow.py hydra.launcher.fast_serialization=true


Custom images per task
-----------------------

Tasks within one workflow can run in different containers — for example, a GPU training task
alongside a CPU data preprocessing task.

Define the extra image in :code:`FlyteWorkflowConfig.extra_images` and reference it by
:code:`flyte_image_name` in the task decorator:

.. code-block:: python

    # launcher_conf.py
    from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteDockerImageConfig, FlyteWorkflowConfig

    launcher_store(
        LauncherConf(
            workflow=FlyteWorkflowConfig(
                default_image=FlyteDockerImageConfig(
                    base_image="<registry>/base",
                    target_image="<registry>/workflow",
                    dockerfile_path="Dockerfile.flyte",
                    flyte_image_name="default",
                ),
                extra_images=[
                    FlyteDockerImageConfig(
                        base_image="pytorch/pytorch",
                        base_image_version="2.3.1-cuda11.8-cudnn8-runtime",
                        target_image="<registry>/workflow-gpu",
                        dockerfile_path="Dockerfile.gpu",
                        flyte_image_name="gpu",
                    ),
                ],
            )
        ),
        name="flyte",
        group="hydra/launcher",
    )

Reference the image by name in the task decorator using Flyte's image interpolation syntax:

.. code-block:: python

    @runtime_task(
        requests=Resources(mem="16Gi", cpu="4", gpu="1"),
        container_image="{{.images.gpu.fqn}}:{{.images.gpu.version}}",
    )
    def train_task(cfg: DictConfig, runtime_cfg: DictConfig, data: list[str]) -> str:
        return zen_call(train, cfg, data=data)

.. warning::
    If a task container needs access to Google Cloud Storage (including Flyte's internal type
    transformer serialization), make sure the Google Cloud SDK is installed in that container.
