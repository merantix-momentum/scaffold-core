.. _hydra:

Hydra
=======

Scaffolds ``hydra`` subpackage provides some utility to ease the usage of hydra in projects.
Some highlights:

- The ``structured_config`` decorator, that can be used instead of a ``dataclass`` decorator for a schema definition,
  which already takes care of registering the schema with hydra.
- An alternative to hydra's ``compose`` function with extra functionality
- An alternative to hydra's ``initialize`` which does not fail if there is an existing hydra instance.


Also see :ref:`example1`.

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


Initialize and compose
------------------------

Hydra provides the :code:`hydra.initialize` and :code:`hydra.compose` with the `compose API <https://hydra.cc/docs/advanced/compose_api/>`_.
Scaffold extends this API slightly, while staying compatible with the original hydra usage.

initialize
""""""""""""

:code:`scaffold.hydra.initialize` mainly add a minor feature: Not breaking if a hydra instance exists, but using the existing one.
It also provides easier access to the global hydra instance, and enables :code:`scaffold.hydra.compose` to be more robust.

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

