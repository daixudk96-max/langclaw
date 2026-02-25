# Examples

Runnable examples that demonstrate the core langclaw API.

## Prerequisites

```bash
pip install langclaw[telegram]   # or langclaw[discord], langclaw[websocket]
langclaw init                    # scaffold ~/.langclaw/ with config + workspace
```

Copy `.env.example` to `.env` in your project root and fill in:

- At least one LLM provider key (e.g. `LANGCLAW__PROVIDERS__ANTHROPIC__API_KEY`)
- At least one channel token (e.g. `LANGCLAW__CHANNELS__TELEGRAM__TOKEN`)

## Research Assistant

A stock-price bot with scheduled digest reports.

**What it shows:** `@app.tool()`, `@app.command()`, `app.role()`, lifecycle hooks, cron-ready design.

```bash
python examples/research_assistant.py
```

Then message the bot:

- *"What's the price of NVDA?"* — calls the custom `get_stock_price` tool
- *"Search the web for AI chip market news"* — uses built-in `web_search`
- *"Schedule a daily market summary at 9 AM"* — creates a cron job via the agent
- `/watchlist` — instant price snapshot, no LLM involved

## Knowledge Base Bot

A support assistant with custom middleware and LangChain community tools.

**What it shows:** `@app.tool()`, `app.register_tool()` (LangChain DuckDuckGo), `app.add_middleware()` (token-usage tracker), `@app.command()`, RBAC.

```bash
pip install duckduckgo-search
python examples/knowledge_base_bot.py
```

Then message the bot:

- *"What is your refund policy?"* — calls the custom `lookup_knowledge_base` tool
- *"Search the web for Python 3.13 release notes"* — uses the registered DuckDuckGo tool
- *"How do I return an item?"* — multi-tool reasoning (KB + web fallback)
- `/usage` — show your token usage stats, no LLM involved
