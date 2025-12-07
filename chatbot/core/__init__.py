"""Core modules for the Synthio chatbot."""

from chatbot.core.config import settings
from chatbot.core.database import DatabaseManager
from chatbot.core.models import (
    AgentState,
    GuardrailResult,
    QueryPlan,
    SQLResult,
    ValidationResult,
)
from chatbot.core.schema import get_database_schema
from chatbot.core.tracing import (
    TracingContext,
    generate_run_id,
    get_langsmith_client,
    get_trace_metadata,
    log_feedback,
    trace_agent,
    trace_llm_call,
    trace_workflow,
)

__all__ = [
    # Config
    "settings",
    # Database
    "DatabaseManager",
    # Models
    "AgentState",
    "GuardrailResult",
    "QueryPlan",
    "SQLResult",
    "ValidationResult",
    # Schema
    "get_database_schema",
    # Tracing
    "TracingContext",
    "generate_run_id",
    "get_langsmith_client",
    "get_trace_metadata",
    "log_feedback",
    "trace_agent",
    "trace_llm_call",
    "trace_workflow",
]
