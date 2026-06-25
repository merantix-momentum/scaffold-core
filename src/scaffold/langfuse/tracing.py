"""
Drop-in Langfuse tracing script — call init_langfuse() to set up basic Langfuse tracing for your application.
Usage:

```python
from scaffold.langfuse.tracing import init_langfuse
init_langfuse(
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    host=os.environ["LANGFUSE_BASE_URL"],
    framework=os.environ["TRACING_FRAMEWORK"],
)
```
Note: You need to call init_langfuse() at the top of your application entrypoint even before importing any LLM frameworks.
Supported frameworks:
  openai          — OpenAI SDK direct (chat.completions), default
  openai_agents   — OpenAI Agents SDK
  langgraph       — LangChain / LangGraph
  gemini          — Google Gemini (ADK)
"""

import atexit
import logging

from langfuse import Langfuse

logger = logging.getLogger(__name__)

_VALID_FRAMEWORKS = {"openai", "openai_agents", "langgraph", "gemini"}


def init_langfuse(
    secret_key: str,
    public_key: str,
    host: str = "https://cloud.langfuse.com",
    framework: str = "openai",
) -> None:
    """Initialise Langfuse tracing for the given framework.

    Call this once at application startup, before any LLM imports.
    It sets up the Langfuse OTEL exporter, activates the framework-specific
    instrumentor, and wraps the framework's run entrypoint so that the
    Langfuse trace preview shows plain-text input/output instead of raw JSON.

    Args:
        secret_key: Langfuse project secret key (sk-...).
        public_key: Langfuse project public key (pk-...).
        host: Langfuse host URL. Defaults to https://cloud.langfuse.com.
        framework: Framework to instrument. One of: "openai", "openai_agents",
            "gemini". Defaults to "openai".

    Raises:
        ValueError: If `framework` is not one of the supported values.

    Example:
        >>> from tracing import init_langfuse
        >>> init_langfuse(
        ...     secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        ...     public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        ...     framework="openai_agents",
        ... )
    """
    global langfuse

    if framework not in _VALID_FRAMEWORKS:
        raise ValueError(
            f"framework={framework!r} is not recognised. "
            f"Valid options: {', '.join(sorted(_VALID_FRAMEWORKS))}"
        )

    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )
    logger.info(
        "Langfuse tracing initialised | host=%s framework=%s public_key=%s...",
        host,
        framework,
        public_key[:6],
    )

    prev_framework = getattr(init_langfuse, "_patched_framework", None)
    if prev_framework is None:
        setattr(init_langfuse, "_patched_framework", framework)
    elif prev_framework != framework:
        raise RuntimeError(
            f"init_langfuse() was already called for framework={prev_framework!r}; "
            f"cannot re-initialize with framework={framework!r}"
        )
    else:
        logger.debug(
            "Langfuse tracing already patched for framework=%s; skipping patching.",
            framework,
        )
        return

    if framework == "openai_agents":
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
        OpenAIAgentsInstrumentor().instrument()

        from agents import Runner as _Runner
        _orig_runner_run = _Runner.run

        async def _patched_runner_run(*args, **kwargs):
            input_val = kwargs.get("input", "")
            input_text = input_val if isinstance(input_val, str) else str(input_val)
            with langfuse.start_as_current_observation(name="trace-top", as_type="span") as obs:
                obs.update(input=input_text)
                result = await _orig_runner_run(*args, **kwargs)
                obs.update(output=result.final_output)
            return result

        _Runner.run = _patched_runner_run

    elif framework == "langgraph":
        from openinference.instrumentation.langchain import LangChainInstrumentor
        LangChainInstrumentor().instrument()

        from langgraph.pregel import Pregel as _Pregel

        def _graph_input_text(input_data) -> str:
            if isinstance(input_data, dict):
                for msg in reversed(input_data.get("messages", [])):
                    if hasattr(msg, "type") and msg.type in ("human", "user"):
                        return msg.content if isinstance(msg.content, str) else str(msg.content)
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        return msg.get("content", "")
            return str(input_data)

        def _graph_output_text(result) -> str:
            if isinstance(result, dict):
                msgs = result.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    return last.content if hasattr(last, "content") else str(last)
            return str(result)

        _orig_invoke = _Pregel.invoke
        _orig_ainvoke = _Pregel.ainvoke

        def _patched_invoke(self, input, config=None, **kwargs):
            with langfuse.start_as_current_observation(name="trace-top", as_type="span") as obs:
                obs.update(input=_graph_input_text(input))
                result = _orig_invoke(self, input, config, **kwargs)
                obs.update(output=_graph_output_text(result))
            return result

        async def _patched_ainvoke(self, input, config=None, **kwargs):
            with langfuse.start_as_current_observation(name="trace-top", as_type="span") as obs:
                obs.update(input=_graph_input_text(input))
                result = await _orig_ainvoke(self, input, config, **kwargs)
                obs.update(output=_graph_output_text(result))
            return result

        _Pregel.invoke = _patched_invoke
        _Pregel.ainvoke = _patched_ainvoke

    elif framework == "gemini":
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        GoogleGenAIInstrumentor().instrument()

        from google.adk.runners import Runner as _Runner
        _orig_run_async = _Runner.run_async

        async def _patched_run_async(self, *, user_id, session_id, new_message, **kwargs):
            input_text = ""
            if hasattr(new_message, "parts"):
                for part in new_message.parts:
                    if hasattr(part, "text") and part.text:
                        input_text = part.text
                        break

            # Buffer all events inside the observation context so that child spans
            # from GoogleGenAIInstrumentor are created while our span is active (and
            # therefore parented to it). Yielding outside the `with` block avoids the
            # async-generator context-loss problem where each __anext__() call resets
            # the contextvar to the caller's context.
            events = []
            response_parts = []
            with langfuse.start_as_current_observation(name="trace-top", as_type="span") as obs:
                obs.update(input=input_text)
                async for event in _orig_run_async(
                    self,
                    user_id=user_id,
                    session_id=session_id,
                    new_message=new_message,
                    **kwargs,
                ):
                    events.append(event)
                    if (
                        event.is_final_response()
                        and event.content
                        and event.content.parts
                    ):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_parts.append(part.text)
                obs.update(output="\n".join(response_parts))

            for event in events:
                yield event

        _Runner.run_async = _patched_run_async
        atexit.register(langfuse.flush)

    else:  # openai — OpenAI SDK direct, chat.completions
        from openinference.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()

        import openai as _openai

        def _get_last_user_message(messages: list) -> str:
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    content = msg.get("content", "")
                    return content if isinstance(content, str) else str(content)
            return ""

        def _get_assistant_output(response) -> str:
            if not hasattr(response, "choices") or not response.choices:
                return ""
            message = response.choices[0].message
            if message.content:
                return message.content
            if hasattr(message, "tool_calls") and message.tool_calls:
                names = [tc.function.name for tc in message.tool_calls]
                return f"[tool_calls: {', '.join(names)}]"
            return ""

        _orig_create = _openai.resources.chat.completions.Completions.create

        def _patched_create(self, *args, **kwargs):
            input_text = _get_last_user_message(kwargs.get("messages", []))
            with langfuse.start_as_current_observation(name="trace-top", as_type="span") as obs:
                obs.update(input=input_text)
                result = _orig_create(self, *args, **kwargs)
                obs.update(output=_get_assistant_output(result))
            return result

        _openai.resources.chat.completions.Completions.create = _patched_create
