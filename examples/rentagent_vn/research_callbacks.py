"""Callbacks for area research progress and result events."""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from examples.rentagent_vn.api.research_broker import ResearchEvent, research_broker
from examples.rentagent_vn.db import queries
from langclaw import Langclaw
from langclaw.bus.base import InboundMessage


async def research_streaming_url_callback(
    app: Langclaw,
    research_id: str,
    listing_id: str,
    campaign_id: str,
    streaming_url: str,
    channel_context: dict[str, Any],
) -> None:
    """Called when TinyFish provides a streaming URL for live browser viewing."""
    logger.info(
        "Research {} streaming URL received: {}",
        research_id,
        streaming_url,
    )
    research_broker.publish(
        campaign_id,
        ResearchEvent(
            type="streaming_url",
            research_id=research_id,
            data={
                "listing_id": listing_id,
                "browser_url": streaming_url,
            },
            timestamp=time.monotonic(),
        ),
    )


async def research_progress_callback(
    app: Langclaw,
    research_id: str,
    listing_id: str,
    campaign_id: str,
    step: str,
    detail: str,
    channel_context: dict[str, Any],
) -> None:
    """Called when TinyFish reports progress on a research job."""
    research_broker.publish(
        campaign_id,
        ResearchEvent(
            type="progress",
            research_id=research_id,
            data={
                "listing_id": listing_id,
                "step": step,
                "detail": detail,
            },
            timestamp=time.monotonic(),
        ),
    )

    bus = app.get_bus()
    if bus is None:
        return

    await bus.publish(
        InboundMessage(
            channel=channel_context.get("channel", ""),
            user_id=channel_context.get("user_id", ""),
            context_id=channel_context.get("context_id", ""),
            chat_id=channel_context.get("chat_id", ""),
            content=f"Researching: {detail}",
            origin="area_research",
            to="channel",
            metadata={"research_id": research_id},
        )
    )


async def research_result_callback(
    app: Langclaw,
    research_id: str,
    listing_id: str,
    campaign_id: str,
    overall_score: float,
    verdict: str,
    channel_context: dict[str, Any],
) -> None:
    """Called when a research job completes successfully."""
    research_broker.publish(
        campaign_id,
        ResearchEvent(
            type="completed",
            research_id=research_id,
            data={
                "listing_id": listing_id,
                "overall_score": overall_score,
                "verdict": verdict,
            },
            timestamp=time.monotonic(),
        ),
    )
    research_broker.decrement_active(campaign_id)

    await queries.add_activity(
        campaign_id,
        "research_complete",
        f"Area research completed — score {overall_score:.1f}/10",
        metadata={
            "research_id": research_id,
            "listing_id": listing_id,
            "overall_score": overall_score,
        },
    )

    logger.info(
        "Research {} completed — score {:.1f}/10",
        research_id,
        overall_score,
    )


async def research_error_callback(
    app: Langclaw,
    research_id: str,
    listing_id: str,
    campaign_id: str,
    error_message: str,
    channel_context: dict[str, Any],
) -> None:
    """Called when a research job fails."""
    research_broker.publish(
        campaign_id,
        ResearchEvent(
            type="failed",
            research_id=research_id,
            data={
                "listing_id": listing_id,
                "error": error_message,
            },
            timestamp=time.monotonic(),
        ),
    )
    research_broker.decrement_active(campaign_id)

    await queries.add_activity(
        campaign_id,
        "research_error",
        f"Area research failed: {error_message}",
        metadata={
            "research_id": research_id,
            "listing_id": listing_id,
        },
    )

    logger.error("Research {} failed: {}", research_id, error_message)
