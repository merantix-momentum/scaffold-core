"""Tests for Metric, register_metric, and _score_trace in scaffold.langfuse_utils.scoring."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_langfuse_mock():
    lf = MagicMock()
    return lf


def _langfuse_module_mock(instance):
    """Return a fake `langfuse` top-level module whose Langfuse() returns *instance*."""
    mod = MagicMock()
    mod.Langfuse.return_value = instance
    return mod


@pytest.fixture(autouse=True)
def isolate_scoring_module():
    lf_instance = _make_langfuse_mock()
    lf_mod = _langfuse_module_mock(lf_instance)

    # Remove cached modules so they re-import fresh with mocked langfuse
    sys.modules.pop("scaffold.langfuse_utils.scoring", None)
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)
    sys.modules.pop("scaffold.langfuse_utils", None)

    with patch.dict(sys.modules, {"langfuse": lf_mod}):
        yield

    # Clean up after the test
    sys.modules.pop("scaffold.langfuse_utils.scoring", None)
    sys.modules.pop("scaffold.langfuse_utils.tracing", None)
    sys.modules.pop("scaffold.langfuse_utils", None)


# ---------------------------------------------------------------------------
# register_metric
# ---------------------------------------------------------------------------


def test_register_metric_appends_entry():
    from scaffold.langfuse_utils.scoring import register_metric, _metric_registry, Metric

    scorer = MagicMock(return_value=0.5)
    metric = Metric(name="quality", scorer=scorer)
    register_metric(metric)

    assert len(_metric_registry) == 1
    m = _metric_registry[0]
    assert m.name == "quality"
    assert m.scorer is scorer
    assert m.data_type is None
    assert m.comment is None


def test_register_metric_multiple_accumulate():
    from scaffold.langfuse_utils.scoring import register_metric, _metric_registry, Metric

    register_metric(Metric(name="a", scorer=MagicMock(return_value=1.0)))
    register_metric(Metric(name="b", scorer=MagicMock(return_value=0.0)))

    assert len(_metric_registry) == 2
    assert _metric_registry[0].name == "a"
    assert _metric_registry[1].name == "b"


# ---------------------------------------------------------------------------
# _score_trace
# ---------------------------------------------------------------------------


def test_score_trace_calls_scorer_and_create_score():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"
    scorer = MagicMock(return_value=0.9)

    register_metric(Metric(name="quality", scorer=scorer))
    _score_trace(langfuse_mock, obs, "in", "out", metadata={"k": "v"})

    scorer.assert_called_once_with("in", "out", {"k": "v"})
    langfuse_mock.create_score.assert_called_once_with(
        trace_id="t1", name="quality", value=0.9
    )


def test_score_trace_includes_data_type_when_set():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    register_metric(
        Metric(
            name="flag",
            scorer=MagicMock(return_value=1.0),
            data_type="BOOLEAN",
        )
    )
    _score_trace(langfuse_mock, obs, "in", "out")

    kwargs = langfuse_mock.create_score.call_args.kwargs
    assert kwargs["data_type"] == "BOOLEAN"


def test_score_trace_omits_data_type_when_none():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    register_metric(Metric(name="q", scorer=MagicMock(return_value=0.5)))
    _score_trace(langfuse_mock, obs, "in", "out")

    kwargs = langfuse_mock.create_score.call_args.kwargs
    assert "data_type" not in kwargs


def test_score_trace_scorer_exception_does_not_propagate():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    register_metric(
        Metric(
            name="bad",
            scorer=MagicMock(side_effect=RuntimeError("scorer blew up")),
        )
    )
    _score_trace(langfuse_mock, obs, "in", "out")  # must not raise

    langfuse_mock.create_score.assert_not_called()


def test_score_trace_multiple_metrics_all_scored():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    register_metric(Metric(name="m1", scorer=MagicMock(return_value=0.1)))
    register_metric(Metric(name="m2", scorer=MagicMock(return_value=0.2)))
    _score_trace(langfuse_mock, obs, "in", "out")

    assert langfuse_mock.create_score.call_count == 2
    names = {c.kwargs["name"] for c in langfuse_mock.create_score.call_args_list}
    assert names == {"m1", "m2"}


def test_score_trace_one_bad_scorer_does_not_block_others():
    from scaffold.langfuse_utils.scoring import register_metric, _score_trace, Metric

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    register_metric(Metric(name="bad", scorer=MagicMock(side_effect=ValueError("wrong"))))
    register_metric(Metric(name="good", scorer=MagicMock(return_value=0.7)))
    _score_trace(langfuse_mock, obs, "in", "out")

    langfuse_mock.create_score.assert_called_once()
    assert langfuse_mock.create_score.call_args.kwargs["name"] == "good"


def test_score_trace_empty_registry_skips_create_score():
    from scaffold.langfuse_utils.scoring import _score_trace

    langfuse_mock = _make_langfuse_mock()
    obs = MagicMock()
    obs.trace_id = "t1"

    _score_trace(langfuse_mock, obs, "in", "out")

    langfuse_mock.create_score.assert_not_called()
