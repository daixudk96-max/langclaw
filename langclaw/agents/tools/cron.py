"""Cron tool — allows the agent to schedule, list, and remove recurring jobs.

The tool reads channel context (channel, user_id, context_id) from the
``RunnableConfig`` injected by ``ChannelContextMiddleware``, so jobs are
automatically routed back to the conversation that created them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, InjectedToolArg, tool
from loguru import logger

from langclaw.cron.utils import make_cron_context_id

if TYPE_CHECKING:
    from langclaw.cron.scheduler import CronManager

CRON_TOOL_DOC = """Schedule, list, or remove recurring jobs.

    HOW IT WORKS
    ------------
    When a job fires, ``message`` is injected into the agent pipeline as a
    new prompt — exactly as if the user had typed it at that moment. You (the
    agent) wake up, process the prompt with full access to all tools (web
    search, web fetch, memory, etc.), and send the result to the user.
    Write ``message`` as a clear instruction to yourself, not as text for the
    user. The user only sees your final reply.
    Keep it short and executable:
      - state the task, output format, and constraints
      - include defaults for optional choices
      - avoid open questions unless truly required to run

    TIMEZONE
    --------
    The active timezone is {timezone}.
    Cron expressions are interpreted in {timezone}.
    Always express times in {timezone} when building a cron_expr.
    Interval-based schedules (every_seconds) are timezone-independent.

    Actions
    -------
    ``add``    — create a new scheduled job.
    ``list``   — list all active jobs.
    ``remove`` — delete a job by ID.

    Args:
        action:        One of ``'add'``, ``'list'``, or ``'remove'``.
        type:          One of ``'reminder'``, ``'task'``.
                       Required for ``add``.
                       Type ``'reminder'`` includes recent conversation history.
                       Type ``'task'`` includes only the scheduled message.
        message:       Prompt injected into the agent at fire time.
                       Required for ``add``.
                       Write task instructions only.
                       Do NOT include schedule/timezone or recipient/user info;
                       scheduling + routing are already handled by cron context.
        every_seconds: Repeat interval in seconds (e.g. 3600 = every hour).
                       Mutually exclusive with ``cron_expr``.
        cron_expr:     Standard 5-field cron expression in {timezone}.
                       e.g. ``'0 9 * * *'`` = daily at 09:00 {timezone}.
                       Mutually exclusive with ``every_seconds``.
        job_id:        ID of the job to remove. Required for ``remove``.

    Examples
    --------
    Simple reminder every 20 minutes::

        cron(action='add', message='Tell the user to take a break.',\
             type='reminder', every_seconds=1200)

    Daily task at 9 AM using live web tools::

        cron(action='add',
             message='Search the web for the latest AI news and summarize the top
                      3 stories for my morning reading.',
             type='task',
             cron_expr='0 9 * * *')

    Daily quote task (task-only message; no time/user in message)::

        cron(action='add',
             message='Pick one movie or anime quote matching today mood from
                      local weather + weekday/weekend. Output: quote, 1-2
                      sentence fit explanation, source link. Add SPOILER WARNING
                      only for major twists/final-act reveals. Avoid explicit
                      NSFW.',
             type='task',
             cron_expr='30 13 * * *')

    List active jobs::

        cron(action='list')

    Remove a job::

        cron(action='remove', job_id='<job_id>')
"""


def make_cron_tool(cron_manager: CronManager, timezone: str = "UTC") -> BaseTool:
    """Return a ``cron`` tool wired to *cron_manager*.

    The returned tool is a single LangChain ``BaseTool`` that exposes three
    actions — ``add``, ``list``, and ``remove`` — so the LLM can manage
    scheduled jobs through natural language.

    Channel context (channel name, user_id, context_id) is read from the
    injected ``RunnableConfig`` rather than mutated state, keeping the tool
    stateless and thread-safe.

    The ``timezone`` is embedded into the tool's schema description so the
    LLM always knows which timezone to use when constructing cron expressions.

    Args:
        cron_manager: A running ``CronManager`` instance owned by the gateway.
        timezone:     Timezone string from ``config.cron.timezone``
                      (e.g. ``"Europe/Amsterdam"``). Baked into the tool
                      description so the LLM reasons in the correct timezone.

    Returns:
        A LangChain ``BaseTool`` named ``"cron"``.
    """

    async def cron(
        action: Literal["add", "list", "remove"],
        type: Literal["reminder", "task"] | None = None,
        message: str | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        job_id: str | None = None,
        *,
        config: Annotated[RunnableConfig, InjectedToolArg],
    ) -> str:
        # ── Resolve channel context from RunnableConfig ────────────────────
        configurable = (config or {}).get("configurable", {})
        ctx = configurable.get("channel_context", {})
        channel = ctx.get("channel", "")
        user_id = ctx.get("user_id", "")
        context_id = ctx.get("context_id", "default")
        chat_id = ctx.get("chat_id", user_id)

        # ── add ────────────────────────────────────────────────────────────
        if action == "add":
            if not type:
                return "Error: type is required for add. Use 'reminder' or 'task'."
            if not message:
                return "Error: message is required for add."
            if not channel or not user_id:
                return (
                    "Error: no session context (channel/user_id). "
                    "Make sure the gateway is running with cron enabled."
                )
            if every_seconds is None and cron_expr is None:
                return "Error: either every_seconds or cron_expr is required."

            name = f"{message[:40].strip()}..."
            # Tasks get their own isolated thread; reminders share the current one.
            effective_context_id = (
                context_id if type == "reminder" else make_cron_context_id()
            )
            try:
                job_id_new = await cron_manager.add_job(
                    name=name,
                    message=message,
                    channel=channel,
                    user_id=user_id,
                    context_id=effective_context_id,
                    chat_id=chat_id,
                    cron_expr=cron_expr,
                    every_seconds=every_seconds,
                )
            except Exception as exc:
                import traceback

                logger.error(f"cron add failed: {exc}\n{traceback.format_exc()}")
                return f"Error scheduling job: {exc}"

            schedule_desc = (
                f"every {every_seconds}s"
                if every_seconds is not None
                else f'cron "{cron_expr}"'
            )
            return (
                f"Job scheduled ({schedule_desc}).\n"
                f"Job ID: {job_id_new}\n"
                f"Message: {message}"
            )

        # ── list ───────────────────────────────────────────────────────────
        if action == "list":
            jobs = await cron_manager.list_jobs(
                channel=channel or None,
                user_id=user_id or None,
            )
            if not jobs:
                return "No active cron jobs."

            lines = ["Active cron jobs:"]
            for j in jobs:
                lines.append(f"  • [{j.id}] {j.name!r} — {j.schedule}")
            return "\n".join(lines)

        # ── remove ─────────────────────────────────────────────────────────
        if action == "remove":
            if not job_id:
                return "Error: job_id is required for remove."
            removed = await cron_manager.remove_job(
                job_id,
                channel=channel or None,
                user_id=user_id or None,
            )
            if removed:
                return f"Job {job_id} removed."
            return f"Job {job_id} not found."

        return f"Unknown action: {action!r}. Use 'add', 'list', or 'remove'."

    # Set the docstring before passing to tool() so the LLM-visible schema
    # includes the active timezone. tool() reads __doc__ at call time.
    cron.__doc__ = CRON_TOOL_DOC.format(timezone=timezone)

    return tool(cron)


__all__ = ["make_cron_tool"]
