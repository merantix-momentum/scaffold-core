import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_KEYS = dict(secret_key="sk-test", public_key="pk-test", host="https://example.com")


def _make_langfuse_mock():
    """Return a mock Langfuse instance with a working context-manager observation."""
    obs = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=obs)
    cm.__exit__ = MagicMock(return_value=False)
    lf = MagicMock()
    lf.start_as_current_observation.return_value = cm
    return lf


def _langfuse_module_mock(instance):
    """Return a fake `langfuse` top-level module whose Langfuse() returns *instance*."""
    mod = MagicMock()
    mod.Langfuse.return_value = instance
    return mod


@pytest.fixture(autouse=True)
def isolate_tracing_module():
    """
    Each test gets a freshly imported tracing module with langfuse mocked out,
    so no test leaks _patched_framework state into the next.
    """
    lf_instance = _make_langfuse_mock()
    lf_mod = _langfuse_module_mock(lf_instance)

    # Remove any cached version of the module so importlib re-executes it.
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)

    with patch.dict(sys.modules, {"langfuse": lf_mod}):
        yield lf_instance

    # Clean up after the test.
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_unknown_framework_raises():
    from scaffold.langfuse_utils.tracing import init_langfuse

    with pytest.raises(ValueError, match="not recognised"):
        init_langfuse(**FAKE_KEYS, framework="unknown_framework")


def test_reinit_different_framework_raises():
    openai_mod = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "openinference.instrumentation.openai": MagicMock(OpenAIInstrumentor=MagicMock()),
            "openai": openai_mod,
            "openai.resources": openai_mod.resources,
            "openai.resources.chat": openai_mod.resources.chat,
            "openai.resources.chat.completions": openai_mod.resources.chat.completions,
        },
    ):
        from scaffold.langfuse_utils.tracing import init_langfuse

        init_langfuse(**FAKE_KEYS, framework="openai")

        with pytest.raises(RuntimeError, match="already called"):
            init_langfuse(**FAKE_KEYS, framework="langgraph")


# ---------------------------------------------------------------------------
# Missing dependency — logs error and returns without raising
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "framework,missing_module",
    [
        ("openai", "openai"),
        ("openai_agents", "agents"),
        ("langgraph", "langgraph"),
        ("gemini", "google"),
    ],
)
def test_missing_dependency_raises(framework, missing_module):
    instrumentor_mocks = {
        "openinference.instrumentation.openai": MagicMock(OpenAIInstrumentor=MagicMock()),
        "openinference.instrumentation.openai_agents": MagicMock(OpenAIAgentsInstrumentor=MagicMock()),
        "openinference.instrumentation.langchain": MagicMock(LangChainInstrumentor=MagicMock()),
        "openinference.instrumentation.google_genai": MagicMock(GoogleGenAIInstrumentor=MagicMock()),
    }

    with patch.dict(sys.modules, {**instrumentor_mocks, missing_module: None}):
        from scaffold.langfuse_utils.tracing import init_langfuse

        with pytest.raises(ImportError, match="install"):
            init_langfuse(**FAKE_KEYS, framework=framework)


def test_missing_dependency_resets_patched_framework():
    """After a failed init, _patched_framework is cleared so a retry is possible."""
    instrumentor_mocks = {
        "openinference.instrumentation.openai": MagicMock(OpenAIInstrumentor=MagicMock()),
    }
    with patch.dict(sys.modules, {**instrumentor_mocks, "openai": None}):
        import scaffold.langfuse_utils.tracing as tracing

        with pytest.raises(ImportError):
            tracing.init_langfuse(**FAKE_KEYS, framework="openai")
        assert not hasattr(tracing.init_langfuse, "_patched_framework")


# ---------------------------------------------------------------------------
# Idempotency — second call with the same framework is a no-op
# ---------------------------------------------------------------------------


def test_same_framework_twice_does_not_repatch():
    openai_instrumentor_cls = MagicMock()
    openai_mod = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "openinference.instrumentation.openai": MagicMock(OpenAIInstrumentor=openai_instrumentor_cls),
            "openai": openai_mod,
            "openai.resources": openai_mod.resources,
            "openai.resources.chat": openai_mod.resources.chat,
            "openai.resources.chat.completions": openai_mod.resources.chat.completions,
        },
    ):
        from scaffold.langfuse_utils.tracing import init_langfuse

        init_langfuse(**FAKE_KEYS, framework="openai")
        init_langfuse(**FAKE_KEYS, framework="openai")

    assert openai_instrumentor_cls.call_count == 1


# ---------------------------------------------------------------------------
# Monkey-patching correctness
# ---------------------------------------------------------------------------


def test_openai_create_is_patched():
    openai_mod = MagicMock()
    original_create = MagicMock()
    openai_mod.resources.chat.completions.Completions.create = original_create

    with patch.dict(
        sys.modules,
        {
            "openinference.instrumentation.openai": MagicMock(OpenAIInstrumentor=MagicMock()),
            "openai": openai_mod,
            "openai.resources": openai_mod.resources,
            "openai.resources.chat": openai_mod.resources.chat,
            "openai.resources.chat.completions": openai_mod.resources.chat.completions,
        },
    ):
        from scaffold.langfuse_utils.tracing import init_langfuse

        init_langfuse(**FAKE_KEYS, framework="openai")

    assert openai_mod.resources.chat.completions.Completions.create is not original_create


def test_openai_agents_runner_is_patched():
    agents_mod = MagicMock()
    original_run = MagicMock()
    agents_mod.Runner.run = original_run

    with patch.dict(
        sys.modules,
        {
            "openinference.instrumentation.openai_agents": MagicMock(OpenAIAgentsInstrumentor=MagicMock()),
            "agents": agents_mod,
        },
    ):
        from scaffold.langfuse_utils.tracing import init_langfuse

        init_langfuse(**FAKE_KEYS, framework="openai_agents")

    assert agents_mod.Runner.run is not original_run


def test_langgraph_pregel_is_patched():
    langgraph_pregel_mod = MagicMock()
    original_invoke = MagicMock()
    original_ainvoke = MagicMock()
    langgraph_pregel_mod.Pregel.invoke = original_invoke
    langgraph_pregel_mod.Pregel.ainvoke = original_ainvoke

    with patch.dict(
        sys.modules,
        {
            "openinference.instrumentation.langchain": MagicMock(LangChainInstrumentor=MagicMock()),
            "langgraph": MagicMock(),
            "langgraph.pregel": langgraph_pregel_mod,
        },
    ):
        from scaffold.langfuse_utils.tracing import init_langfuse

        init_langfuse(**FAKE_KEYS, framework="langgraph")

    assert langgraph_pregel_mod.Pregel.invoke is not original_invoke
    assert langgraph_pregel_mod.Pregel.ainvoke is not original_ainvoke
