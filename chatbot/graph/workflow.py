"""LangGraph workflow definition for the Synthio chatbot."""

import uuid
from datetime import datetime
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chatbot.agents import (
    GuardrailAgent,
    PlannerAgent,
    SQLGeneratorAgent,
    ValidatorAgent,
    WriterAgent,
)
from chatbot.core.config import settings
from chatbot.core.database import DatabaseManager
from chatbot.core.models import AgentState
from chatbot.core.schema import get_database_schema
from chatbot.core.tracing import TracingContext, get_trace_metadata
from chatbot.graph.nodes import (
    create_guardrail_node,
    create_planner_node,
    create_sql_generator_node,
    create_validator_node,
    create_writer_node,
)


class SynthioWorkflow:
    """
    Main workflow orchestrator for the Synthio chatbot.

    This class encapsulates the LangGraph workflow and provides
    a clean interface for executing queries.

    Workflow:
    1. Guardrail: Check if query is relevant and safe
       - If BLOCKED: Return friendly rejection message
       - If ALLOWED: Continue to Planner
    2. Planner: Create natural language instructions
    3. SQL Generator: Generate and execute SQL
    4. Validator: Check results (retry if needed)
    5. Writer: Generate final response

    All steps are traced with LangSmith when enabled.
    """

    def __init__(
        self,
        llm_client: Any,
        db_path: str = "synthio.db",
    ):
        """
        Initialize the workflow with all agents.

        Args:
            llm_client: LangChain LLM client instance
            db_path: Path to the SQLite database
        """
        self.llm = llm_client
        self.db_manager = DatabaseManager(db_path)

        # Initialize agents
        self.guardrail = GuardrailAgent(llm_client)
        self.planner = PlannerAgent(llm_client)
        self.sql_generator = SQLGeneratorAgent(llm_client, self.db_manager)
        self.validator = ValidatorAgent(llm_client)
        self.writer = WriterAgent(llm_client)

        # Pre-compute schema context
        self.schema_context = get_database_schema(self.db_manager, include_samples=True)

        # Build the workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> CompiledStateGraph:
        """
        Build the LangGraph workflow with all nodes and edges.

        Returns:
            Compiled StateGraph workflow
        """
        # Create the state graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("guardrail", create_guardrail_node(self.guardrail))
        workflow.add_node("blocked_response", self._create_blocked_response)
        workflow.add_node("planner", create_planner_node(self.planner))
        workflow.add_node("sql_generator", create_sql_generator_node(self.sql_generator))
        workflow.add_node("validator", create_validator_node(self.validator))
        workflow.add_node("writer", create_writer_node(self.writer))

        # Define edges - start with guardrail
        workflow.set_entry_point("guardrail")

        # Conditional edge after guardrail: proceed or block
        workflow.add_conditional_edges(
            "guardrail",
            self._check_guardrail,
            {
                "proceed": "planner",
                "block": "blocked_response",
            }
        )

        # Blocked response goes to END
        workflow.add_edge("blocked_response", END)

        # Normal flow continues
        workflow.add_edge("planner", "sql_generator")
        workflow.add_edge("sql_generator", "validator")

        # Conditional edge: retry or proceed to writer
        workflow.add_conditional_edges(
            "validator",
            self._should_retry,
            {
                "retry": "sql_generator",
                "proceed": "writer",
            }
        )

        workflow.add_edge("writer", END)

        # Compile the workflow
        return workflow.compile()

    def _check_guardrail(self, state: AgentState) -> Literal["proceed", "block"]:
        """
        Check if the query passed the guardrail.

        Args:
            state: Current workflow state

        Returns:
            "proceed" if allowed, "block" if rejected
        """
        if state.get("guardrail_passed", False):
            return "proceed"
        return "block"

    async def _create_blocked_response(self, state: AgentState) -> dict[str, Any]:
        """
        Create a response for blocked queries.

        Args:
            state: Current workflow state

        Returns:
            State update with final_response set to the block message
        """
        guardrail_result = state.get("guardrail_result", {})
        user_response = guardrail_result.get(
            "user_response",
            "I'm designed to help with pharmaceutical sales data analysis. "
            "Please ask a question about prescriptions, doctors, territories, "
            "or sales activities."
        )

        return {
            "final_response": user_response,
            "sql_query": "",  # No SQL for blocked queries
        }

    def _should_retry(self, state: AgentState) -> Literal["retry", "proceed"]:
        """
        Determine whether to retry SQL generation.

        Args:
            state: Current workflow state

        Returns:
            "retry" or "proceed"
        """
        should_retry = state.get("should_retry", False)
        retry_count = state.get("retry_count", 0)
        max_retries = settings.max_retries

        if should_retry and retry_count < max_retries:
            return "retry"

        return "proceed"

    async def execute(
        self,
        user_query: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute the workflow for a user query with full tracing.

        Args:
            user_query: The user's natural language question
            session_id: Optional session ID for trace correlation
            user_id: Optional user ID for trace attribution

        Returns:
            Final workflow state with the response and trace metadata
        """
        # Generate trace identifiers
        run_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Build trace metadata
        trace_metadata = {
            **get_trace_metadata(),
            "run_id": run_id,
            "session_id": session_id,
            "user_id": user_id,
            "user_query_length": len(user_query),
        }

        # Initialize state with trace context
        initial_state: AgentState = {
            "user_query": user_query,
            "schema_context": self.schema_context,
            "retry_count": 0,
            "should_retry": False,
            "guardrail_passed": False,
            "messages": [],
        }

        try:
            # Execute the workflow
            # LangGraph automatically traces when LANGCHAIN_TRACING_V2=true
            final_state = await self.workflow.ainvoke(
                initial_state,
                config={
                    "metadata": trace_metadata,
                    "tags": [
                        f"env:{settings.environment}",
                        f"provider:{settings.llm_provider}",
                        "workflow:synthio",
                    ],
                    "run_name": f"Synthio Query: {user_query[:50]}...",
                },
            )

            result = dict(final_state)

            # Add trace metadata to result
            result["trace_metadata"] = {
                "run_id": run_id,
                "session_id": session_id,
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "success": True,
                "guardrail_passed": result.get("guardrail_passed", False),
            }

            return result

        except Exception as e:
            # Log error in trace metadata
            return {
                "final_response": f"An error occurred: {str(e)}",
                "sql_query": "",
                "guardrail_passed": False,
                "trace_metadata": {
                    "run_id": run_id,
                    "session_id": session_id,
                    "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            }

    def execute_sync(
        self,
        user_query: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Synchronous wrapper for execute().

        Args:
            user_query: The user's natural language question
            session_id: Optional session ID for trace correlation
            user_id: Optional user ID for trace attribution

        Returns:
            Final workflow state with the response
        """
        import asyncio

        return asyncio.run(self.execute(user_query, session_id, user_id))


def create_workflow(
    llm_client: Any | None = None,
    db_path: str = "synthio.db",
) -> SynthioWorkflow:
    """
    Factory function to create a configured workflow.

    Args:
        llm_client: Optional LLM client (created from settings if not provided)
        db_path: Path to the SQLite database

    Returns:
        Configured SynthioWorkflow instance
    """
    if llm_client is None:
        llm_client = _create_llm_client()

    return SynthioWorkflow(llm_client, db_path)


def _create_llm_client() -> Any:
    """
    Create an LLM client based on settings.

    Returns:
        Configured LLM client instance
    """
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )

    elif settings.llm_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=settings.llm_temperature,
        )

    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )

    elif settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
