
Custom Task Images
=================================

.. warning::
    If you build your own custom docker image, and the task needs access to google cloud buckets (could even be because flyte is triggering a specific type transformer that serializes to a bucket),
    you need to make sure to install the google cloud SDK inside the container.

Within a single workflow, Flyte tasks can be executed in different containers. Use the :code:`container_image` argument in the task decorator to insert your custom image name for the task:

.. code-block:: python
    
    @task(
      cache=True,
      cache_version="1.0",
      requests=Resources(mem="1Gi", cpu="1"),
      container_image="{{.images.custom_image.fqn}}:{{.images.custom_image.version}}",
    )
    def my_task(cfg: DictConfig) -> str:
    # This task uses an image named custom_image, and the version of the image that was set in the configs. By default this is
    # interpolated to match the version of the default image to make sure the most recent image is being used by the task.
   
You need to edit :code:`flyte_launcher.yaml` to include custom images. Add your images under the key :code:`hydra.launcher.workflow.extra_images`. The :code:`flyte_image_name` key should match the image name used in the task decorator:
Note, that `target_image` should be unique across all specified images.

.. code-block:: yaml
    :caption: flyte_launcher.yaml
    :emphasize-lines: 10, 12, 13, 14, 15, 17

    defaults:
      - /scaffold/flyte_launcher/FlyteWorkflowConfig@hydra.launcher.workflow

    hydra:
      mode: MULTIRUN # enables execution with flyte launcher, which not possible with a single run
      launcher:
        execution_environment: remote
        workflow:
          default_image:
            base_image: pytorch/pytorch  # Provide a base image with installed dependencies
            base_image_version: 2.3.1-cuda11.8-cudnn8-runtime
            base_image_version: latest
            target_image: <url>/<your workflow name>  # Where the workflow image created by provided Dockerfile gets pushed to. Flyte pods use this image as runtime environment.
            dockerfile_path: infrastructure/docker/Dockerfile.flyte
            docker_context: . # Relative to project root, i.e. where your "setup.py" is.
            flyte_image_name: default
          extra_images:
            - base_image: <url>/flyte # Your flyte image
              base_image_version: latest
              target_image: <url>/<your workflow name>-custom_image # Should be different from default image
              dockerfile_path: infrastructure/docker/Dockerfile.flyte.custom_image
              docker_context: . # Relative to project root, i.e. where your "setup.py" is.
              flyte_image_name: custom_image
          project: default
          domain: development
