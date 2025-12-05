"""Main entry point for the Synthio chatbot."""

import asyncio
from typing import Any

from chatbot.core.config import settings
from chatbot.core.database import DatabaseManager
from chatbot.graph.workflow import create_workflow, SynthioWorkflow


class SynthioChatbot:
    """
    High-level interface for the Synthio chatbot.
    
    Provides a simple API for interacting with the multi-agent system.
    """
    
    def __init__(
        self,
        db_path: str | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ):
        """
        Initialize the chatbot.
        
        Args:
            db_path: Path to SQLite database (uses settings default if not provided)
            llm_provider: LLM provider name (uses settings default if not provided)
            llm_model: LLM model name (uses settings default if not provided)
        """
        # Override settings if provided
        if db_path:
            settings.database_path = db_path
        if llm_provider:
            settings.llm_provider = llm_provider
        if llm_model:
            settings.llm_model = llm_model
        
        self._workflow: SynthioWorkflow | None = None
    
    @property
    def workflow(self) -> SynthioWorkflow:
        """Lazy initialization of the workflow."""
        if self._workflow is None:
            self._workflow = create_workflow(db_path=settings.database_path)
        return self._workflow
    
    async def ask(self, question: str) -> str:
        """
        Ask a question about the data.
        
        Args:
            question: Natural language question
            
        Returns:
            Natural language answer
        """
        result = await self.workflow.execute(question)
        return result.get("final_response", "I couldn't generate a response.")
    
    def ask_sync(self, question: str) -> str:
        """
        Synchronous version of ask().
        
        Args:
            question: Natural language question
            
        Returns:
            Natural language answer
        """
        return asyncio.run(self.ask(question))
    
    async def ask_with_details(self, question: str) -> dict[str, Any]:
        """
        Ask a question and get detailed results including intermediate steps.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with full workflow state
        """
        return await self.workflow.execute(question)
    
    def get_schema_info(self) -> str:
        """
        Get information about the database schema.
        
        Returns:
            Formatted schema description
        """
        return self.workflow.schema_context
    
    def list_tables(self) -> list[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        return self.workflow.db_manager.get_table_names()


def run_cli():
    """Run the chatbot in CLI mode."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Synthio Chatbot - Ask questions about your pharmaceutical data"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="synthio.db",
        help="Path to SQLite database (default: synthio.db)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["openai", "azure_openai", "anthropic", "ollama"],
        help="LLM provider (default: from environment)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (default: from environment)"
    )
    parser.add_argument(
        "-q", "--question",
        type=str,
        default=None,
        help="Single question to ask (exits after answering)"
    )
    
    args = parser.parse_args()
    
    # Initialize chatbot
    print("🤖 Initializing Synthio Chatbot...")
    chatbot = SynthioChatbot(
        db_path=args.db,
        llm_provider=args.provider,
        llm_model=args.model,
    )
    
    # Single question mode
    if args.question:
        print(f"\n📝 Question: {args.question}\n")
        response = chatbot.ask_sync(args.question)
        print(f"💬 Answer:\n{response}")
        return
    
    # Interactive mode
    print("=" * 60)
    print("Welcome to Synthio Chatbot!")
    print("Ask questions about your pharmaceutical sales data.")
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'schema' to see the database schema.")
    print("Type 'tables' to list all tables.")
    print("=" * 60)
    
    while True:
        try:
            question = input("\n🔍 Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if question.lower() == "schema":
                print("\n📊 Database Schema:")
                print(chatbot.get_schema_info())
                continue
            
            if question.lower() == "tables":
                print("\n📋 Tables:")
                for table in chatbot.list_tables():
                    print(f"  • {table}")
                continue
            
            print("\n⏳ Processing your question...")
            response = chatbot.ask_sync(question)
            print(f"\n💬 Answer:\n{response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    run_cli()

