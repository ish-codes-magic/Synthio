"""LangSmith tracing utilities for production observability."""

import functools
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Generator

from chatbot.core.config import settings

# Conditionally import langsmith
try:
    from langsmith import Client, traceable
    from langsmith.run_helpers import get_current_run_tree

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = None
    Client = None


def get_langsmith_client() -> Any | None:
    """
    Get a LangSmith client instance if tracing is enabled.

    Returns:
        LangSmith Client or None if not available/enabled
    """
    if not LANGSMITH_AVAILABLE or not settings.langsmith_tracing:
        return None

    return Client(
        api_key=settings.langsmith_api_key,
        api_url=settings.langsmith_endpoint,
    )


def get_trace_metadata() -> dict[str, Any]:
    """
    Get standard metadata to attach to all traces.

    Returns:
        Dictionary of metadata fields
    """
    return {
        "environment": settings.environment,
        "app_version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "timestamp": datetime.utcnow().isoformat(),
    }


def generate_run_id() -> str:
    """Generate a unique run ID for trace correlation."""
    return str(uuid.uuid4())


@contextmanager
def trace_session(
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager for a tracing session.

    Usage:
        with trace_session(user_id="user123") as session:
            # All traces within this block share the session context
            result = await workflow.execute(query)

    Args:
        session_id: Optional session ID (generated if not provided)
        user_id: Optional user identifier
        metadata: Additional metadata to attach

    Yields:
        Session context dictionary
    """
    session_context = {
        "session_id": session_id or generate_run_id(),
        "user_id": user_id,
        **get_trace_metadata(),
        **(metadata or {}),
    }

    yield session_context


def trace_agent(
    agent_name: str,
    run_type: str = "chain",
) -> Callable:
    """
    Decorator to trace agent execution with proper metadata.

    Usage:
        @trace_agent("PlannerAgent")
        async def execute(self, state):
            ...

    Args:
        agent_name: Name of the agent for the trace
        run_type: Type of run (chain, llm, tool, etc.)

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        if not LANGSMITH_AVAILABLE or not settings.langsmith_tracing:
            return func

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create traced version with metadata
            traced_func = traceable(
                name=agent_name,
                run_type=run_type,
                metadata=get_trace_metadata(),
                tags=[
                    f"agent:{agent_name}",
                    f"env:{settings.environment}",
                ],
            )(func)
            return await traced_func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            traced_func = traceable(
                name=agent_name,
                run_type=run_type,
                metadata=get_trace_metadata(),
                tags=[
                    f"agent:{agent_name}",
                    f"env:{settings.environment}",
                ],
            )(func)
            return traced_func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def trace_workflow(
    workflow_name: str = "SynthioWorkflow",
) -> Callable:
    """
    Decorator to trace the entire workflow execution.

    Usage:
        @trace_workflow()
        async def execute(self, user_query: str):
            ...

    Args:
        workflow_name: Name for the workflow trace

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        if not LANGSMITH_AVAILABLE or not settings.langsmith_tracing:
            return func

        @functools.wraps(func)
        async def wrapper(self, user_query: str, *args, **kwargs):
            run_id = generate_run_id()

            # Create traced version with full context
            traced_func = traceable(
                name=workflow_name,
                run_type="chain",
                metadata={
                    **get_trace_metadata(),
                    "run_id": run_id,
                    "user_query": user_query[:500],  # Truncate for metadata
                },
                tags=[
                    f"workflow:{workflow_name}",
                    f"env:{settings.environment}",
                    f"provider:{settings.llm_provider}",
                ],
            )(func)

            result = await traced_func(self, user_query, *args, **kwargs)

            # Add run_id to result for correlation
            if isinstance(result, dict):
                result["trace_run_id"] = run_id

            return result

        return wrapper

    return decorator


def trace_llm_call(
    call_name: str = "LLM Call",
) -> Callable:
    """
    Decorator to trace individual LLM calls.

    Usage:
        @trace_llm_call("Planner LLM")
        async def invoke_llm(self, system_prompt, user_prompt):
            ...

    Args:
        call_name: Name for this LLM call

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        if not LANGSMITH_AVAILABLE or not settings.langsmith_tracing:
            return func

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            traced_func = traceable(
                name=call_name,
                run_type="llm",
                metadata={
                    "model": settings.llm_model,
                    "provider": settings.llm_provider,
                    "temperature": settings.llm_temperature,
                },
            )(func)
            return await traced_func(*args, **kwargs)

        return wrapper

    return decorator


def log_feedback(
    run_id: str,
    score: float,
    feedback_type: str = "user_rating",
    comment: str | None = None,
) -> bool:
    """
    Log user feedback to LangSmith for a specific run.

    Args:
        run_id: The run ID to attach feedback to
        score: Feedback score (0.0 to 1.0)
        feedback_type: Type of feedback (user_rating, correctness, etc.)
        comment: Optional text comment

    Returns:
        True if feedback was logged successfully
    """
    if not LANGSMITH_AVAILABLE or not settings.langsmith_tracing:
        return False

    try:
        client = get_langsmith_client()
        if client:
            client.create_feedback(
                run_id=run_id,
                key=feedback_type,
                score=score,
                comment=comment,
            )
            return True
    except Exception as e:
        print(f"Failed to log feedback: {e}")

    return False


def asyncio_iscoroutinefunction(func: Callable) -> bool:
    """Check if function is a coroutine function."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


class TracingContext:
    """
    Context class for managing trace state across a request.

    Usage:
        ctx = TracingContext(user_query="...", user_id="...")
        async with ctx:
            result = await workflow.execute(query)
            ctx.add_metadata("sql_query", result.get("sql_query"))
    """

    def __init__(
        self,
        user_query: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ):
        self.user_query = user_query
        self.user_id = user_id
        self.session_id = session_id or generate_run_id()
        self.run_id = generate_run_id()
        self.metadata: dict[str, Any] = {}
        self.start_time = datetime.utcnow()

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the current trace context."""
        self.metadata[key] = value

    def get_context(self) -> dict[str, Any]:
        """Get the full trace context."""
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_query": self.user_query[:500],
            "start_time": self.start_time.isoformat(),
            **get_trace_metadata(),
            **self.metadata,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Log completion metadata
        self.metadata["duration_seconds"] = (
            datetime.utcnow() - self.start_time
        ).total_seconds()
        self.metadata["success"] = exc_type is None

        if exc_type:
            self.metadata["error_type"] = exc_type.__name__
            self.metadata["error_message"] = str(exc_val)

