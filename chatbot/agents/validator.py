"""Validator agent that checks query results for correctness."""

from typing import Any

import pandas as pd

from chatbot.agents.base import BaseAgent
from chatbot.core.models import ValidationResult


class ValidatorAgent(BaseAgent):
    """
    Agent responsible for validating query results.
    
    Checks whether:
    - The query executed successfully
    - Results make logical sense
    - The answer addresses the user's question
    - There are any data quality issues
    """
    
    @property
    def prompt_template(self) -> str:
        return "validator.jinja"
    
    @property
    def agent_name(self) -> str:
        return "Result Validator"
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the SQL query results.
        
        Args:
            state: Current workflow state containing sql_result and query context
            
        Returns:
            Updated state with validation_result
        """
        user_query = state.get("user_query", "")
        query_plan = state.get("query_plan", {})
        sql_query = state.get("sql_query", "")
        sql_result = state.get("sql_result", {})
        schema_context = state.get("schema_context", "")
        
        # Prepare result preview for the prompt
        sql_error = sql_result.get("error")
        row_count = sql_result.get("row_count", 0)
        
        result_preview = ""
        if sql_result.get("success") and sql_result.get("data"):
            df = pd.DataFrame(sql_result["data"])
            # Limit preview to first 10 rows
            result_preview = df.head(10).to_string(index=False)
        
        # Render prompts
        system_prompt, user_prompt = self.render_prompt(
            schema_context=schema_context,
            user_query=user_query,
            query_plan=query_plan,
            sql_query=sql_query,
            sql_error=sql_error,
            row_count=row_count,
            result_preview=result_preview,
        )
        
        # Get LLM response
        response = await self.invoke_llm(system_prompt, user_prompt)
        
        # Parse the response
        try:
            validation_dict = self.parse_json_response(response)
            
            # Determine if retry is needed
            is_valid = validation_dict.get("is_valid", False)
            confidence = validation_dict.get("confidence", 0.0)
            
            # Trigger retry if validation failed or confidence is low
            should_retry = not is_valid or confidence < 0.5
            retry_count = state.get("retry_count", 0)
            
            return {
                "validation_result": validation_dict,
                "should_retry": should_retry and retry_count < 3,
                "error_message": "" if is_valid else validation_dict.get("reasoning", "Validation failed"),
            }
            
        except ValueError as e:
            return {
                "validation_result": {
                    "is_valid": False,
                    "confidence": 0.0,
                    "issues": ["Failed to parse validation response"],
                    "suggestions": [],
                    "reasoning": str(e),
                },
                "should_retry": True,
                "error_message": str(e),
            }
    
    def create_validation_result(self, result_dict: dict[str, Any]) -> ValidationResult:
        """
        Create a ValidationResult dataclass from the parsed dictionary.
        
        Args:
            result_dict: Parsed validation dictionary
            
        Returns:
            ValidationResult instance
        """
        return ValidationResult(
            is_valid=result_dict.get("is_valid", False),
            confidence=result_dict.get("confidence", 0.0),
            issues=result_dict.get("issues", []),
            suggestions=result_dict.get("suggestions", []),
            reasoning=result_dict.get("reasoning", ""),
        )

