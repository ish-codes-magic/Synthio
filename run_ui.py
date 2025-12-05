#!/usr/bin/env python
"""
Synthio Chatbot - Gradio UI Entry Point.

Launch the web-based chat interface for the Synthio chatbot.

Usage:
    python run_ui.py                    # Launch on localhost:7860
    python run_ui.py --port 8080        # Custom port
    python run_ui.py --share            # Create public share link
"""

import argparse

from chatbot.ui.app import launch_app


def main():
    parser = argparse.ArgumentParser(
        description="Launch the Synthio Chatbot web interface"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="synthio.db",
        help="Path to SQLite database (default: synthio.db)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server hostname (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Server port (default: 7860)",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link",
    )

    args = parser.parse_args()

    print("🧬 Launching Synthio Chatbot UI...")
    print(f"   Database: {args.db}")
    print(f"   Server: http://{args.host}:{args.port}")
    if args.share:
        print("   Public sharing: Enabled")
    print()

    launch_app(
        db_path=args.db,
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()

