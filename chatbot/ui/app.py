"""Gradio chat interface for the Synthio chatbot."""

from typing import Any, Generator

import gradio as gr

from chatbot.graph.workflow import create_workflow, SynthioWorkflow


class SynthioChatUI:
    """Gradio-based chat interface for Synthio."""

    def __init__(self, db_path: str = "synthio.db"):
        """Initialize the chat UI."""
        self.db_path = db_path
        self._workflow: SynthioWorkflow | None = None

    @property
    def workflow(self) -> SynthioWorkflow:
        """Lazy initialization of the workflow."""
        if self._workflow is None:
            self._workflow = create_workflow(db_path=self.db_path)
        return self._workflow

    def process_query_sync(self, query: str) -> tuple[str, str]:
        """
        Process a user query synchronously.

        Args:
            query: User's question

        Returns:
            Tuple of (response_markdown, sql_query)
        """
        import asyncio

        try:
            # Execute the workflow
            result = asyncio.run(self.workflow.execute(query.strip()))

            # Extract response and SQL
            response = result.get("final_response", "I couldn't generate a response.")
            sql_query = result.get("sql_query", "")

            return response, sql_query

        except Exception as e:
            error_msg = f"❌ **Error:** {str(e)}\n\nPlease click 'New Chat' and try again."
            return error_msg, ""


def create_app(db_path: str = "synthio.db") -> gr.Blocks:
    """
    Create the Gradio app interface.

    Args:
        db_path: Path to the SQLite database

    Returns:
        Gradio Blocks app
    """
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

            # SQL Query accordion (collapsible)
            with gr.Accordion(
                "📝 View Generated SQL Query",
                open=False,
                visible=False,
            ) as sql_accordion:
                sql_output = gr.Textbox(
                    label="SQL Query",
                    lines=10,
                    max_lines=20,
                    interactive=False,
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

        # Generator function for streaming updates
        def on_submit_generator(query: str, has_resp: bool) -> Generator:
            """Handle submit with loading state."""
            # If already has a response, don't process
            if has_resp:
                yield (
                    gr.update(visible=False),  # loading_indicator
                    "⚠️ **Please click 'New Chat' to ask another question.**",  # response
                    "",  # sql
                    True,  # has_response state
                    gr.update(visible=False),  # sql_accordion
                    gr.update(visible=False),  # new_chat_prompt
                    gr.update(interactive=False),  # submit_btn
                )
                return

            if not query or not query.strip():
                yield (
                    gr.update(visible=False),  # loading_indicator
                    "⚠️ Please enter a question about your data.",  # response
                    "",  # sql
                    False,  # has_response state
                    gr.update(visible=False),  # sql_accordion
                    gr.update(visible=False),  # new_chat_prompt
                    gr.update(interactive=True),  # submit_btn
                )
                return

            # Step 1: Show loading state immediately, disable button
            yield (
                gr.update(value="⏳ **Generating response...** Please wait while our AI agents analyze your question.", visible=True),  # loading
                "*Processing your query...*",  # response placeholder
                "",  # sql empty
                False,  # has_response stays false during processing
                gr.update(visible=False),  # hide sql accordion
                gr.update(visible=False),  # hide new chat prompt
                gr.update(interactive=False, value="⏳ Processing..."),  # disable button with loading text
            )

            # Step 2: Process the query
            response, sql_query = chat_ui.process_query_sync(query)

            # Step 3: Show final results
            has_error = "Error" in response
            show_sql = bool(sql_query) and not has_error
            
            print(f"sql_query: {sql_query}")
            print(f"show_sql: {show_sql}")

            yield (
                gr.update(visible=False),  # hide loading indicator
                response,  # final response
                sql_query if sql_query else "-- No SQL query generated --",  # sql
                True,  # mark has_response as True
                gr.update(visible=show_sql, open=False),  # show sql accordion if we have SQL
                gr.update(visible=not has_error),  # show new chat prompt if no error
                gr.update(interactive=False, value="🔍 Ask Question"),  # keep button disabled, restore text
            )

        def on_new_chat():
            """Reset the chat to initial state."""
            return (
                gr.update(visible=False),  # loading_indicator
                "",  # query_input
                "*Ask a question about your pharmaceutical data...*",  # response
                "",  # sql
                False,  # has_response
                gr.update(visible=False),  # sql_accordion
                gr.update(visible=False),  # new_chat_prompt
                gr.update(interactive=True, value="🔍 Ask Question"),  # submit_btn
            )

        # Connect events
        submit_btn.click(
            fn=on_submit_generator,
            inputs=[query_input, has_response],
            outputs=[
                loading_indicator,
                response_output,
                sql_output,
                has_response,
                sql_accordion,
                new_chat_prompt,
                submit_btn,
            ],
        )

        # Allow Enter key to submit
        query_input.submit(
            fn=on_submit_generator,
            inputs=[query_input, has_response],
            outputs=[
                loading_indicator,
                response_output,
                sql_output,
                has_response,
                sql_accordion,
                new_chat_prompt,
                submit_btn,
            ],
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
                sql_accordion,
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
