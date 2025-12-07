"""Configuration management for the Synthio chatbot."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()


def _setup_langsmith_early() -> None:
    """
    Set up LangSmith environment variables BEFORE any LangChain imports.
    
    This function is called at module load time to ensure tracing is
    configured before LangChain checks the environment.
    """
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    api_key = os.getenv("LANGSMITH_API_KEY", "")
    
    if tracing_enabled and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "synthio-chatbot")
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv(
            "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
        )
        print(f"🔍 LangSmith tracing enabled for project: {os.environ['LANGCHAIN_PROJECT']}")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


# ⚠️ CRITICAL: Set up LangSmith BEFORE any LangChain imports
_setup_langsmith_early()


@dataclass
class Settings:
    """Application settings with sensible defaults."""

    # Database settings
    database_path: str = field(
        default_factory=lambda: os.getenv("SYNTHIO_DB_PATH", "synthio.db")
    )

    # LLM settings
    llm_provider: Literal["openai", "azure_openai", "anthropic", "ollama"] = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini")
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.0"))
    )

    # OpenAI API Key
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # Azure OpenAI settings
    azure_openai_api_key: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY", "")
    )
    azure_openai_endpoint: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT", "")
    )
    azure_openai_deployment: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    )
    azure_openai_api_version: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    )

    # Anthropic API Key
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # Workflow settings
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )

    # Paths
    prompts_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "prompts"
    )

    # ==========================================================================
    # LangSmith Observability Settings
    # ==========================================================================

    langsmith_tracing: bool = field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    )

    langsmith_api_key: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "")
    )

    langsmith_project: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "synthio-chatbot")
    )

    langsmith_endpoint: str = field(
        default_factory=lambda: os.getenv(
            "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
        )
    )

    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    app_version: str = field(
        default_factory=lambda: os.getenv("APP_VERSION", "0.1.0")
    )

    def validate(self) -> None:
        """Validate the configuration."""
        if not Path(self.database_path).exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        if self.llm_provider == "azure_openai":
            if not self.azure_openai_api_key:
                raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
            if not self.azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
            if not self.azure_openai_deployment:
                raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable is required")

        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        if self.langsmith_tracing and not self.langsmith_api_key:
            raise ValueError(
                "LANGSMITH_API_KEY is required when LANGSMITH_TRACING is enabled"
            )

    def is_tracing_enabled(self) -> bool:
        """Check if LangSmith tracing is properly configured."""
        return self.langsmith_tracing and bool(self.langsmith_api_key)


# Global settings instance
settings = Settings()
