"""Writer agent that generates human-friendly responses."""

from typing import Any

import pandas as pd

from chatbot.agents.base import BaseAgent


class WriterAgent(BaseAgent):
    """
    Agent responsible for generating the final response.
    
    Transforms raw query results into:
    - Clear, well-formatted answers
    - Business-friendly language
    - Actionable insights
    - Appropriate visualizations (when needed)
    """
    
    @property
    def prompt_template(self) -> str:
        return "writer.j2"
    
    @property
    def agent_name(self) -> str:
        return "Response Writer"
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Generate the final human-readable response.
        
        Args:
            state: Current workflow state containing all query results
            
        Returns:
            Updated state with final_response
        """
        user_query = state.get("user_query", "")
        query_plan = state.get("query_plan", {})
        sql_query = state.get("sql_query", "")
        sql_result = state.get("sql_result", {})
        validation_result = state.get("validation_result", {})
        
        # Format result data for the prompt
        row_count = sql_result.get("row_count", 0)
        result_data = ""
        
        if sql_result.get("success") and sql_result.get("data"):
            df = pd.DataFrame(sql_result["data"])
            result_data = self._format_data_for_display(df)
        
        # Format validation notes
        validation_notes = self._format_validation_notes(validation_result)
        
        # Render prompts
        system_prompt, user_prompt = self.render_prompt(
            user_query=user_query,
            query_plan=query_plan,
            sql_query=sql_query,
            row_count=row_count,
            result_data=result_data,
            validation_notes=validation_notes,
        )
        
        # Get LLM response
        response = await self.invoke_llm(system_prompt, user_prompt)
        
        return {
            "final_response": response.strip(),
        }
    
    def _format_data_for_display(self, df: pd.DataFrame, max_rows: int = 50) -> str:
        """
        Format DataFrame for display in the prompt.
        
        Args:
            df: DataFrame to format
            max_rows: Maximum number of rows to include
            
        Returns:
            Formatted string representation
        """
        if df.empty:
            return "No data available."
        
        # Truncate if too many rows
        if len(df) > max_rows:
            display_df = df.head(max_rows)
            truncated_note = f"\n... and {len(df) - max_rows} more rows"
        else:
            display_df = df
            truncated_note = ""
        
        # Format as markdown table for better readability
        table_str = display_df.to_markdown(index=False)
        
        return table_str + truncated_note
    
    def _format_validation_notes(self, validation_result: dict[str, Any]) -> str:
        """
        Format validation results as notes for the writer.
        
        Args:
            validation_result: Validation result dictionary
            
        Returns:
            Formatted validation notes string
        """
        if not validation_result:
            return "No validation performed."
        
        notes = []
        
        is_valid = validation_result.get("is_valid", False)
        confidence = validation_result.get("confidence", 0.0)
        
        notes.append(f"Validation Status: {'Passed' if is_valid else 'Failed'}")
        notes.append(f"Confidence: {confidence:.0%}")
        
        issues = validation_result.get("issues", [])
        if issues:
            notes.append("Issues found:")
            for issue in issues:
                notes.append(f"  - {issue}")
        
        suggestions = validation_result.get("suggestions", [])
        if suggestions:
            notes.append("Suggestions:")
            for suggestion in suggestions:
                notes.append(f"  - {suggestion}")
        
        return "\n".join(notes)

