"""Base agent class with common functionality."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from jinja2 import Environment, FileSystemLoader

from chatbot.core.config import settings

# Marker used to separate system and user prompts in templates
PROMPT_SEPARATOR = "---USER_PROMPT_SEPARATOR---"


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the workflow.

    Provides common functionality for prompt rendering and LLM interaction.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize the base agent.

        Args:
            llm_client: LangChain LLM client instance
        """
        self.llm = llm_client
        self._jinja_env = Environment(
            loader=FileSystemLoader(settings.prompts_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Name of the Jinja template file for this agent."""
        pass

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable name for this agent."""
        pass

    def render_prompt(self, **kwargs) -> tuple[str, str]:
        """
        Render the system and user prompts from the Jinja template.

        The template should contain a separator marker between system and user prompts.

        Args:
            **kwargs: Variables to pass to the template

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        template = self._jinja_env.get_template(self.prompt_template)

        # Render the full template
        rendered = template.render(**kwargs)

        # Split by the separator marker
        if PROMPT_SEPARATOR in rendered:
            parts = rendered.split(PROMPT_SEPARATOR)
            system_prompt = parts[0].strip()
            user_prompt = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Fallback: treat everything as system prompt
            system_prompt = rendered.strip()
            user_prompt = ""

        return system_prompt, user_prompt

    def parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response, handling potential formatting issues.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Try direct parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {response[:500]}...")

    @abstractmethod
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's task.

        Args:
            state: Current workflow state

        Returns:
            Updated state dictionary
        """
        pass

    async def invoke_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Invoke the LLM with the given prompts.

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query prompt

        Returns:
            LLM response string
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content
