Gotchas
=======

Flyte DictConfig Enum serialization for Hydra schemas
-----------------------------------------------------
In case you want to use `Structured Configs <https://hydra.cc/docs/tutorials/structured_config/schema/>`_ for config type checking, you might want to use an :code:`Enum` to specify a set of valid types.
`flytekitplugins-omegaconf <https://pypi.org/project/flytekitplugins-omegaconf/>`_ should support this behavior and restore the :code:`Enum` types inside a :code:`DictConfig`.
In case you still encounter issues with type serialization in flyte, inheriting from :code:`str` helped some users in the past to circumvent issues with flyte being able to reconstruct the config correctly.
Please raise this issue if this happens to you in the future.

Below is an example of how to correctly specify an :code:`Enum` type constraint:

.. code-block:: python

    from enum import Enum, unique

    from scaffold.hydra.config_helpers import structured_config

    @unique
    class FlyteDomainEnum(str, Enum):  # Only inherit from str if you encounter issues
        development = "development"
        staging = "staging"
        production = "production"

    @structured_config(group="scaffold/flyte_launcher")
    class FlyteWorkflowConfig:
        domain: FlyteDomainEnum = FlyteDomainEnum.development
        ...
        
Not pulling the docker image when adding requirements
--------------------------------------------------------

When using the hydra flyte launcher locally, by default it uses the base image with tag :code:`latest`. In case you introduced new requirements into that base image (merged on main), don't forget to pull that base image again! Otherwise the launcher might use an older version which does not contain the new requirement yet.

In case you introduced a new requirement in a feature branch that hasn't been merged into main yet, the :code:`latest` image used by the launcher locally by default does not contain this requirement! You can, however, tell the launcher to use a specific image version which e.g. has been built on our feature branch:

.. code-block:: console

    python flyte_workflows/.../workflow.py -m hydra/launcher=flyte hydra.launcher.workflow.default_image.base_image_version=ef2da5c
