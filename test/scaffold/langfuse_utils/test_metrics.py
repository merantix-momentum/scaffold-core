"""Tests for register_metric and _score_trace in scaffold.langfuse_utils.tracing."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_KEYS = dict(secret_key="sk-test", public_key="pk-test", host="https://example.com")


def _make_langfuse_mock():
    obs = MagicMock()
    obs.trace_id = "trace-123"
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=obs)
    cm.__exit__ = MagicMock(return_value=False)
    lf = MagicMock()
    lf.start_as_current_observation.return_value = cm
    return lf


def _langfuse_module_mock(instance):
    mod = MagicMock()
    mod.Langfuse.return_value = instance
    return mod


@pytest.fixture(autouse=True)
def isolate_tracing_module():
    lf_instance = _make_langfuse_mock()
    lf_mod = _langfuse_module_mock(lf_instance)
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)
    with patch.dict(sys.modules, {"langfuse": lf_mod}):
        yield lf_instance
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)


# ---------------------------------------------------------------------------
# register_metric
# ---------------------------------------------------------------------------


def test_register_metric_appends_entry():
    import scaffold.langfuse_utils.tracing as tracing

    scorer = MagicMock(return_value=0.5)
    tracing.register_metric("quality", scorer)

    assert len(tracing._metric_registry) == 1
    m = tracing._metric_registry[0]
    assert m.name == "quality"
    assert m.scorer is scorer
    assert m.data_type is None
    assert m.comment is None


def test_register_metric_multiple_accumulate():
    import scaffold.langfuse_utils.tracing as tracing

    tracing.register_metric(name="a", scorer=MagicMock(return_value=1.0))
    tracing.register_metric(name="b", scorer=MagicMock(return_value=0.0))

    assert len(tracing._metric_registry) == 2
    assert tracing._metric_registry[0].name == "a"
    assert tracing._metric_registry[1].name == "b"


# ---------------------------------------------------------------------------
# _score_trace
# ---------------------------------------------------------------------------


def test_score_trace_calls_scorer_and_create_score(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"
    scorer = MagicMock(return_value=0.9)

    tracing.register_metric(name="quality", scorer=scorer)
    tracing._score_trace(obs, "in", "out", metadata={"k": "v"})

    scorer.assert_called_once_with("in", "out", {"k": "v"})
    isolate_tracing_module.create_score.assert_called_once_with(
        trace_id="t1", name="quality", value=0.9
    )


def test_score_trace_includes_data_type_when_set(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing.register_metric(
        name="flag",
        scorer=MagicMock(return_value=1.0),
        data_type="BOOLEAN",
    )
    tracing._score_trace(obs, "in", "out")

    kwargs = isolate_tracing_module.create_score.call_args.kwargs
    assert kwargs["data_type"] == "BOOLEAN"


def test_score_trace_omits_data_type_when_none(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing.register_metric(name="q", scorer=MagicMock(return_value=0.5))
    tracing._score_trace(obs, "in", "out")

    kwargs = isolate_tracing_module.create_score.call_args.kwargs
    assert "data_type" not in kwargs


def test_score_trace_scorer_exception_does_not_propagate(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing.register_metric(
        name="bad",
        scorer=MagicMock(side_effect=RuntimeError("scorer blew up")),
    )
    tracing._score_trace(obs, "in", "out")  # must not raise

    isolate_tracing_module.create_score.assert_not_called()


def test_score_trace_multiple_metrics_all_scored(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing.register_metric(name="m1", scorer=MagicMock(return_value=0.1))
    tracing.register_metric(name="m2", scorer=MagicMock(return_value=0.2))
    tracing._score_trace(obs, "in", "out")

    assert isolate_tracing_module.create_score.call_count == 2
    names = {c.kwargs["name"] for c in isolate_tracing_module.create_score.call_args_list}
    assert names == {"m1", "m2"}


def test_score_trace_one_bad_scorer_does_not_block_others(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing.register_metric("bad", scorer=MagicMock(side_effect=ValueError("wrong")))
    tracing.register_metric("good", scorer=MagicMock(return_value=0.7))
    tracing._score_trace(obs, "in", "out")

    isolate_tracing_module.create_score.assert_called_once()
    assert isolate_tracing_module.create_score.call_args.kwargs["name"] == "good"


def test_score_trace_empty_registry_skips_create_score(isolate_tracing_module):
    import scaffold.langfuse_utils.tracing as tracing

    tracing.langfuse = isolate_tracing_module
    obs = MagicMock()
    obs.trace_id = "t1"

    tracing._score_trace(obs, "in", "out")

    isolate_tracing_module.create_score.assert_not_called()
