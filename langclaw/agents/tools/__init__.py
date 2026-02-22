"""Built-in agent tools for langclaw."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langclaw.agents.tools.web_fetch import web_fetch
from langclaw.agents.tools.web_search import make_search_tool

if TYPE_CHECKING:
    from langclaw.config.schema import LangclawConfig

# Map each backend to the config field that holds its API key.
# duckduckgo needs no key, so it maps to an empty string constant.
_BACKEND_KEY_FIELD: dict[str, str] = {
    "brave": "brave_api_key",
    "tavily": "tavily_api_key",
    "duckduckgo": "",
}


def build_web_tools(config: LangclawConfig) -> list[Any]:
    """Return web-related tools enabled by the current config.

    The search tool is added when either:
    - the configured backend requires no API key (``"duckduckgo"``), or
    - the corresponding API key field in ``config.tools`` is non-empty.

    ``web_fetch`` is always included as it needs no credentials.
    """
    tools: list[Any] = []

    tools_cfg = config.tools
    backend = tools_cfg.search_backend
    key_field = _BACKEND_KEY_FIELD.get(backend, "")

    if key_field == "":
        # No key required (e.g. duckduckgo)
        tools.append(make_search_tool(backend))
    else:
        api_key: str = getattr(tools_cfg, key_field, "")
        if api_key:
            tools.append(make_search_tool(backend, api_key=api_key))

    tools.append(web_fetch)

    return tools


__all__ = ["build_web_tools", "web_fetch", "make_search_tool"]
