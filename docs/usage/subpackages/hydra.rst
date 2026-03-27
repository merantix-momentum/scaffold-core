.. _hydra:

Hydra
=======

Scaffold's ``hydra`` subpackage provides utilities to ease the usage of Hydra in projects.

.. warning::
    The helpers described in this page (``structured_config``, ``compose``, ``initialize``) are
    **deprecated** and will be removed in a future release. New projects should use
    `hydra-zen <https://mit-ll-responsible-ai.github.io/hydra-zen/>`_ instead —
    see the :ref:`hydra-zen section below <hydra-zen-section>`.



Deprecated: @structured_config
--------------------------------

.. deprecated::
    Use :func:`hydra_zen.builds` and :func:`hydra_zen.store` instead.

Scaffolds ``hydra`` subpackage provides some utility to ease the usage of hydra in projects.
Some highlights:

- The ``structured_config`` decorator, that can be used instead of a ``dataclass`` decorator for a schema definition,
  which already takes care of registering the schema with hydra.
  - An alternative to hydra's ``compose`` function with extra functionality
- An alternative to hydra's ``initialize`` which does not fail if there is an existing hydra instance.


Also see :ref:`quickstart`.

Registering schemas with @structured_config
--------------------------------------------

:code:`structured_config` is a replacement for :code:`dataclass` when used with hydra schemas, which also integrates the
config registration with the `hydra config store <https://hydra.cc/docs/tutorials/structured_config/config_store/>`_.
This puts the schema definition and the registration at one place.

.. note::
    Because a decorator is only triggered on function definition, the module of the class has to be imported at some point
    during an execution. If hydra is not able to find your schema, try importing it in your script.

.. code-block:: python

    from scaffold.hydra.config_helpers import structured_config
    from omegaconf import MISSING


    @structured_config(group="your_package/schemas")
    class MyConfig:
        reasons_for_this_key_name: int = MISSING
        foo: str = "bar"

When specifying your config, you can then use this schema by finding it with the class name by default:

.. code-block:: yaml

    defaults:
    - /your_package/schemas/MyConfig@_here_  # You can also apply it to other subkeys than @_here_


Deprecated: Initialize and compose
-------------------------------------

.. deprecated::
    These helpers are no longer needed. Use hydra's own ``hydra.initialize`` directly,
    or define configs with :func:`hydra_zen.builds` and :func:`hydra_zen.store`.

Hydra provides the :code:`hydra.initialize` and :code:`hydra.compose` with the `compose API <https://hydra.cc/docs/advanced/compose_api/>`_.
Scaffold extends this API slightly, while staying compatible with the original hydra usage.

initialize
""""""""""""

:code:`scaffold.hydra.initialize` adds one feature: it does not fail if a hydra instance already exists, but
uses the existing one instead.

.. code-block:: python

    import hydra
    import scaffold.hydra as sc_hydra
    from hydra.core.global_hydra import GlobalHydra

    if __name__ == "__main__":
        with hydra.initialize(config_path=None):
            hydra_instance = GlobalHydra.instance()
            with sc_hydra.initialize(exists_ok=True) as instance:  # This now works
                assert id(instance) == id(hydra_instance)


compose
""""""""""""
:code:`scaffold.hydra.compose` extends :code:`hydra.compose` with a few features.

Lets start with the same schema from before:

.. code-block:: python

    from scaffold.hydra.config_helpers import structured_config
    from omegaconf import MISSING


    @structured_config(group="your_package/schemas")
    class MyConfig:
        reasons_for_this_key_name: int = MISSING
        foo: str = "bar"


1. No need to call :code:`hydra.initialize` before composing a config, since this will use :code:`scaffold.hydra.initialize`
   internally.

.. code-block:: python

    cfg = compose("your_package/schemas/MyConfig")

2. It's able to compose a config from any :code:`StructuredConfig` class, which does not require the user to know the path
   in the config store, where the structured config was registered.

.. code-block:: python

    cfg = compose(MyConfig)

3. Can check for missing values right away, instead of only throwing an exception when trying to access them.

.. code-block:: python

    cfg = compose(MyConfig, check_missing=True)

4. Automatically returns the leaf node of the given config. When calling the original
   hydra.compose("/my/grouped/config"), this results in a config with the keys config["my"]["group"][...].
   Setting return_leaf=True (Default), scaffold.hydra.compose will automatically return the result of config["my"]["group"]
   instead of adding all group keys.

.. _hydra-zen-section:

hydra-zen
---------

New projects should use `hydra-zen <https://mit-ll-responsible-ai.github.io/hydra-zen/>`_ for
configuration instead of the deprecated helpers above.
See :ref:`ml-pipelines` for end-to-end examples using hydra-zen with Scaffold.
