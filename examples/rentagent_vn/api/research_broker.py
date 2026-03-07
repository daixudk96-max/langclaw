"""In-memory event broker for real-time area research progress streaming.

Same pattern as scan_broker.py but scoped to campaign-level research streams.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class ResearchEvent:
    """A single event in the research stream."""

    type: str  # started | progress | completed | failed | done
    research_id: str | None
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class _ResearchStreamState:
    """Internal state for a campaign's research event stream."""

    events: list[ResearchEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[ResearchEvent | None]] = field(default_factory=list)
    active_count: int = 0


class ResearchEventBroker:
    """In-memory event broker with buffered pub/sub for research events.

    Scoped to campaign_id — all research jobs for a campaign share one stream.
    """

    def __init__(self, cleanup_ttl_seconds: float = 300.0) -> None:
        self._streams: dict[str, _ResearchStreamState] = {}
        self._cleanup_ttl = cleanup_ttl_seconds

    def publish(self, campaign_id: str, event: ResearchEvent) -> None:
        """Publish an event to all subscribers of a campaign's research stream."""
        state = self._streams.setdefault(campaign_id, _ResearchStreamState())
        state.events.append(event)

        for queue in state.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full for campaign {} research, dropping event",
                    campaign_id,
                )

        if event.type == "done":
            for queue in state.subscribers:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            self._schedule_cleanup(campaign_id)

    def increment_active(self, campaign_id: str) -> None:
        """Track that a new research job started for this campaign."""
        state = self._streams.setdefault(campaign_id, _ResearchStreamState())
        state.active_count += 1

    def decrement_active(self, campaign_id: str) -> None:
        """Track that a research job finished. Sends 'done' when all complete."""
        state = self._streams.get(campaign_id)
        if state is None:
            return
        state.active_count = max(0, state.active_count - 1)
        if state.active_count == 0:
            self.publish(
                campaign_id,
                ResearchEvent(type="done", research_id=None, data={}),
            )

    async def subscribe(self, campaign_id: str) -> AsyncIterator[ResearchEvent]:
        """Subscribe to research events for a campaign.

        Replays buffered events, then streams new ones.
        """
        state = self._streams.get(campaign_id)
        if state is None:
            state = self._streams.setdefault(campaign_id, _ResearchStreamState())

        queue: asyncio.Queue[ResearchEvent | None] = asyncio.Queue(maxsize=1000)
        state.subscribers.append(queue)

        try:
            for event in list(state.events):
                yield event

            if state.active_count == 0 and state.events:
                return

            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)

    def _schedule_cleanup(self, campaign_id: str) -> None:
        async def _cleanup() -> None:
            await asyncio.sleep(self._cleanup_ttl)
            self.cleanup(campaign_id)

        try:
            asyncio.create_task(_cleanup(), name=f"research-cleanup-{campaign_id}")
        except RuntimeError:
            pass

    def cleanup(self, campaign_id: str) -> None:
        removed = self._streams.pop(campaign_id, None)
        if removed:
            logger.debug("Cleaned up research state for campaign {}", campaign_id)


# Module-level singleton
research_broker = ResearchEventBroker()
