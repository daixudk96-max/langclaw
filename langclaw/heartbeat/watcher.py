"""
Heartbeat — event-driven / condition-based proactive agent wake-up.

Unlike cron (time-driven), heartbeat conditions are checked on a polling
interval and fire only when a condition's check() returns a non-None string.

Example use-cases:
  - Market alerts (price threshold crossed)
  - Queue depth threshold
  - Service health degradation
  - Custom event streams

All fired messages flow through the same bus → agent pipeline as channel
and cron messages. ``metadata["source"] == "heartbeat"`` identifies them.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langclaw.bus.base import BaseMessageBus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Condition base class
# ---------------------------------------------------------------------------


class HeartbeatCondition(ABC):
    """
    Abstract condition checked on each heartbeat interval.

    Implement ``check()`` to return a message string when the condition
    warrants waking up the agent, or ``None`` to skip.
    """

    name: str = "unnamed"
    """Human-readable identifier for logging."""

    @abstractmethod
    async def check(self) -> str | None:
        """
        Evaluate the condition.

        Returns:
            A non-empty string (the message to send to the agent) if the
            condition is met, or ``None`` if nothing should happen.
        """
        ...


# ---------------------------------------------------------------------------
# Target descriptor
# ---------------------------------------------------------------------------


@dataclass
class HeartbeatTarget:
    """Describes where a triggered heartbeat message should be routed."""

    channel: str
    user_id: str
    context_id: str = "default"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class HeartbeatManager:
    """
    Polls registered :class:`HeartbeatCondition` instances and publishes to
    the bus whenever one fires.

    Args:
        bus:             MessageBus to publish triggered messages into.
        interval:        Polling interval in seconds. Default 60.
        conditions:      Initial list of (condition, target) pairs.
    """

    def __init__(
        self,
        bus: BaseMessageBus,
        interval: int = 60,
        conditions: list[tuple[HeartbeatCondition, HeartbeatTarget]] | None = None,
    ) -> None:
        self._bus = bus
        self._interval = interval
        self._conditions: list[tuple[HeartbeatCondition, HeartbeatTarget]] = (
            list(conditions) if conditions else []
        )
        self._running = False
        self._task: asyncio.Task | None = None

    def add_condition(
        self, condition: HeartbeatCondition, target: HeartbeatTarget
    ) -> None:
        """Register a new condition + routing target at runtime."""
        self._conditions.append((condition, target))

    def remove_condition(self, name: str) -> bool:
        """Remove all conditions with the given name. Returns True if any removed."""
        before = len(self._conditions)
        self._conditions = [(c, t) for c, t in self._conditions if c.name != name]
        return len(self._conditions) < before

    async def start(self) -> None:
        """Start the polling loop as a background asyncio task."""
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="heartbeat_loop")
        logger.info(
            "HeartbeatManager started (interval=%ds, conditions=%d).",
            self._interval,
            len(self._conditions),
        )

    async def stop(self) -> None:
        """Cancel the polling loop gracefully."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            await self._tick()
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    async def _tick(self) -> None:
        """Evaluate all conditions and publish those that fire."""
        from langclaw.bus.base import InboundMessage

        for condition, target in self._conditions:
            try:
                result = await condition.check()
            except Exception:
                logger.exception(
                    f"HeartbeatCondition '{condition.name}' raised an exception."
                )
                continue

            if result:
                logger.debug(
                    f"HeartbeatCondition '{condition.name}' fired: {result[:80]}"
                )
                await self._bus.publish(
                    InboundMessage(
                        channel=target.channel,
                        user_id=target.user_id,
                        context_id=target.context_id,
                        content=result,
                        metadata={
                            "source": "heartbeat",
                            "condition": condition.name,
                        },
                    )
                )
