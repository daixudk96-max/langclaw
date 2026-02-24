"""Channel-agnostic command router.

Commands (``/start``, ``/reset``, ``/help``, ``/cron``, …) are handled here
instead of inside each channel implementation.  Channels detect commands using
platform conventions (PTB ``CommandHandler`` for Telegram, slash commands for
Discord/Slack, etc.) and delegate execution to the shared ``CommandRouter``.

Commands bypass the message bus entirely — they are fast system operations
that should not pollute conversation history or invoke the LLM.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langclaw.cron.scheduler import CronManager
    from langclaw.session.manager import SessionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CommandContext:
    """Everything a command handler needs to execute."""

    channel: str
    user_id: str
    context_id: str
    chat_id: str
    args: list[str] = field(default_factory=list)
    display_name: str = ""


@dataclass
class CommandEntry:
    """A registered command."""

    name: str
    handler: Callable[[CommandContext], Awaitable[str]]
    description: str


# ---------------------------------------------------------------------------
# Built-in command handlers
# ---------------------------------------------------------------------------


async def _cmd_start(ctx: CommandContext) -> str:
    name = ctx.display_name or "there"
    return (
        f"Hi {name}! I'm powered by langclaw.\n\n"
        "Send me a message to get started.\n"
        "Use /reset to start a fresh conversation."
    )


async def _cmd_reset(ctx: CommandContext) -> str:
    router = _ACTIVE_ROUTER
    if router is None or router._session_manager is None:
        return "Reset is not available right now."
    await router._session_manager.delete_thread(
        channel=ctx.channel,
        user_id=ctx.user_id,
        context_id=ctx.context_id,
    )
    return "Conversation reset. Starting fresh!"


async def _cmd_help(ctx: CommandContext) -> str:
    router = _ACTIVE_ROUTER
    if router is None:
        return "Help is not available right now."
    lines: list[str] = []
    for entry in router.list_commands():
        lines.append(f"/{entry.name}  — {entry.description}")
    return "\n".join(lines) or "No commands registered."


async def _cmd_cron(ctx: CommandContext) -> str:
    router = _ACTIVE_ROUTER
    if router is None or router._cron_manager is None:
        return "Cron is not available."

    cron_mgr = router._cron_manager
    sub = ctx.args[0] if ctx.args else "list"

    if sub == "list":
        jobs = await cron_mgr.list_jobs(
            channel=ctx.channel or None,
            user_id=ctx.user_id or None,
        )
        if not jobs:
            return "No active cron jobs."
        lines = ["Active cron jobs:"]
        for j in jobs:
            lines.append(f"  [{j.id}] {j.name!r} — {j.schedule}")
        return "\n".join(lines)

    if sub == "remove":
        if len(ctx.args) < 2:
            return "Usage: /cron remove <job_id>"
        job_id = ctx.args[1]
        removed = await cron_mgr.remove_job(
            job_id,
            channel=ctx.channel or None,
            user_id=ctx.user_id or None,
        )
        if removed:
            return f"Job {job_id} removed."
        return f"Job {job_id} not found."

    return "Usage: /cron [list | remove <job_id>]"


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ACTIVE_ROUTER: CommandRouter | None = None


class CommandRouter:
    """Registry of channel-agnostic commands.

    Created by ``GatewayManager`` and shared with every channel via
    ``BaseChannel.set_command_router()``.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        cron_manager: CronManager | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._cron_manager = cron_manager
        self._commands: dict[str, CommandEntry] = {}
        self._register_builtins()

        global _ACTIVE_ROUTER  # noqa: PLW0603
        _ACTIVE_ROUTER = self

    def _register_builtins(self) -> None:
        self.register("start", _cmd_start, "say hello")
        self.register("reset", _cmd_reset, "clear conversation history")
        self.register("help", _cmd_help, "show this message")
        if self._cron_manager is not None:
            self.register("cron", _cmd_cron, "list or remove cron jobs")

    def register(
        self,
        name: str,
        handler: Callable[[CommandContext], Awaitable[str]],
        description: str,
    ) -> None:
        """Register a command handler."""
        self._commands[name] = CommandEntry(
            name=name,
            handler=handler,
            description=description,
        )

    async def dispatch(
        self,
        name: str,
        ctx: CommandContext,
    ) -> str:
        """Execute a command by name. Returns response text."""
        entry = self._commands.get(name)
        if entry is None:
            return f"Unknown command: /{name}"
        try:
            return await entry.handler(ctx)
        except Exception:
            logger.exception("Command /%s failed", name)
            return f"Command /{name} failed. Please try again."

    def list_commands(self) -> list[CommandEntry]:
        """Return all registered commands in insertion order."""
        return list(self._commands.values())


__all__ = ["CommandContext", "CommandEntry", "CommandRouter"]
