"""Planner agent that analyzes user queries and creates natural language instructions."""

from typing import Any

from chatbot.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Agent responsible for analyzing user questions and creating detailed instructions.

    The planner understands business questions and provides clear, natural language
    instructions for the SQL Generator agent. It does NOT specify technical details
    like table names or SQL syntax - that's the SQL Generator's job.

    Output includes:
    - User intent interpretation
    - Assumptions being made
    - Detailed natural language instructions
    - Output requirements
    - Sorting and limit preferences
    """

    @property
    def prompt_template(self) -> str:
        return "planner.jinja"

    @property
    def agent_name(self) -> str:
        return "Query Planner"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze the user query and generate natural language instructions.

        Args:
            state: Current workflow state containing user_query and schema_context

        Returns:
            Updated state with query_plan containing instructions
        """
        user_query = state.get("user_query", "")
        schema_context = state.get("schema_context", "")

        # Render prompts
        system_prompt, user_prompt = self.render_prompt(
            schema_context=schema_context,
            user_query=user_query,
        )

        # Get LLM response
        response = await self.invoke_llm(system_prompt, user_prompt)

        # Parse the response
        try:
            plan_dict = self.parse_json_response(response)

            # Validate required fields and set defaults
            plan_dict.setdefault("user_intent", "")
            plan_dict.setdefault("assumptions", [])
            plan_dict.setdefault("instructions", "")
            plan_dict.setdefault("output_requirements", [])
            plan_dict.setdefault("sorting_preference", "")
            plan_dict.setdefault("limit_preference", "")
            plan_dict.setdefault("complexity", "medium")

            return {
                "query_plan": plan_dict,
                "error_message": "",
            }

        except ValueError as e:
            return {
                "query_plan": {
                    "user_intent": "Failed to analyze the question",
                    "assumptions": [],
                    "instructions": f"Please retrieve data to answer: {user_query}",
                    "output_requirements": [],
                    "sorting_preference": "",
                    "limit_preference": "",
                    "complexity": "unknown",
                },
                "error_message": str(e),
            }
