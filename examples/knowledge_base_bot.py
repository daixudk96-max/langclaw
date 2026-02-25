"""
Knowledge Base Bot — a multi-channel assistant that answers questions
using web search, tracks token usage, and blocks off-topic requests.

Demonstrates
------------
- ``@app.tool()``           — custom tool (company knowledge base lookup)
- ``app.register_tool()``   — plug in existing LangChain community tools
- ``app.add_middleware()``   — custom LangChain middleware (token-usage logger)
- ``@app.command()``        — fast ``/usage`` command (bypasses the LLM)
- ``app.role()``            — RBAC: admins get all tools, members are scoped

Run
---
1. Copy ``.env.example`` to ``.env`` and fill in at least one LLM provider key
   and one channel token.
2. ``pip install 'langclaw[telegram]' duckduckgo-search``
3. ``python examples/knowledge_base_bot.py``
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime
from loguru import logger

from langclaw import Langclaw
from langclaw.gateway.commands import CommandContext

app = Langclaw()

# ---------------------------------------------------------------------------
# Custom tool — company knowledge base (simulated)
# ---------------------------------------------------------------------------

KB: dict[str, str] = {
    "refund": (
        "Refund policy: Full refund within 30 days of purchase. "
        "After 30 days, store credit only. Contact support@example.com."
    ),
    "shipping": (
        "Standard shipping: 5-7 business days. "
        "Express: 1-2 business days ($12.99). Free shipping over $50."
    ),
    "hours": "Support hours: Mon-Fri 9 AM - 6 PM EST. Closed weekends.",
    "returns": (
        "Returns accepted within 30 days. Item must be unused and in "
        "original packaging. Start a return at example.com/returns."
    ),
}


@app.tool()
async def lookup_policy(
    query: Literal["refund", "shipping", "hours", "returns"],
) -> str:
    """Search the company knowledge base for policy and support info.

    Args:
        query: A keyword or topic to look up (e.g. "refund", "shipping").

    Returns:
        The matching knowledge base entry, or a not-found message.
    """
    key = query.strip().lower()
    for kb_key, answer in KB.items():
        if kb_key in key or key in kb_key:
            return answer
    return f"No knowledge base entry found for '{query}'. Try: {', '.join(KB)}."


# ---------------------------------------------------------------------------
# Register existing LangChain community tools
# ---------------------------------------------------------------------------

try:
    from langchain_community.tools import DuckDuckGoSearchResults

    ddg = DuckDuckGoSearchResults(
        name="web_search",
        description="Search the web for recent information not in the knowledge base.",
        num_results=3,
    )
    app.register_tool(ddg)
    logger.info("DuckDuckGo search tool registered")
except ImportError:
    logger.info(
        "langchain-community not installed — web search skipped. "
        "Install with: pip install langchain-community duckduckgo-search"
    )

# ---------------------------------------------------------------------------
# Custom middleware — token-usage tracker (LangChain AgentMiddleware)
# ---------------------------------------------------------------------------

_usage_log: dict[str, dict[str, int]] = defaultdict(
    lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0}
)


class UsageTrackerMiddleware(AgentMiddleware):
    """Track per-user model call counts and token usage.

    Uses LangChain's ``wrap_model_call`` hook to intercept every
    model invocation, record stats, and pass through transparently.

    Channel context is read from ``runtime.context`` — a
    ``LangclawContext`` instance that langclaw always injects.
    """

    @staticmethod
    def _get_user_id(request: ModelRequest) -> str:
        ctx = getattr(request.runtime, "context", None)
        return ctx.user_id if ctx else "unknown"

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        response = await handler(request)

        user_id = self._get_user_id(request)
        _usage_log[user_id]["calls"] += 1

        usage = getattr(response, "usage_metadata", None)
        if usage:
            _usage_log[user_id]["input_tokens"] += getattr(usage, "input_tokens", 0)
            _usage_log[user_id]["output_tokens"] += getattr(usage, "output_tokens", 0)
        logger.debug("Usage for {}: {}", user_id, dict(_usage_log[user_id]))

        return response

    def before_agent(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """Log each agent invocation with a timestamp."""
        ctx = getattr(runtime, "context", None)
        user = ctx.user_id if ctx else "?"
        logger.info(
            "[{}] Agent invoked by user {} ({} messages)",
            datetime.now(UTC).strftime("%H:%M:%S"),
            user,
            len(state.get("messages", [])),
        )
        return None


app.add_middleware(UsageTrackerMiddleware())


# ---------------------------------------------------------------------------
# Custom command — show token usage stats (no LLM call)
# ---------------------------------------------------------------------------


@app.command("usage", description="show your token usage stats")
async def usage_cmd(ctx: CommandContext) -> str:
    stats = _usage_log.get(ctx.user_id)
    if not stats or stats["calls"] == 0:
        return "No usage recorded yet. Send a message first!"
    return (
        f"Your usage stats:\n"
        f"  Model calls:   {stats['calls']}\n"
        f"  Input tokens:  {stats['input_tokens']}\n"
        f"  Output tokens: {stats['output_tokens']}"
    )


# ---------------------------------------------------------------------------
# RBAC — admins get all tools, members get KB + search only
# ---------------------------------------------------------------------------

app.role("admin", tools=["*"])
app.role("member", tools=["lookup_knowledge_base", "web_search"])


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run()
