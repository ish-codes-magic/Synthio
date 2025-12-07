"""Guardrail agent that filters queries for relevance and safety."""

from typing import Any

from chatbot.agents.base import BaseAgent


class GuardrailAgent(BaseAgent):
    """
    Agent responsible for filtering user queries before processing.

    Checks for:
    - Relevance to the pharmaceutical data domain
    - Harmful or inappropriate content
    - Prompt injection attempts
    - Data manipulation requests
    - Off-topic queries

    Returns a decision (ALLOW/BLOCK) with an appropriate user response if blocked.
    """

    @property
    def prompt_template(self) -> str:
        return "guardrail.j2"

    @property
    def agent_name(self) -> str:
        return "Query Guardrail"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate the user query for relevance and safety.

        Args:
            state: Current workflow state containing user_query

        Returns:
            Updated state with guardrail_result
        """
        user_query = state.get("user_query", "")

        # Quick check for empty queries
        if not user_query or not user_query.strip():
            return {
                "guardrail_result": {
                    "decision": "BLOCK",
                    "category": "empty_query",
                    "confidence": 1.0,
                    "reasoning": "Empty query provided",
                    "user_response": "Please enter a question about the pharmaceutical sales data.",
                },
                "guardrail_passed": False,
            }

        # Render prompts
        system_prompt, user_prompt = self.render_prompt(
            user_query=user_query,
        )

        # Get LLM response
        response = await self.invoke_llm(system_prompt, user_prompt)

        # Parse the response
        try:
            result = self.parse_json_response(response)

            # Validate required fields
            decision = result.get("decision", "BLOCK").upper()
            result["decision"] = decision

            # Ensure we have a user response for blocked queries
            if decision == "BLOCK" and not result.get("user_response"):
                result["user_response"] = (
                    "I'm not able to process that request. I'm here to help you "
                    "analyze pharmaceutical sales data including prescriptions, "
                    "doctor performance, territory analysis, and sales activities. "
                    "Could you ask a question about our data?"
                )

            return {
                "guardrail_result": result,
                "guardrail_passed": decision == "ALLOW",
            }

        except ValueError as e:
            # If parsing fails, default to allowing the query
            # (better to let planner handle edge cases than block legitimate queries)
            return {
                "guardrail_result": {
                    "decision": "ALLOW",
                    "category": "parse_error",
                    "confidence": 0.5,
                    "reasoning": f"Failed to parse guardrail response: {str(e)}",
                    "user_response": "",
                },
                "guardrail_passed": True,
            }

    def is_obvious_attack(self, query: str) -> tuple[bool, str]:
        """
        Quick check for obvious attack patterns without LLM call.

        Args:
            query: User query string

        Returns:
            Tuple of (is_attack, response_message)
        """
        query_lower = query.lower()

        # Prompt injection patterns
        injection_patterns = [
            "ignore previous",
            "ignore all previous",
            "ignore your instructions",
            "disregard your",
            "forget your instructions",
            "you are now",
            "pretend you are",
            "act as if",
            "new instructions:",
            "system prompt:",
            "override:",
            "jailbreak",
            "dan mode",
            "developer mode",
        ]

        for pattern in injection_patterns:
            if pattern in query_lower:
                return True, (
                    "I noticed your message contains unusual instructions. "
                    "I'm designed to help with pharmaceutical sales data analysis. "
                    "Please ask a question about prescriptions, doctors, territories, "
                    "or sales activities!"
                )

        # SQL injection patterns
        sql_patterns = [
            "drop table",
            "delete from",
            "truncate table",
            "update set",
            "insert into",
            "; --",
            "' or '1'='1",
            "union select",
        ]

        for pattern in sql_patterns:
            if pattern in query_lower:
                return True, (
                    "I'm not able to process that request. "
                    "I can help you analyze our pharmaceutical sales data using natural language. "
                    "Try asking something like 'Who are the top 10 doctors by prescriptions?'"
                )

        return False, ""

