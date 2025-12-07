"""Node definitions for the LangGraph workflow."""

from typing import Any, Literal

from chatbot.agents import (
    GuardrailAgent,
    PlannerAgent,
    SQLGeneratorAgent,
    ValidatorAgent,
    WriterAgent,
)
from chatbot.core.models import AgentState


def create_guardrail_node(agent: GuardrailAgent):
    """
    Create a guardrail node function for the workflow.

    Args:
        agent: Initialized GuardrailAgent instance

    Returns:
        Async node function
    """
    async def guardrail_node(state: AgentState) -> dict[str, Any]:
        """Check if the query is relevant and safe."""
        # First, check for obvious attacks without LLM call
        query = state.get("user_query", "")
        is_attack, attack_response = agent.is_obvious_attack(query)

        if is_attack:
            return {
                "guardrail_result": {
                    "decision": "BLOCK",
                    "category": "obvious_attack",
                    "confidence": 1.0,
                    "reasoning": "Detected obvious attack pattern",
                    "user_response": attack_response,
                },
                "guardrail_passed": False,
            }

        # If not an obvious attack, use LLM to evaluate
        return await agent.execute(dict(state))

    return guardrail_node


def create_planner_node(agent: PlannerAgent):
    """
    Create a planner node function for the workflow.

    Args:
        agent: Initialized PlannerAgent instance

    Returns:
        Async node function
    """
    async def planner_node(state: AgentState) -> dict[str, Any]:
        """Plan the query execution strategy."""
        return await agent.execute(dict(state))

    return planner_node


def create_sql_generator_node(agent: SQLGeneratorAgent):
    """
    Create an SQL generator node function for the workflow.

    Args:
        agent: Initialized SQLGeneratorAgent instance

    Returns:
        Async node function
    """
    async def sql_generator_node(state: AgentState) -> dict[str, Any]:
        """Generate and execute SQL query."""
        return await agent.execute(dict(state))

    return sql_generator_node


def create_validator_node(agent: ValidatorAgent):
    """
    Create a validator node function for the workflow.

    Args:
        agent: Initialized ValidatorAgent instance

    Returns:
        Async node function
    """
    async def validator_node(state: AgentState) -> dict[str, Any]:
        """Validate the query results."""
        result = await agent.execute(dict(state))

        # Increment retry count if retrying
        if result.get("should_retry"):
            result["retry_count"] = state.get("retry_count", 0) + 1

        return result

    return validator_node


def create_writer_node(agent: WriterAgent):
    """
    Create a writer node function for the workflow.

    Args:
        agent: Initialized WriterAgent instance

    Returns:
        Async node function
    """
    async def writer_node(state: AgentState) -> dict[str, Any]:
        """Generate the final response."""
        return await agent.execute(dict(state))

    return writer_node


def should_retry(state: AgentState) -> Literal["sql_generator", "writer"]:
    """
    Determine whether to retry SQL generation or proceed to writing.

    This is a conditional edge function that routes the workflow based on
    validation results and retry count.

    Args:
        state: Current workflow state

    Returns:
        Next node name ("sql_generator" or "writer")
    """
    should_retry_flag = state.get("should_retry", False)
    retry_count = state.get("retry_count", 0)
    max_retries = 3

    if should_retry_flag and retry_count < max_retries:
        return "sql_generator"

    return "writer"


# Standalone node functions for direct use
async def guardrail_node(state: AgentState, agent: GuardrailAgent) -> dict[str, Any]:
    """Standalone guardrail node."""
    return await agent.execute(dict(state))


async def planner_node(state: AgentState, agent: PlannerAgent) -> dict[str, Any]:
    """Standalone planner node."""
    return await agent.execute(dict(state))


async def sql_generator_node(state: AgentState, agent: SQLGeneratorAgent) -> dict[str, Any]:
    """Standalone SQL generator node."""
    return await agent.execute(dict(state))


async def validator_node(state: AgentState, agent: ValidatorAgent) -> dict[str, Any]:
    """Standalone validator node."""
    result = await agent.execute(dict(state))
    if result.get("should_retry"):
        result["retry_count"] = state.get("retry_count", 0) + 1
    return result


async def writer_node(state: AgentState, agent: WriterAgent) -> dict[str, Any]:
    """Standalone writer node."""
    return await agent.execute(dict(state))
