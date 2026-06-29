.. _langfuse_utils:

Langfuse Utils
==============

This package provides a drop-in Langfuse tracing setup for LLM applications.
Call :code:`init_langfuse()` once at application startup — before importing any LLM framework — to initialise the Langfuse OTEL exporter and instrument the chosen framework.

Usage
-----

.. code-block:: python

    from scaffold.langfuse_utils.tracing import init_langfuse

    init_langfuse(
        secret_key=LANGFUSE_SECRET_KEY,
        public_key=LANGFUSE_PUBLIC_KEY,
        host=LANGFUSE_BASE_URL,      # defaults to https://cloud.langfuse.com
        framework=TRACING_FRAMEWORK, # defaults to "openai"
    )

Supported frameworks
--------------------

+-------------------+------------------------------------------------+
| ``framework``     | What gets instrumented                         |
+===================+================================================+
| ``openai``        | OpenAI SDK — ``chat.completions.create``       |
+-------------------+------------------------------------------------+
| ``openai_agents`` | OpenAI Agents SDK — ``Runner.run``             |
+-------------------+------------------------------------------------+
| ``langgraph``     | LangChain / LangGraph — ``Pregel.invoke``      |
+-------------------+------------------------------------------------+
| ``gemini``        | Google Gemini ADK — ``Runner.run_async``       |
+-------------------+------------------------------------------------+

.. note::
    Each framework's dependencies are imported lazily, so only the package for
    the framework you select needs to be installed locally in your project.

Running the tests
-----------------

The tests for this module are located in ``test/scaffold/langfuse_utils/``.
Run them with the ``--noconftest`` flag to avoid loading the root ``conftest.py``,
which requires ``pynvml`` (a GPU monitoring library not needed by these tests):

.. code-block:: bash

    uv run pytest test/scaffold/langfuse_utils/ -v --noconftest
