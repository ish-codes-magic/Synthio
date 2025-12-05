"""SQL Generator agent that translates natural language instructions into SQL queries."""

from typing import Any

import pandas as pd

from chatbot.agents.base import BaseAgent
from chatbot.core.database import DatabaseManager
from chatbot.core.models import SQLResult


class SQLGeneratorAgent(BaseAgent):
    """
    Agent responsible for translating instructions into SQL and executing queries.

    Receives natural language instructions from the Planner agent and:
    - Figures out which tables and columns are needed
    - Determines optimal joins and relationships
    - Writes efficient SQLite queries
    - Executes queries and returns results
    """

    def __init__(self, llm_client: Any, db_manager: DatabaseManager):
        """
        Initialize the SQL generator agent.

        Args:
            llm_client: LangChain LLM client instance
            db_manager: Database manager for query execution
        """
        super().__init__(llm_client)
        self.db_manager = db_manager

    @property
    def prompt_template(self) -> str:
        return "sql_generator.j2"

    @property
    def agent_name(self) -> str:
        return "SQL Generator"

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Generate SQL from natural language instructions and execute it.

        Args:
            state: Current workflow state containing query_plan and schema_context

        Returns:
            Updated state with sql_query and sql_result
        """
        user_query = state.get("user_query", "")
        query_plan = state.get("query_plan", {})
        schema_context = state.get("schema_context", "")

        # Extract instruction details from the plan
        instructions = query_plan.get("instructions", "")
        user_intent = query_plan.get("user_intent", "")
        output_requirements = query_plan.get("output_requirements", [])
        sorting_preference = query_plan.get("sorting_preference", "")
        limit_preference = query_plan.get("limit_preference", "")

        # Render prompts with the natural language instructions
        system_prompt, user_prompt = self.render_prompt(
            schema_context=schema_context,
            user_query=user_query,
            instructions=instructions,
            user_intent=user_intent,
            output_requirements=output_requirements,
            sorting_preference=sorting_preference,
            limit_preference=limit_preference,
        )

        # Get LLM response
        response = await self.invoke_llm(system_prompt, user_prompt)

        # Parse the response
        try:
            result_dict = self.parse_json_response(response)
            sql_query = result_dict.get("sql_query", "")
            reasoning = result_dict.get("reasoning", "")

            if not sql_query:
                return {
                    "sql_query": "",
                    "sql_reasoning": reasoning,
                    "sql_result": {
                        "query": "",
                        "success": False,
                        "data": None,
                        "error": "No SQL query generated",
                        "row_count": 0,
                    },
                    "error_message": "No SQL query generated",
                }

            # Execute the query
            df, error = self.db_manager.execute_query(sql_query)

            if error:
                return {
                    "sql_query": sql_query,
                    "sql_reasoning": reasoning,
                    "sql_result": {
                        "query": sql_query,
                        "success": False,
                        "data": None,
                        "error": error,
                        "row_count": 0,
                    },
                    "error_message": error,
                }

            return {
                "sql_query": sql_query,
                "sql_reasoning": reasoning,
                "sql_result": {
                    "query": sql_query,
                    "success": True,
                    "data": df.to_dict(orient="records"),
                    "error": None,
                    "row_count": len(df),
                },
                "error_message": "",
            }

        except ValueError as e:
            return {
                "sql_query": "",
                "sql_reasoning": "",
                "sql_result": {
                    "query": "",
                    "success": False,
                    "data": None,
                    "error": str(e),
                    "row_count": 0,
                },
                "error_message": str(e),
            }

    def create_sql_result(
        self,
        query: str,
        df: pd.DataFrame | None,
        error: str | None,
    ) -> SQLResult:
        """
        Create an SQLResult dataclass from execution results.

        Args:
            query: The executed SQL query
            df: Result DataFrame or None
            error: Error message or None

        Returns:
            SQLResult instance
        """
        return SQLResult(
            query=query,
            success=error is None,
            data=df,
            error=error,
            row_count=len(df) if df is not None else 0,
        )
