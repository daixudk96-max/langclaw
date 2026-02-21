"""
CronManager — scheduled task engine backed by APScheduler v4.

Jobs publish InboundMessages to the bus on fire, so they flow through the
same agent pipeline as channel messages. The agent pipeline is source-agnostic;
it uses metadata["source"] == "cron" for any special handling.

Persistence: APScheduler v4 jobs are held in-memory by default. For
production persistence configure a SQLAlchemy data store (PostgreSQL, etc.)
via APScheduler's built-in facilities.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from langclaw.bus.base import BaseMessageBus, InboundMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job descriptor
# ---------------------------------------------------------------------------


@dataclass
class CronJob:
    id: str
    name: str
    message: str
    channel: str
    user_id: str
    context_id: str
    schedule: str
    """Either a cron expression (``"0 9 * * *"``) or ``"every:<seconds>"``."""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class CronManager:
    """
    Manages scheduled jobs that trigger agent invocations.

    Natural-language scheduling is handled by the agent itself via the
    ``schedule_task`` tool — the LLM parses "every morning at 9" and calls
    this manager with the resulting cron expression.

    Args:
        bus:      MessageBus to publish triggered messages into.
        timezone: Default timezone for cron expressions (e.g. ``"Europe/Amsterdam"``).
    """

    def __init__(self, bus: BaseMessageBus, timezone: str = "UTC") -> None:
        self._bus = bus
        self._timezone = timezone
        self._scheduler: object = None  # APScheduler AsyncScheduler
        self._jobs: dict[str, CronJob] = {}

    async def start(self) -> None:
        """Start the APScheduler AsyncScheduler."""
        try:
            from apscheduler import AsyncScheduler
            from apscheduler.datastores.memory import MemoryDataStore
            from apscheduler.eventbrokers.local import LocalEventBroker
        except ImportError as exc:
            raise ImportError(
                "CronManager requires apscheduler>=4. "
                "Install with: uv add 'apscheduler>=4'"
            ) from exc

        self._scheduler = AsyncScheduler(
            data_store=MemoryDataStore(),
            event_broker=LocalEventBroker(),
        )
        await self._scheduler.__aenter__()
        logger.info(f"CronManager started (timezone={self._timezone}).")

    async def stop(self) -> None:
        if self._scheduler is not None:
            await self._scheduler.__aexit__(None, None, None)
            self._scheduler = None

    async def add_job(
        self,
        name: str,
        message: str,
        channel: str,
        user_id: str,
        context_id: str = "default",
        cron_expr: str | None = None,
        every_seconds: int | None = None,
    ) -> str:
        """
        Schedule a job that fires a message into the agent pipeline.

        Args:
            name:          Human-readable label.
            message:       Text content to send as an InboundMessage.
            channel:       Target channel name (e.g. ``"telegram"``).
            user_id:       Target user ID on the channel.
            context_id:    Conversation context (default ``"default"``).
            cron_expr:     Standard 5-field cron expression (``"0 9 * * *"``).
            every_seconds: Interval in seconds (alternative to cron_expr).

        Returns:
            A stable job ID string.
        """
        if self._scheduler is None:
            raise RuntimeError("CronManager not started — call start() first.")
        if cron_expr is None and every_seconds is None:
            raise ValueError("Provide either cron_expr or every_seconds.")

        try:
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError as exc:
            raise ImportError("apscheduler>=4 required") from exc

        job_id = str(uuid.uuid4())
        trigger = (
            CronTrigger.from_crontab(cron_expr, timezone=self._timezone)
            if cron_expr
            else IntervalTrigger(seconds=every_seconds)
        )

        job = CronJob(
            id=job_id,
            name=name,
            message=message,
            channel=channel,
            user_id=user_id,
            context_id=context_id,
            schedule=cron_expr or f"every:{every_seconds}s",
        )
        self._jobs[job_id] = job

        await self._scheduler.add_schedule(
            self._fire,
            trigger,
            id=job_id,
            kwargs={
                "message": message,
                "channel": channel,
                "user_id": user_id,
                "context_id": context_id,
                "job_name": name,
            },
        )
        logger.info(
            f"Cron job '{name}' scheduled (id={job_id}, schedule={job.schedule})."
        )
        return job_id

    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job. Returns True if it existed."""
        if self._scheduler is None:
            return False
        try:
            await self._scheduler.remove_schedule(job_id)
            self._jobs.pop(job_id, None)
            return True
        except Exception:
            return False

    def list_jobs(self) -> list[CronJob]:
        """Return all registered cron jobs."""
        return list(self._jobs.values())

    # ------------------------------------------------------------------
    # Internal fire callback
    # ------------------------------------------------------------------

    async def _fire(
        self,
        message: str,
        channel: str,
        user_id: str,
        context_id: str,
        job_name: str,
    ) -> None:
        logger.debug(f"Cron job '{job_name}' fired → publishing to bus.")
        await self._bus.publish(
            InboundMessage(
                channel=channel,
                user_id=user_id,
                context_id=context_id,
                content=message,
                metadata={
                    "source": "cron",
                    "job_name": job_name,
                },
            )
        )
