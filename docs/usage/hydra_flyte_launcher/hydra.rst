
Hydra
=====

In this section we will cover the basic mechanics of hydra, which are the most useful in most cases.
They also illustrate some capabilities of hydra, which can help to understand how hydra and flyte work together.

Minimal usage
-------------

The simplest common use of hydra only requires a :code:`yaml` configuration file and adding :code:`hydra.main()` to our script.
Also see the hydra basic tutorial for `specifying a config file <https://hydra.cc/docs/tutorials/basic/your_first_app/config_file/>`_ for more info.

.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_conf.yaml
    :caption: conf/main_hydra_conf.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/main_hydra.py
    :caption: main_hydra.py
    :language: python

You can structure the yaml file however you want, and access all values from within your script with dot notation.

Hydra also provides you with a powerful CLI. A quick cheat sheet for some useful functionalities:


.. list-table::
   :widths: 40 60

   * - Overwriting a value 
     - :code:`python3 main_hydra.py model.learning_rate=0.2`
   * - Adding a new value 
     - :code:`python3 main_hydra.py +model.new_val=0.2`
   * - Multi-run with multiple values (See `Multi-run <https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/>`_ for more info)
     - :code:`python3 main_hydra.py --multirun model.learning_rate=0.2,0.3`
   * - Help with specific usage of hydra 
     - :code:`python3 main_hydra.py --hydra-help`
   * - See available (non-hydra) configuration groups and options
     - :code:`python3 main_hydra.py --help`
   * - Showing your rendered config (See hydra-help for other options)
     - :code:`python3 main_hydra.py --cfg job`
   * - Showing more extensive hydra info (See hydra-help for other options)
     - :code:`python3 main_hydra.py --info all`


.. note::
    The Multi-run flag triggers the hydra `Launcher <https://hydra.cc/docs/1.1/advanced/plugins/overview/#launcher>`_, which is a component that can be provided via plugins.
    This is where the Hydra Flyte Launcher comes in later, in order to launch your job with flyte.

Grouping config files (`official docs <https://hydra.cc/docs/1.1/tutorials/basic/your_first_app/config_groups/>`_)
------------------------------------------------------------------------------------------------------------------
This feature allows you to to split up your config into reusable sub configs and build up a **hierarchical config structure**.

Config groups are selected in your main config file using the `Defaults List <https://hydra.cc/docs/1.1/advanced/defaults_list/>`_ (See the top of :code:`/main_hydra_group.yaml`).
In the defaults list you can select whole configs in order to construct the final config you want.
Hydra configs are basically constructed from top to bottom, and every entry in the defaults list adds their content under the respective key.

Discovering the configs works much like python name spaces.
Since we added :code:`config_path="./conf"` to our hydra main call, hydra can by default find all configs in this directory.

.. code-block:: console
    :caption: folder structure

    ├── conf
    │   ├── main_hydra_group.yaml
    │   └── model
    │       └── model_conf.yaml
    ├── main_hydra_group.py

.. literalinclude:: /../test/docs_examples/snippets/conf/model/model_conf.yaml
    :caption: conf/model/model_conf.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_group.yaml
    :caption: conf/main_hydra_group.yaml
    :language: yaml

.. literalinclude:: /../test/docs_examples/snippets/main_hydra_group.py
    :caption: main_hydra_group.py
    :language: python
    

Looking at the config using :code:`python3 main_hydra_group.py --cfg job` should give you the same result:

.. code-block:: console

    model:
        learning_rate: 0.001
    experiment_name: training


.. tip::
    Putting configs into groups also allows you to pick and place the content of these configs multiple times at different locations.
    This is made possible through a hydra feature called `Packages <https://hydra.cc/docs/1.1/advanced/overriding_packages/>`_ and the :code:`group@package: group_option` syntax in the defaults list.

Selecting configs from other sources
----------------------------------------
Since the `Defaults List <https://hydra.cc/docs/1.1/advanced/defaults_list/>`_ is the mechanism to select an available config option in order to add it to your config tree, this mechanism is also used to **access configs you did not define yourself**.

This also allows you to pick configs that are provided via a `SearchPathPlugin <https://hydra.cc/docs/1.1/advanced/plugins/overview/#searchpathplugin>`_.
Hydra itself, as well as Scaffold and Chameleon implement such plugins in order to make configurations accessible in the defaults list without requiring you to copy paste yaml files.
The only requirement is that you have the respective python package installed in the same environment.

You can discover the available group options using :code:`python3 main_hydra_group.py --help`, which should show you something similar to this:

.. code-block:: console

    [...]
    == Configuration groups ==
    Compose your configuration from those groups (group=option)

    model: model_conf
    scaffold/artifact_manager: ArtifactManagerConf, WandbArtifactManagerConf, FileSystemArtifactManagerConf
    scaffold/entrypoint: EntrypointConf, hydra_defaults
    scaffold/entrypoint/callbacks: my_callbacks
    scaffold/entrypoint/logging: default, disabled, none, stdout
    scaffold/flyte_launcher: FlyteDockerImageConfig, FlyteWorkflowConfig
    [...]

Using this information, we can take any of those configs, and use them in our own config.
For illustrative purposed we can take the content of the default logging option and put it under a different key (or hydra package) in our config:

.. literalinclude:: /../test/docs_examples/snippets/conf/main_hydra_from_package.yaml
    :caption: conf/main_hydra_from_packages.yaml
    :language: yaml

Which should result in a rendered config like this

.. code-block:: yaml

    model:
        learning_rate: 0.001
    my_logging:
        version: 1
        formatters:
            simple:
            format: '[%(asctime)s][%(name)s][%(levelname)s] - %(message)s'
        handlers:
            # [...]
        root:
            # [...]
        disable_existing_loggers: false
    experiment_name: training

.. note::
    Taking a look at :code:`python3 main_hydra_group.py --hydra-help` will show you specific group options for configuring hydra.
    There you will also find the :code:`hydra/launcher: basic, flyte` options. The :code:`flyte` option is provided by the launcher plugin of scaffold and will come in use later.
