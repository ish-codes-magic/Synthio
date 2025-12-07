"""
Synthio Chatbot - LangGraph-based multi-agent system for data analysis.

This chatbot uses a multi-agent architecture to answer questions about
pharmaceutical sales and healthcare provider data stored in SQLite.
"""

# ⚠️ CRITICAL: Import config FIRST to set up LangSmith before any LangChain imports
from chatbot.core.config import settings  # noqa: F401

from chatbot.main import SynthioChatbot

__version__ = "0.1.0"
__all__ = ["SynthioChatbot", "settings"]
