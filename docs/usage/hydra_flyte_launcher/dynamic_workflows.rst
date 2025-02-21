Dynamic Workflows
====================

In some cases it might make sense to turn your :code:`workflow` into a `dynamic workflow <https://docs.flyte.org/en/latest/user_guide/advanced_composition/dynamic_workflows.html#dynamic-workflow>`_ in order to
have very flexible control flow.

.. note::
    In most cases you should try to solve your problem with a static workflow, which gives you more robust error handling, since dynamic workflows only fail at runtime.
    In case you want to call the same function many times with different configuration values, a `map task <https://docs.flyte.org/en/latest/user_guide/advanced_composition/map_tasks.html>`_ might be the way to go.

Dynamic workflows are "black boxes" to flyte. They act like workflows at compile time (packaging a number of tasks) but run like tasks, so they can execute any python code.
Importantly, they hide the nodes that make up the execution graph from our flyte launcher. As a consequence subtasks of dynamic workflows are not
explicitly registered, making them unavailable for caching.

This can be resolved by declaring subnodes explicitly (using the below decorator), so the flyte launcher can discover them and register them with the Flyte backend.

.. literalinclude:: /../test/docs_examples/snippets/main_hydra_flyte_dynamic.py
    :caption: main_hydra_flyte_dynamic.py
    :language: python
