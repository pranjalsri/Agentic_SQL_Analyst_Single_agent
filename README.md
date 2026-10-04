# Agentic SQL Analyst

An AI-powered SQL assistant built to turn natural-language business questions into safe Snowflake SQL, validate the query before execution, and return a concise human-readable answer.

This project combines LangGraph orchestration, Ollama-hosted LLMs, and Snowflake metadata inspection to create a lightweight "SQL analyst" agent that works directly against a database schema.

## Overview

The workflow is designed around a multi-step agent pipeline:

1. Curates the user's question for better clarity.
2. Pulls schema context from Snowflake using the configured database and schema.
3. Generates a read-only SQL statement from the prompt and schema details.
4. Uses a second LLM evaluation step to decide whether the SQL is safe to execute.
5. Executes the query against Snowflake.
6. Converts the result into a plain-English response for the user.

## Key capabilities

- Natural-language-to-SQL conversion
- Snowflake schema discovery and sample data context
- Safety checks to reject write operations and unsafe queries
- Read-only execution flow for analytical use cases
- Final answer generation in user-friendly language

## Tech stack

- Python 3.14+
- LangGraph
- LangChain + Ollama
- Snowflake Connector for Python
- Pydantic
- python-dotenv

## Repository structure

- `agents/sql_analyst.py` — main LangGraph-based SQL agent workflow
- `models/schema.py` — schemas used for state and judge validation
- `utils/database.py` — Snowflake connection and schema introspection helpers
- `utils/pick_llm.py` — LLM initialization using Ollama
- `schema_details.txt` — generated schema context used by the agent
- `src/` — project package scaffolding

## Prerequisites

Before running the project, make sure you have:

- Python 3.14 or later installed
- Ollama installed and running locally
- A valid Snowflake account, warehouse, database, and schema
- An LLM model available in Ollama (the project currently uses `qwen2.5-coder:7b` by default)

## Environment setup

Create a `.env` file in the project root with the required Snowflake and Ollama settings, for example:

```env
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5-coder:7b

SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=SYSADMIN
```

Then install dependencies:

```bash
uv sync
```

If you are not using `uv`, install the project dependencies with your preferred Python environment manager.

## Running the project

The main workflow is defined in `agents/sql_analyst.py`.

```bash
python agents/sql_analyst.py
```

This script runs a sample question through the graph and prints:

- the curated question
- the generated SQL query
- the SQL execution result
- the final natural-language answer

## Example use case

Example user questions:

- "What is the total balance by customer?"
- "Which accounts are suspended?"
- "Show the top 10 transactions by amount."
- "How many active customers are in the staging dataset?"

The agent converts these into Snowflake SQL and returns a business-friendly result.

## Safety model

The project is designed to execute only read-only SQL. The guard logic rejects queries that attempt to modify the database, including commands such as:

- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `ALTER`
- `CREATE`
- `TRUNCATE`

This ensures the agent is suitable for analytical and reporting workflows rather than destructive operations.

## Notes

- The schema details are loaded dynamically from Snowflake at runtime.
- The project uses the configured database/schema as the execution context.
- The SQL query is limited to a read-only `SELECT`/`WITH` pattern to maintain safe execution behavior.

## License

This project is currently provided as a local development project without a formal license file.
