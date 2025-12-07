"""Gradio chat interface for the Synthio chatbot."""

# ⚠️ CRITICAL: Import config FIRST to set up LangSmith before any LangChain imports
from chatbot.core.config import settings  # noqa: F401

import asyncio
import concurrent.futures

import gradio as gr

from chatbot.graph.workflow import SynthioWorkflow, create_workflow

# Thread pool for running async code efficiently
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _run_async(coro):
    """Run an async coroutine in a new event loop efficiently."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class SynthioChatUI:
    """Gradio-based chat interface for Synthio."""

    def __init__(self, db_path: str = "synthio.db"):
        """Initialize the chat UI."""
        self.db_path = db_path
        self._workflow: SynthioWorkflow | None = None
        # Pre-initialize workflow to avoid first-call delay
        self._ensure_workflow()

    def _ensure_workflow(self) -> SynthioWorkflow:
        """Ensure workflow is initialized."""
        if self._workflow is None:
            print("🔧 Initializing workflow (this happens once)...")
            self._workflow = create_workflow(db_path=self.db_path)
            print("✅ Workflow ready!")
        return self._workflow

    @property
    def workflow(self) -> SynthioWorkflow:
        """Get the workflow instance."""
        return self._ensure_workflow()

    def process_query(self, query: str) -> tuple[str, str, bool]:
        """
        Process a user query.

        Args:
            query: User's question

        Returns:
            Tuple of (response_markdown, sql_query, was_blocked)
        """
        try:
            # Execute the workflow using the thread pool
            result = _run_async(self.workflow.execute(query.strip()))

            # Check if query was blocked by guardrail
            guardrail_passed = result.get("guardrail_passed", True)

            # Extract response and SQL
            response = result.get("final_response", "I couldn't generate a response.")
            sql_query = result.get("sql_query", "")

            # If blocked, there won't be SQL
            was_blocked = not guardrail_passed

            return response, sql_query, was_blocked

        except Exception as e:
            error_msg = f"❌ **Error:** {str(e)}\n\nPlease click 'New Chat' and try again."
            return error_msg, "", False


def create_app(db_path: str = "synthio.db") -> gr.Blocks:
    """
    Create the Gradio app interface.

    Args:
        db_path: Path to the SQLite database

    Returns:
        Gradio Blocks app
    """
    # Pre-initialize the chat UI (and workflow) at app creation time
    print("🚀 Starting Synthio Chatbot...")
    chat_ui = SynthioChatUI(db_path=db_path)

    with gr.Blocks(title="Synthio Chatbot") as app:
        # State to track if response has been generated
        has_response = gr.State(False)

        # Header
        gr.Markdown(
            """
            # 🧬 Synthio Chatbot
            ### AI-powered pharmaceutical data analytics
            ---
            """
        )

        with gr.Column():
            # Query input
            query_input = gr.Textbox(
                label="Your Question",
                placeholder="e.g., Who are the top 10 doctors by prescription count?",
                lines=2,
                max_lines=4,
            )

            # Buttons row
            with gr.Row():
                submit_btn = gr.Button(
                    "🔍 Ask Question",
                    variant="primary",
                    scale=2,
                )
                new_chat_btn = gr.Button(
                    "🔄 New Chat",
                    variant="secondary",
                    scale=1,
                )

            gr.Markdown("---")

            # Response section
            gr.Markdown("### 💬 Response")

            # Loading indicator (hidden by default)
            loading_indicator = gr.Markdown(
                value="",
                visible=False,
            )

            response_output = gr.Markdown(
                value="*Ask a question about your pharmaceutical data...*",
            )

            # SQL Query accordion
            with gr.Accordion(
                "📝 View Generated SQL Query",
                open=False,
                visible=True,
            ):
                sql_output = gr.Textbox(
                    label="SQL Query",
                    lines=10,
                    max_lines=20,
                    interactive=False,
                    value="-- SQL will appear here after you ask a question --",
                )

            # New chat prompt (shown after response)
            new_chat_prompt = gr.Markdown(
                visible=False,
                value="💡 **Want to ask another question?** Click the **New Chat** button above.",
            )

        # Footer
        gr.Markdown(
            """
            ---
            <center>Powered by LangGraph • Multi-Agent AI System</center>
            """,
        )

        def on_submit(query: str, has_resp: bool):
            """Handle submit - simple function, no generator."""
            # If already has a response, don't process again
            if has_resp:
                return (
                    gr.update(visible=False),
                    "⚠️ **Please click 'New Chat' to ask another question.**",
                    gr.update(),
                    True,
                    gr.update(visible=True),
                    gr.update(interactive=False, value="🔍 Ask Question"),
                )

            # Empty query case
            if not query or not query.strip():
                return (
                    gr.update(visible=False),
                    "⚠️ Please enter a question about your data.",
                    gr.update(),
                    False,
                    gr.update(visible=False),
                    gr.update(interactive=True, value="🔍 Ask Question"),
                )

            # Process the query
            response, sql_query, was_blocked = chat_ui.process_query(query)

            # Determine what to show
            has_error = "Error" in response

            # SQL value
            if was_blocked:
                sql_value = "-- Query was not processed (see response above) --"
            elif sql_query:
                sql_value = sql_query
            else:
                sql_value = "-- No SQL query generated --"

            return (
                gr.update(visible=False),
                response,
                sql_value,
                True,
                gr.update(visible=not has_error),
                gr.update(interactive=False, value="🔍 Ask Question"),
            )

        def on_new_chat():
            """Reset the chat to initial state."""
            return (
                gr.update(visible=False),
                "",
                "*Ask a question about your pharmaceutical data...*",
                "-- SQL will appear here after you ask a question --",
                False,
                gr.update(visible=False),
                gr.update(interactive=True, value="🔍 Ask Question"),
            )

        submit_btn.click(
            fn=on_submit,
            inputs=[query_input, has_response],
            outputs=[
                loading_indicator,
                response_output,
                sql_output,
                has_response,
                new_chat_prompt,
                submit_btn,
            ],
            show_progress="full",  # This shows the built-in Gradio loading indicator
        )

        # Allow Enter key to submit
        query_input.submit(
            fn=on_submit,
            inputs=[query_input, has_response],
            outputs=[
                loading_indicator,
                response_output,
                sql_output,
                has_response,
                new_chat_prompt,
                submit_btn,
            ],
            show_progress="full",
        )

        new_chat_btn.click(
            fn=on_new_chat,
            inputs=[],
            outputs=[
                loading_indicator,
                query_input,
                response_output,
                sql_output,
                has_response,
                new_chat_prompt,
                submit_btn,
            ],
        )

    return app


def launch_app(
    db_path: str = "synthio.db",
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    share: bool = False,
) -> None:
    """
    Launch the Gradio app.

    Args:
        db_path: Path to the SQLite database
        server_name: Server hostname
        server_port: Server port
        share: Whether to create a public share link
    """
    app = create_app(db_path=db_path)
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
    )


if __name__ == "__main__":
    launch_app()
