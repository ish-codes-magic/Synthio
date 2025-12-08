# Synthio Chatbot

AI-powered pharmaceutical data analytics chatbot built with LangGraph multi-agent architecture.

## Features

- 🤖 **Multi-Agent Architecture** - Specialized agents for planning, SQL generation, validation, and response writing
- 🛡️ **Guardrail Protection** - Filters irrelevant queries and blocks jailbreak attempts
- 🔍 **Natural Language to SQL** - Converts business questions to optimized SQLite queries
- 📊 **LangSmith Observability** - Full tracing and monitoring of all LLM calls
- 🖥️ **Gradio Web UI** - Beautiful, responsive chat interface
- 🔄 **Auto-Retry** - Validates results and retries if confidence is low

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp chatbot/config.example.env .env
# Edit .env with your API keys

# 3. Launch the Web UI
python run_ui.py
```

Open http://localhost:7860 in your browser.

## Architecture

The chatbot uses a **multi-agent architecture** with clear separation of responsibilities:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Question                                 │
│            "Who are the top prescribing doctors?"                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  🛡️ GUARDRAIL AGENT (Security Filter)                               │
│                                                                      │
│  Role: Filter irrelevant/harmful queries before processing          │
│                                                                      │
│  Checks for:                                                        │
│  - Off-topic questions (weather, sports, coding help)               │
│  - Prompt injection attempts ("ignore instructions", "pretend")     │
│  - SQL injection patterns                                           │
│  - Medical advice requests                                          │
│  - Harmful content requests                                         │
│                                                                      │
│  Output: ALLOW → Continue | BLOCK → Friendly rejection message      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
              [BLOCKED]              [ALLOWED]
                    │                       │
                    ▼                       ▼
         Friendly rejection    ┌─────────────────────────────────────┐
         message to user       │  🎯 PLANNER AGENT (Business Analyst) │
                               │                                      │
                               │  Role: Understand the question and   │
                               │  provide natural language instructions│
                               │                                      │
                               │  Output Example:                     │
                               │  "Get total prescription count for   │
                               │   each doctor. Include name and      │
                               │   specialty. Rank highest to lowest. │
                               │   Show only top 10."                 │
                               │                                      │
                               │  Does NOT specify: table names,      │
                               │  joins, SQL syntax                   │
                               └─────────────────────────────────────┘
                                               │
                                               ▼
                               ┌─────────────────────────────────────┐
                               │  💾 SQL GENERATOR AGENT              │
                               │     (Technical Expert)               │
                               │                                      │
                               │  Role: Implement the instructions    │
                               │                                      │
                               │  Responsibilities:                   │
                               │  - Identify needed tables            │
                               │  - Determine optimal joins           │
                               │  - Write efficient SQL               │
                               │  - Execute and return results        │
                               └─────────────────────────────────────┘
                                               │
                                               ▼
                               ┌─────────────────────────────────────┐
                               │  ✅ VALIDATOR AGENT                  │
                               │                                      │
                               │  - Checks if results answer question │
                               │  - Validates data quality            │
                               │  - Triggers retry if confidence low  │
                               └─────────────────────────────────────┘
                                               │
                                   ┌───────────┴───────────┐
                                   │                       │
                                   ▼                       ▼
                             [Retry SQL]           ┌──────────────────┐
                             (max 3x)              │ ✍️ WRITER AGENT   │
                                                   │                  │
                                                   │ - Format results │
                                                   │ - Add insights   │
                                                   │ - Generate final │
                                                   │   response       │
                                                   └──────────────────┘
                                                           │
                                                           ▼
                                                   ┌──────────────────┐
                                                   │  Final Response   │
                                                   └──────────────────┘
```

## Project Structure

```
synthio/
├── chatbot/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # CLI entry point
│   ├── config.example.env       # Example environment configuration
│   │
│   ├── core/                    # Core functionality
│   │   ├── config.py           # Settings management + LangSmith setup
│   │   ├── database.py         # Database connection and queries
│   │   ├── models.py           # Data models and state definitions
│   │   ├── schema.py           # Schema extraction and documentation
│   │   └── tracing.py          # LangSmith tracing utilities
│   │
│   ├── agents/                  # Agent implementations
│   │   ├── base.py             # Base agent class with LLM invocation
│   │   ├── guardrail.py        # Security and relevance filter
│   │   ├── planner.py          # Natural language instruction generator
│   │   ├── sql_generator.py    # SQL query builder and executor
│   │   ├── validator.py        # Result validation agent
│   │   └── writer.py           # Response writing agent
│   │
│   ├── prompts/                 # Jinja2 prompt templates
│   │   ├── guardrail.j2        # Security filter prompts
│   │   ├── planner.j2          # Business analysis prompts
│   │   ├── sql_generator.j2    # SQL generation prompts
│   │   ├── validator.j2        # Validation prompts
│   │   └── writer.j2           # Response writing prompts
│   │
│   ├── graph/                   # LangGraph workflow
│   │   ├── nodes.py            # Node definitions
│   │   └── workflow.py         # Workflow orchestration
│   │
│   └── ui/                      # Gradio Web Interface
│       ├── __init__.py
│       └── app.py              # Gradio app implementation
│
├── data/                        # CSV data files
├── tests/                       # Test suite
├── run_ui.py                   # Web UI launcher
├── run_chatbot.py              # CLI launcher
├── pyproject.toml              # Project configuration
└── requirements.txt            # Dependencies
```

## Installation

```bash
# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Configuration

1. Copy the example configuration:
   ```bash
   cp chatbot/config.example.env .env
   ```

2. Edit `.env` and add your API keys (see LLM Providers section below)

## Usage

### Web UI (Recommended)

Launch the Gradio web interface:

```bash
python run_ui.py
```

Options:
```bash
python run_ui.py --port 8080        # Custom port
python run_ui.py --host 0.0.0.0     # Allow external access
python run_ui.py --share            # Create public share link
```

The UI features:
- 💬 Clean chat interface
- ⏳ Loading animation while processing
- 📝 Collapsible SQL query viewer
- 🔄 "New Chat" button for fresh conversations
- 📱 Responsive design

### CLI Mode

Interactive mode:
```bash
python run_chatbot.py
```

Single question:
```bash
python run_chatbot.py -q "What are the top 5 doctors by prescription count?"
```

### Programmatic Usage

```python
from chatbot import SynthioChatbot

chatbot = SynthioChatbot(db_path="synthio.db")

# Simple question
response = chatbot.ask_sync("Show me all doctors in Territory 1")
print(response)

# Get full details including SQL
import asyncio
result = asyncio.run(chatbot.ask_with_details("List all accounts"))
print("Instructions:", result["query_plan"]["instructions"])
print("SQL:", result["sql_query"])
print("Response:", result["final_response"])
print("Blocked:", not result["guardrail_passed"])
```

## Guardrail Protection

The Guardrail Agent filters queries to ensure:

### ✅ Allowed Queries
- Doctor/HCP information, rankings, performance
- Prescription trends, counts, comparisons
- Sales rep activities and performance
- Territory and regional analysis
- Account/facility information
- Market share and patient metrics
- Insurance/payor distribution

### ❌ Blocked Queries
- Off-topic questions (weather, sports, coding)
- Prompt injection ("ignore instructions", "pretend you are")
- SQL injection attempts
- Medical advice requests
- Personal data requests (SSN, salaries)
- Harmful content requests

When blocked, users receive a friendly message explaining what types of questions can be asked.

## LLM Providers

### OpenAI
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt_model_name
OPENAI_API_KEY=sk-your-key-here
```

### Azure OpenAI
```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-01
```

### Anthropic
```bash
uv pip install langchain-anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=anthropic_model_name
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Ollama (Local)
```bash
uv pip install langchain-ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
```

## LangSmith Observability

Enable production-grade tracing and monitoring:

```bash
# In your .env file
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your-key-here
LANGSMITH_PROJECT=synthio-chatbot
ENVIRONMENT=production
```

LangSmith provides:
- 📊 Full trace visualization of agent workflows
- ⏱️ Latency tracking for each LLM call
- 💰 Token usage monitoring
- 🐛 Error tracking and debugging
- 📈 Performance analytics over time

Get your API key at [smith.langchain.com](https://smith.langchain.com)

## Database Schema

The chatbot works with pharmaceutical sales data:

### Dimension Tables
- **hcp_dim** - Healthcare professionals (doctors)
- **account_dim** - Hospitals and clinics
- **rep_dim** - Sales representatives
- **territory_dim** - Geographic territories
- **date_dim** - Calendar/time dimensions

### Fact Tables
- **fact_rx** - Prescription data (TRx, NRx counts)
- **fact_rep_activity** - Sales rep interactions
- **fact_ln_metrics** - Market intelligence metrics
- **fact_payor_mix** - Insurance/payor breakdown

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
