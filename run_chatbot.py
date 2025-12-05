#!/usr/bin/env python
"""
Synthio Chatbot - Entry point script.

This script provides a convenient way to run the chatbot from the project root.

Usage:
    python run_chatbot.py                           # Interactive mode
    python run_chatbot.py -q "Your question here"   # Single question mode
    python run_chatbot.py --help                    # Show help
"""

from chatbot.main import run_cli

if __name__ == "__main__":
    run_cli()

