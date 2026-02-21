"""
GatewayManager — orchestrates channels, the message bus, and the agent loop.

Architecture:
  - All enabled channels run as sibling tasks inside asyncio.TaskGroup
  - A single _bus_worker task reads from the bus and dispatches agent calls
  - Each message is handled concurrently (one asyncio.Task per message)
  - Streaming agent chunks are forwarded to the originating channel in real time
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from langclaw.bus.base import BaseMessageBus, InboundMessage, OutboundMessage
from langclaw.checkpointer.base import BaseCheckpointerBackend
from langclaw.config.schema import LangclawConfig
from langclaw.gateway.base import BaseChannel
from langclaw.session.manager import SessionManager


class GatewayManager:
    """
    Central orchestrator for the multi-channel gateway.

    Responsibilities:
    - Start/stop all registered channels (via asyncio.TaskGroup)
    - Run the bus worker that feeds messages to the agent
    - Handle per-message agent streaming back to the originating channel

    Args:
        config:      Loaded LangclawConfig.
        bus:         Initialised BaseMessageBus.
        checkpointer_backend: Initialised BaseCheckpointerBackend (in context).
        agent:       Compiled LangGraph agent (from create_claw_agent).
        channels:    List of BaseChannel implementations to manage.
    """

    def __init__(
        self,
        config: LangclawConfig,
        bus: BaseMessageBus,
        checkpointer_backend: BaseCheckpointerBackend,
        agent: CompiledStateGraph,
        channels: list[BaseChannel],
    ) -> None:
        self._config = config
        self._bus = bus
        self._checkpointer_backend = checkpointer_backend
        self._agent = agent
        self._channels = [ch for ch in channels if ch.is_enabled()]
        self._sessions = SessionManager()
        self._channel_map: dict[str, BaseChannel] = {
            ch.name: ch for ch in self._channels
        }

    async def run(self) -> None:
        """
        Start all channels and the bus worker.

        Uses Python 3.11+ ``asyncio.TaskGroup`` for structured concurrency:
        if any channel task raises an unhandled exception the group cancels
        all sibling tasks, preventing zombie processes.
        """
        try:
            async with asyncio.TaskGroup() as tg:
                for channel in self._channels:
                    tg.create_task(
                        self._run_channel(channel),
                        name=f"channel:{channel.name}",
                    )
                tg.create_task(self._bus_worker(), name="bus_worker")
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error(f"Gateway task failed: {exc}")
            raise

    async def _run_channel(self, channel: BaseChannel) -> None:
        """Start a single channel, stopping it cleanly on cancellation."""
        logger.info(f"Starting channel: {channel.name}")
        try:
            await channel.start(self._bus)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info(f"Stopping channel: {channel.name}")
            await channel.stop()

    async def _bus_worker(self) -> None:
        """
        Consume InboundMessages from the bus.
        Each message spawns an independent asyncio task so channels remain responsive.
        """
        logger.info("Bus worker started.")
        async for msg in self._bus.subscribe():
            asyncio.create_task(
                self._handle(msg),
                name=f"handle:{msg.channel}:{msg.user_id}",
            )

    async def _handle(self, msg: InboundMessage) -> None:
        """
        Full message handling pipeline:
          1. Resolve / create LangGraph thread
          2. Build RunnableConfig with channel context
          3. Stream agent response, forwarding tool-progress and final reply
          4. Forward each chunk to the channel
        """
        channel = self._channel_map.get(msg.channel)
        if channel is None:
            logger.warning(
                f"No channel handler for '{msg.channel}' — dropping message."
            )
            return

        channel_context = {
            "channel": msg.channel,
            "user_id": msg.user_id,
            "context_id": msg.context_id,
            "metadata": msg.metadata,
        }
        runnable_config = await self._sessions.get_config(
            channel=msg.channel,
            user_id=msg.user_id,
            context_id=msg.context_id,
            channel_context=channel_context,
        )

        input_state = {"messages": [HumanMessage(content=msg.content)]}

        try:
            from langchain_core.messages import AIMessage

            accumulated = ""
            # Track which tool-call IDs we've already notified about so we
            # don't spam the user when the same state is re-emitted.
            notified_tool_ids: set[str] = set()

            async for chunk in self._agent.astream(
                input_state,
                config=runnable_config,
                stream_mode="values",
                print_mode="values",
            ):
                if "messages" not in chunk:
                    continue

                messages = chunk["messages"]

                # ── Tool-progress notifications ───────────────────────────
                # When the LLM has decided to call a tool the AIMessage carries
                # non-empty tool_calls but often an empty content field.  Emit
                # a friendly status message so the user knows what is happening.
                for m in messages:
                    if not (isinstance(m, AIMessage) and m.tool_calls):
                        continue
                    for tc in m.tool_calls:
                        tc_id = tc.get("id") or tc.get("name", "")
                        if tc_id and tc_id not in notified_tool_ids:
                            notified_tool_ids.add(tc_id)
                            await channel.send(
                                OutboundMessage(
                                    channel=msg.channel,
                                    user_id=msg.user_id,
                                    context_id=msg.context_id,
                                    content="",
                                    streaming=True,
                                    metadata={
                                        "type": "tool_progress",
                                        "tool": tc.get("name", ""),
                                        "args": tc.get("args", {}),
                                    },
                                )
                            )

                # ── Final-text accumulation ───────────────────────────────
                # With stream_mode="values" the last message after a tool call
                # is often a ToolMessage, not an AIMessage.  Search backwards
                # for the last AIMessage that actually has text content.
                last_ai = next(
                    (
                        m
                        for m in reversed(messages)
                        if isinstance(m, AIMessage) and m.content
                    ),
                    None,
                )
                if last_ai is None:
                    continue

                raw = last_ai.content
                # Flatten list-of-content-blocks (some providers return this)
                if not isinstance(raw, str):
                    raw = " ".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in raw
                    )
                if raw and raw != accumulated:
                    delta = raw[len(accumulated) :]
                    accumulated = raw
                    if delta:
                        await channel.send(
                            OutboundMessage(
                                channel=msg.channel,
                                user_id=msg.user_id,
                                context_id=msg.context_id,
                                content=delta,
                                streaming=True,
                            )
                        )

            # Final non-streaming marker so the channel knows the turn is complete
            if accumulated:
                await channel.send(
                    OutboundMessage(
                        channel=msg.channel,
                        user_id=msg.user_id,
                        context_id=msg.context_id,
                        content=accumulated,
                        streaming=False,
                    )
                )

        except Exception:
            logger.exception(f"Error handling message from {msg.channel}/{msg.user_id}")
            try:
                await channel.send(
                    OutboundMessage(
                        channel=msg.channel,
                        user_id=msg.user_id,
                        context_id=msg.context_id,
                        content="Sorry, something went wrong. Please try again.",
                        streaming=False,
                    )
                )
            except Exception:
                logger.exception("Failed to send error response.")
