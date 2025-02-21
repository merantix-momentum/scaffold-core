.. _entrypoints:

Entrypoints
===========

Scaffold :code:`entrypoint` is a callable class that structures entry points, i.e. python modules, that are supposed to be executed directly.
They are configured using an already parsed hydra :code:`DictConfig`, which is usually provided by using :code:`hydra.main()`.

Scaffold entrypoints aim at:

- Enabling the sharing of functionality through a common interface and reducing boiler code in a project, by isolating steps that are always executed before/after we execute a step, using :code:`EntrypointCallback`.
- Bootstrap projects by adding useful, general functionality like configuring python logging, tracking configuration.
- Ease the hydra integration and define a standard.

See :ref:`example1`, for an example use case of structuring your code and using callbacks.


Minimal usage
-------------
This minimal example mostly just structures your code by

* Defining a callable entry point class which encapsulates your logic
* Using :code:`hydra.main` to parse the config and pass it to the entry point
* Enforcing the expected config schema for the default :code:`EntrypointConf`, which configures the default hydra and logging settings.
  As you can see, we chose to overwrite the default logging option. Scaffold exposes the same options as hydra.
  This enables multiple logging configurations in one workflow config file, for the case that multiple Entrypoints are spread across different flyte tasks.
  You can checkout the structured config definition in the package :code:`scaffold.conf.scaffold.entrypoint.EntrypointConf`.
* Note also that entrypoint definition can take a generic type parameter, which allows us to specify the config type, which is then used to type hint the structured config object in the entrypoint methods.


.. literalinclude:: /../test/docs_examples/snippets/conf/entrypoint_conf.yaml
    :caption: conf/entrypoint_conf.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/entrypoint.py
    :caption: entrypoint.py
    :language: python


EntrypointCallback
----------------------------------------

An :code:`EntrypointCallback` is a simple way to define logic that get executed before or after an entry point, or when an exception occurs.
Implementations inherit from a base class:

.. code-block:: python

    class EntrypointCallback(ABC):
        """Base class for entry point callbacks."""

        def on_run_start(self, entrypoint: Entrypoint, run_args: Tuple, run_kwargs: Dict) -> None:
            """Runs before the entrypoint `run()` method."""
            pass

        def on_run_end(self, entrypoint: Entrypoint, output: Any) -> Optional[Any]:
            """Runs after the entrypoint `run()` method."""
            return output

        def on_exception(self, entrypoint: Entrypoint, exception: BaseException = None) -> None:
            """Runs if an exception is raised in `run()` before reraising the exception."""
            pass


An example for defining your own callback could look something like this:

.. literalinclude:: /../test/docs_examples/snippets/entrypoint_callback.py
    :caption: entrypoint_callback.py
    :language: python


You can also add callbacks through config targets, instead of passing them in as python arguments.
Additionally, you can choose in which order the callbacks are executed (either first in first out: :code:`fifo`, or first in last out: :code:`fifo`).

.. literalinclude:: /../test/docs_examples/snippets/conf/entrypoint_callback_conf.yaml
    :caption: conf/entrypoint_callback_conf.yaml
    :language: yaml

.. note::
    The callbacks from the config are added first, the python argument callbacks are appended!

