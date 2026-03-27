.. _gotchas:

Common Gotchas
==============


Enum serialization in Flyte
----------------------------

Flyte serializes task inputs and outputs through its type system. If you use a Python
:code:`Enum` inside a :code:`DictConfig`, you may encounter issues with Flyte being unable to
reconstruct the enum value correctly on the remote side.

`flytekitplugins-omegaconf <https://pypi.org/project/flytekitplugins-omegaconf/>`_ is designed to
handle this and restore :code:`Enum` types inside a :code:`DictConfig`. If you still see issues,
inheriting your enum from :code:`str` has worked as a workaround:

.. code-block:: python

    from enum import Enum, unique

    @unique
    class SplitEnum(str, Enum):  # str inheritance as fallback if Flyte can't reconstruct
        train = "train"
        val = "val"
        test = "test"

Please raise an issue if you encounter this so we can track it.


Stale base image after adding requirements
-------------------------------------------

The launcher builds your workflow image on top of a **base image**. By default the base image is
pulled with the :code:`latest` tag. If you merged new Python requirements into main but haven't
pulled the updated base image, the launcher will silently use the old one — your new dependency
will be missing at runtime.

**Fix:** pull the latest base image before registering, or pin
:code:`base_image_version` to a specific commit hash while on a feature branch:

.. code-block:: console

    python workflow.py hydra.launcher.workflow.default_image.base_image_version=<commit-hash>

See :ref:`deployment` for the full :code:`FlyteDockerImageConfig` reference.


Google Cloud SDK missing in custom task images
-----------------------------------------------

Flyte uses Google Cloud Storage internally for type serialization, even if your tasks don't
explicitly write to GCS. If a task runs in a custom container image that does not have the
Google Cloud SDK installed, it will fail with a cryptic storage error.

Make sure any custom image used via :code:`container_image=` has the Google Cloud SDK installed.
See :ref:`deployment` for the custom images setup.


Launcher not triggered — forgot MULTIRUN
-----------------------------------------

The Flyte launcher is a Hydra launcher plugin and is only invoked in **multirun** mode. If you run
:code:`python workflow.py` without having added :code:`HydraConf(mode=RunMode.MULTIRUN)` to the
store in :code:`__main__`, Hydra runs in normal single-run mode and calls :code:`main(cfg)`
directly — the launcher is never triggered and no remote execution happens.

Always add this in :code:`__main__`:

.. code-block:: python

    if __name__ == "__main__":
        workflow_store(HydraConf(mode=RunMode.MULTIRUN))
        workflow_store.add_to_hydra_store(overwrite_ok=True)
        launcher_store.add_to_hydra_store(overwrite_ok=True)
        main()


Dynamic workflow tasks not registered
---------------------------------------

Tasks nested inside a :code:`@dynamic` function are opaque to Flyte's static analysis — the
launcher cannot discover them automatically. You must declare them explicitly with
:code:`@mxm_register`. See :ref:`advanced` for details.
