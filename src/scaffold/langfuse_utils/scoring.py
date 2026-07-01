"""
Langfuse scoring and metrics infrastructure.

Register custom metrics that will be automatically computed and submitted
to Langfuse after each trace completes.

Example:
    Define your metrics in a metrics.py file in your app:

    ```python
    from scaffold.langfuse_utils.scoring import register_metric

    def score_response_quality(input_text: str, output_text: str, metadata: dict | None) -> float:
        # Your scoring logic here
        return 0.8

    register_metric(
        name="response_quality",
        scorer=score_response_quality,
        data_type="NUMERIC",
        comment="Evaluates output quality based on input",
    )
    ```

    Then in your app startup (same place as init_langfuse):

    ```python
    from scaffold.langfuse_utils.tracing import init_langfuse
    from myapp.metrics import score_response_quality  # Import to trigger register_metric calls

    init_langfuse(
        secret_key=LANGFUSE_SECRET_KEY,
        public_key=LANGFUSE_PUBLIC_KEY,
        framework="openai",
    )
    ```
"""

import logging
from dataclasses import dataclass
from typing import Callable, Literal

logger = logging.getLogger(__name__)


@dataclass
class _Metric:
    name: str
    scorer: Callable[[str, str, dict | None], float | str]
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL", "TEXT"] | None = None
    comment: str | None = None


_metric_registry: list[_Metric] = []


def register_metric(
    name: str,
    scorer: Callable[[str, str, dict | None], float | str],
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL", "TEXT"] | None = None,
    comment: str | None = None,
) -> None:
    """Register a project-specific scoring metric.

    The scorer is called with (input_text, output_text, metadata) after each
    trace completes, and the returned value is submitted to Langfuse via
    create_score().

    Args:
        name: Score name visible in Langfuse (e.g. "response_quality").
        scorer: Callable(input_text, output_text, metadata) -> float | str.
            Return a float for NUMERIC/BOOLEAN scores, str for CATEGORICAL/TEXT.
        data_type: Langfuse data type. Auto-detected from value type when None.
            Use "BOOLEAN" explicitly (values 0.0 / 1.0) since booleans would
            otherwise be inferred as NUMERIC.
        comment: Optional static comment attached to every score entry.
    """
    _metric_registry.append(
        _Metric(name=name, scorer=scorer, data_type=data_type, comment=comment)
    )
    logger.info("Metric registered: %s", name)


def _score_trace(
        langfuse,
        obs,
        input_text: str,
        output_text: str,
        metadata: dict | None = None,
) -> None:
    """Submit all registered metrics for the current trace.

    Args:
        langfuse: The Langfuse client instance.
        obs: The current observation span.
        input_text: The input text for scoring context.
        output_text: The output text for scoring context.
        metadata: Optional metadata to pass to scorers.
    """
    for metric in _metric_registry:
        try:
            value = metric.scorer(input_text, output_text, metadata)
            kwargs: dict = {"trace_id": obs.trace_id, "name": metric.name, "value": value}
            if metric.data_type is not None:
                kwargs["data_type"] = metric.data_type
            if metric.comment is not None:
                kwargs["comment"] = metric.comment
            langfuse.create_score(**kwargs)
        except Exception:
            logger.exception("Metric scorer %r raised an error", metric.name)
