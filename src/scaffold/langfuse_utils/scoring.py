"""
Langfuse scoring and metrics infrastructure.

Register custom metrics that will be automatically computed and submitted
to Langfuse after each trace completes.

Example:
    Define your metrics in a metrics.py file in your app:

    ```python
    from langfuse_utils.scoring import Metric

    def score_response_quality(input_text: str, output_text: str, metadata: dict | None) -> float:
        # Your scoring logic here
        return 0.8

    RESPONSE_QUALITY = Metric(
        name="response_quality",
        scorer=score_response_quality,
        data_type="NUMERIC",
        comment="Evaluates output quality based on input",
    )
    ```

    Then in your app startup (same place as init_langfuse):

    ```python
    from langfuse_utils.tracing import init_langfuse
    from myapp.metrics import RESPONSE_QUALITY
    from langfuse_utils.scoring import register_metric

    init_langfuse(
        secret_key=LANGFUSE_SECRET_KEY,
        public_key=LANGFUSE_PUBLIC_KEY,
        framework="openai",
    )
    register_metric(RESPONSE_QUALITY)
    ```
"""

import logging
from dataclasses import dataclass
from typing import Callable, Literal

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """A scoring metric to be computed and submitted to Langfuse after each trace."""
    name: str
    scorer: Callable[[str, str, dict | None], float | str]
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL", "TEXT"] | None = None
    comment: str | None = None


_metric_registry: list[Metric] = []


def register_metric(metric: Metric) -> None:
    """Register a metric to be computed on every trace.

    Args:
        metric: A Metric object containing name, scorer, data_type, and comment.
    """
    _metric_registry.append(metric)
    logger.info("Metric registered: %s", metric.name)


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
