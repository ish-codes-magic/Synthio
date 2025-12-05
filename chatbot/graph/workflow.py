"""LangGraph workflow definition for the Synthio chatbot."""

from typing import Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chatbot.agents import (
    PlannerAgent,
    SQLGeneratorAgent,
    ValidatorAgent,
    WriterAgent,
)
from chatbot.core.config import settings
from chatbot.core.database import DatabaseManager
from chatbot.core.models import AgentState
from chatbot.core.schema import get_database_schema
from chatbot.graph.nodes import (
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
        workflow.add_node("planner", create_planner_node(self.planner))
        workflow.add_node("sql_generator", create_sql_generator_node(self.sql_generator))
        workflow.add_node("validator", create_validator_node(self.validator))
        workflow.add_node("writer", create_writer_node(self.writer))

        # Define edges
        workflow.set_entry_point("planner")
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

    async def execute(self, user_query: str) -> dict[str, Any]:
        """
        Execute the workflow for a user query.

        Args:
            user_query: The user's natural language question

        Returns:
            Final workflow state with the response
        """
        # Initialize state
        initial_state: AgentState = {
            "user_query": user_query,
            "schema_context": self.schema_context,
            "retry_count": 0,
            "should_retry": False,
            "messages": [],
        }

        # Execute the workflow
        final_state = await self.workflow.ainvoke(initial_state)

        return dict(final_state)

    def execute_sync(self, user_query: str) -> dict[str, Any]:
        """
        Synchronous wrapper for execute().

        Args:
            user_query: The user's natural language question

        Returns:
            Final workflow state with the response
        """
        import asyncio

        return asyncio.run(self.execute(user_query))


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
