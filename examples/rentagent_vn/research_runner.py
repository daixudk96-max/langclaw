"""Background runner for area research jobs using TinyFish + LLM scoring."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from loguru import logger

from examples.rentagent_vn.api.research_broker import ResearchEvent, research_broker
from examples.rentagent_vn.db import queries
from examples.rentagent_vn.models import RESEARCH_CRITERIA_LABELS, ResearchScores
from examples.rentagent_vn.prompts import RESEARCH_SCORING_PROMPT, build_research_goal
from examples.rentagent_vn.tinyfish.client import TinyFishClient
from langclaw import Langclaw

ProgressCallback = Callable[
    [Langclaw, str, str, str, str, str, dict[str, Any]],
    Awaitable[None],
]
ResultCallback = Callable[
    [Langclaw, str, str, str, float, str, dict[str, Any]],
    Awaitable[None],
]
ErrorCallback = Callable[
    [Langclaw, str, str, str, str, dict[str, Any]],
    Awaitable[None],
]


class BackgroundResearchRunner:
    """Runs area research jobs in the background using TinyFish for Google Maps
    exploration and LLM for scoring observations."""

    def __init__(
        self,
        app: Langclaw,
        tinyfish_client: TinyFishClient,
        *,
        progress_callback: ProgressCallback | None = None,
        result_callback: ResultCallback | None = None,
        error_callback: ErrorCallback | None = None,
    ) -> None:
        self._app = app
        self._tinyfish_client = tinyfish_client
        self._progress_callback = progress_callback
        self._result_callback = result_callback
        self._error_callback = error_callback
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(
        self,
        research_id: str,
        listing_id: str,
        address: str,
        criteria: list[str],
        campaign_id: str,
        channel_context: dict[str, Any],
    ) -> str:
        """Start a research job in the background. Returns job_id."""
        job_id = uuid4().hex[:12]
        research_broker.increment_active(campaign_id)

        task = asyncio.create_task(
            self._run(
                job_id,
                research_id,
                listing_id,
                address,
                criteria,
                campaign_id,
                channel_context,
            ),
            name=f"research-{research_id}",
        )
        self._tasks[job_id] = task
        logger.info(
            "Research {} started for listing {} at '{}'",
            research_id,
            listing_id,
            address,
        )
        return job_id

    async def _run(
        self,
        job_id: str,
        research_id: str,
        listing_id: str,
        address: str,
        criteria: list[str],
        campaign_id: str,
        channel_context: dict[str, Any],
    ) -> None:
        try:
            # 1. Mark as running
            await queries.update_research_status(
                research_id,
                "running",
                tinyfish_job_id=job_id,
            )

            # 2. Publish started event
            import time

            research_broker.publish(
                campaign_id,
                ResearchEvent(
                    type="started",
                    research_id=research_id,
                    data={"listing_id": listing_id, "address": address},
                    timestamp=time.monotonic(),
                ),
            )

            # 3. Build goal and run TinyFish
            goal = build_research_goal(address, criteria)
            raw_result: dict[str, Any] = {}

            async for event in self._tinyfish_client.stream_run(
                "https://maps.google.com",
                goal,
            ):
                if event.type == "PROGRESS" and self._progress_callback:
                    await self._progress_callback(
                        self._app,
                        research_id,
                        listing_id,
                        campaign_id,
                        event.purpose or "researching",
                        event.purpose or "",
                        channel_context,
                    )
                elif event.type == "COMPLETE":
                    raw_result = event.result_json or {}
                    logger.info("TinyFish research completed for {}", research_id)
                elif event.type == "ERROR":
                    raise RuntimeError(event.message or "TinyFish research failed")

            if not raw_result:
                raise RuntimeError("TinyFish returned empty result")

            # 4. Score the raw observations with LLM
            criteria_labels = [
                f"- {key}: {RESEARCH_CRITERIA_LABELS.get(key, key)}" for key in criteria
            ]
            scoring_prompt = RESEARCH_SCORING_PROMPT.format(
                raw_observations=json.dumps(raw_result, ensure_ascii=False, indent=2),
                criteria_list="\n".join(criteria_labels),
            )

            scores = await self._call_llm_for_scoring(scoring_prompt)

            # 5. Save results
            # TODO: what is verdict?
            await queries.complete_research(
                research_id=research_id,
                scores=scores.model_dump(),
                result=raw_result,
                verdict=scores.verdict,
                overall_score=scores.overall,
                street_view_urls=self._extract_street_view_urls(raw_result),
            )
            await queries.link_research_to_listing(listing_id, research_id)

            # 6. Notify via callback
            if self._result_callback:
                await self._result_callback(
                    self._app,
                    research_id,
                    listing_id,
                    campaign_id,
                    scores.overall,
                    scores.verdict,
                    channel_context,
                )

        except Exception as exc:
            logger.exception("Research {} failed", research_id)
            error_msg = str(exc)
            await queries.update_research_status(
                research_id,
                "failed",
                error_message=error_msg,
            )
            if self._error_callback:
                await self._error_callback(
                    self._app,
                    research_id,
                    listing_id,
                    campaign_id,
                    error_msg,
                    channel_context,
                )
        finally:
            self._tasks.pop(job_id, None)

    async def _call_llm_for_scoring(self, prompt: str) -> ResearchScores:
        """Call the LLM to score raw research observations."""
        from langchain.chat_models import init_chat_model

        cfg = self._app.config.agents
        model = init_chat_model(cfg.model, **cfg.model_kwargs)
        model = model.with_structured_output(ResearchScores)

        research_scores = await model.ainvoke(prompt)
        return research_scores

    def _extract_street_view_urls(self, raw_result: dict[str, Any]) -> list[str]:
        """Extract any Street View screenshot URLs from TinyFish result."""
        urls: list[str] = []
        assessment = raw_result.get("neighbourhood_assessment", raw_result)
        street_view = assessment.get("street_view", {})
        if isinstance(street_view, dict):
            for key in ("screenshots", "images", "urls"):
                val = street_view.get(key)
                if isinstance(val, list):
                    urls.extend(str(u) for u in val if u)
        return urls
