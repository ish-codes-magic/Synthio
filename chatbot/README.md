# Synthio Chatbot

An AI-powered multi-agent chatbot for pharmaceutical data analytics, built with LangGraph.

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
│  🎯 PLANNER AGENT (The Business Analyst)                             │
│                                                                      │
│  Role: Understand the question, provide natural language instructions│
│                                                                      │
│  Output Example:                                                     │
│  "Get the total prescription count for each doctor. Include their   │
│   name and specialty. Rank from highest to lowest prescriptions.    │
│   Show only the top 10 performers."                                 │
│                                                                      │
│  Does NOT specify: table names, joins, SQL syntax                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  💾 SQL GENERATOR AGENT (The Technical Expert)                       │
│                                                                      │
│  Role: Figure out HOW to implement the instructions                  │
│                                                                      │
│  Responsibilities:                                                   │
│  - Identify which tables are needed (hcp_dim, fact_rx)              │
│  - Determine joins (hcp_id relationship)                            │
│  - Write optimal SQL query                                          │
│  - Execute and return results                                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ✅ VALIDATOR AGENT                                                  │
│  - Checks if results answer the question                             │
│  - Validates data quality and logic                                  │
│  - Triggers retry if confidence is low                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
              [Retry SQL]           ┌─────────────────────────────────┐
                                    │  ✍️ WRITER AGENT                 │
                                    │  - Formats results for humans    │
                                    │  - Highlights key insights       │
                                    │  - Generates final response      │
                                    └─────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌─────────────────────────────────┐
                                    │        Final Response            │
                                    └─────────────────────────────────┘
```

## Agent Responsibilities

### 🎯 Planner Agent
- **Acts as**: Business Analyst / Product Manager
- **Input**: User's natural language question
- **Output**: Detailed natural language instructions
- **Does NOT**: Mention table names, column names, or SQL syntax

Example output:
```json
{
  "user_intent": "Find the highest-performing doctors by prescription volume",
  "instructions": "Get the total number of prescriptions written by each doctor. Include the doctor's full name and their medical specialty. Rank them from highest to lowest prescription count. Return only the top 10.",
  "output_requirements": ["Doctor name", "Specialty", "Total prescriptions"],
  "sorting_preference": "Descending by prescription count",
  "limit_preference": "Top 10"
}
```

### 💾 SQL Generator Agent
- **Acts as**: Database Expert / SQL Developer
- **Input**: Natural language instructions from Planner
- **Output**: Optimized SQL query + execution results
- **Responsibilities**: 
  - Interpret business requirements
  - Select appropriate tables and columns
  - Design efficient joins
  - Write clean, performant SQL

### ✅ Validator Agent
- **Acts as**: QA Analyst
- **Checks**: Result correctness, data quality, logical consistency
- **Can trigger**: Retry loop if confidence is low

### ✍️ Writer Agent
- **Acts as**: Communications Specialist
- **Transforms**: Raw data into human-friendly insights
- **Formats**: Markdown tables, bullet points, key highlights

## Project Structure

```
chatbot/
├── __init__.py              # Package initialization
├── main.py                  # Entry point and CLI
├── config.example.env       # Example environment configuration
│
├── core/                    # Core functionality
│   ├── config.py           # Settings management
│   ├── database.py         # Database connection and queries
│   ├── models.py           # Data models and state definitions
│   └── schema.py           # Schema extraction and documentation
│
├── agents/                  # Agent implementations
│   ├── base.py             # Base agent class
│   ├── planner.py          # Natural language instruction generator
│   ├── sql_generator.py    # SQL query builder and executor
│   ├── validator.py        # Result validation agent
│   └── writer.py           # Response writing agent
│
├── prompts/                 # Jinja2 prompt templates
│   ├── planner.jinja       # Business analysis prompts
│   ├── sql_generator.jinja # SQL generation prompts
│   ├── validator.jinja     # Validation prompts
│   └── writer.jinja        # Response writing prompts
│
└── graph/                   # LangGraph workflow
    ├── nodes.py            # Node definitions
    └── workflow.py         # Workflow orchestration
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

2. Edit `.env` and add your API key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

## Usage

### Interactive Mode

```bash
python run_chatbot.py
```

### Single Question Mode

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

# Get full details including the planner's instructions and SQL
import asyncio
result = asyncio.run(chatbot.ask_with_details("List all accounts"))
print("Instructions:", result["query_plan"]["instructions"])
print("SQL:", result["sql_query"])
print("Response:", result["final_response"])
```

## Example Questions

- "How many doctors are in each territory?"
- "What are the top 10 HCPs by total prescriptions?"
- "Show me the prescription trend for GAZYVA by month"
- "Which sales reps have the most completed activities?"
- "What is the payor mix for Hospital accounts?"
- "List doctors with estimated market share above 10%"
- "Compare new vs total prescriptions by specialty"

## LLM Providers

### OpenAI
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-key-here
```

### Azure OpenAI (Recommended for Enterprise)
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
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Ollama (local)
```bash
uv pip install langchain-ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
```
