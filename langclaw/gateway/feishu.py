"""Feishu/Lark channel implementation."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

try:
    import aiohttp
    from aiohttp import web

    FEISHU_WEBHOOK_AVAILABLE = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]
    web = None  # type: ignore[assignment]
    FEISHU_WEBHOOK_AVAILABLE = False

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
        UpdateMessageRequest,
        UpdateMessageRequestBody,
    )
    from lark_oapi.core.const import FEISHU_DOMAIN, LARK_DOMAIN
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
    from lark_oapi.ws import Client as FeishuWSClient

    FEISHU_AVAILABLE = True
    FEISHU_WEBSOCKET_AVAILABLE = True
except ImportError:
    lark = None  # type: ignore[assignment]
    CreateMessageRequest = None  # type: ignore[assignment]
    CreateMessageRequestBody = None  # type: ignore[assignment]
    UpdateMessageRequest = None  # type: ignore[assignment]
    UpdateMessageRequestBody = None  # type: ignore[assignment]
    FEISHU_DOMAIN = None  # type: ignore[assignment]
    LARK_DOMAIN = None  # type: ignore[assignment]
    EventDispatcherHandler = None  # type: ignore[assignment]
    FeishuWSClient = None  # type: ignore[assignment]
    FEISHU_AVAILABLE = False
    FEISHU_WEBSOCKET_AVAILABLE = False

from loguru import logger

from langclaw.bus.base import InboundMessage
from langclaw.config.schema import FeishuChannelConfig, secret_value
from langclaw.cron.utils import is_cron_context_id
from langclaw.gateway.base import BaseChannel
from langclaw.gateway.commands import CommandContext
from langclaw.gateway.utils import format_tool_progress, is_allowed, split_message

if TYPE_CHECKING:
    from langclaw.bus.base import BaseMessageBus, OutboundMessage


_MARKDOWN_HINT_RE = re.compile(
    r"(^#{1,6}\s)|(^\s*[-*]\s)|(^\s*\d+\.\s)|(^\s*---+\s*$)|(```)|(`[^`\n]+`)|(\*\*[^*\n].+?\*\*)|(~~[^~\n].+?~~)|(<u>.+?</u>)|(\*[^*\n]+\*)|(\[[^\]]+\]\([^)]+\))|(^>\s)",
    re.MULTILINE,
)


def _build_markdown_post_payload(content: str) -> str:
    return json.dumps(
        {
            "zh_cn": {
                "content": [[{"tag": "md", "text": content}]],
            }
        },
        ensure_ascii=False,
    )


def _run_official_feishu_ws_client(ws_client: Any, adapter: Any) -> None:
    ws_client.start()


def check_feishu_requirements(connection_mode: str = "websocket") -> bool:
    if not FEISHU_AVAILABLE:
        return False
    if connection_mode == "webhook":
        return FEISHU_WEBHOOK_AVAILABLE
    return FEISHU_WEBSOCKET_AVAILABLE


@dataclass(frozen=True)
class FeishuPostMediaRef:
    file_key: str
    file_name: str = ""
    resource_type: str = "file"


@dataclass(frozen=True)
class FeishuPostParseResult:
    text_content: str
    image_keys: list[str] = field(default_factory=list)
    media_refs: list[FeishuPostMediaRef] = field(default_factory=list)
    mentioned_ids: list[str] = field(default_factory=list)


def parse_feishu_post_content(raw_content: str) -> FeishuPostParseResult:
    try:
        parsed = json.loads(raw_content) if raw_content else {}
    except json.JSONDecodeError:
        return FeishuPostParseResult(text_content="[Rich text message]")
    return parse_feishu_post_payload(parsed)


def parse_feishu_post_payload(payload: Any) -> FeishuPostParseResult:
    resolved = _resolve_post_payload(payload)
    if not resolved:
        return FeishuPostParseResult(text_content="[Rich text message]")

    image_keys: list[str] = []
    media_refs: list[FeishuPostMediaRef] = []
    mentioned_ids: list[str] = []
    parts: list[str] = []

    title = str(resolved.get("title", "") or "").strip()
    if title:
        parts.append(title)

    for row in resolved.get("content", []) or []:
        if not isinstance(row, list):
            continue
        row_text = "".join(
            _render_post_element(item, image_keys, media_refs, mentioned_ids) for item in row
        ).strip()
        if row_text:
            parts.append(row_text)

    return FeishuPostParseResult(
        text_content="\n".join(parts).strip() or "[Rich text message]",
        image_keys=image_keys,
        media_refs=media_refs,
        mentioned_ids=mentioned_ids,
    )


def _resolve_post_payload(payload: Any) -> dict[str, Any]:
    direct = _to_post_payload(payload)
    if direct:
        return direct
    if not isinstance(payload, dict):
        return {}

    wrapped = payload.get("post")
    wrapped_direct = _resolve_locale_payload(wrapped)
    if wrapped_direct:
        return wrapped_direct
    return _resolve_locale_payload(payload)


def _resolve_locale_payload(payload: Any) -> dict[str, Any]:
    direct = _to_post_payload(payload)
    if direct:
        return direct
    if not isinstance(payload, dict):
        return {}

    for key in ("zh_cn", "en_us"):
        candidate = _to_post_payload(payload.get(key))
        if candidate:
            return candidate
    for value in payload.values():
        candidate = _to_post_payload(value)
        if candidate:
            return candidate
    return {}


def _to_post_payload(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    content = candidate.get("content")
    if not isinstance(content, list):
        return {}
    return {
        "title": str(candidate.get("title", "") or ""),
        "content": content,
    }


def _render_post_element(
    element: Any,
    image_keys: list[str],
    media_refs: list[FeishuPostMediaRef],
    mentioned_ids: list[str],
) -> str:
    if isinstance(element, str):
        return element
    if not isinstance(element, dict):
        return ""

    tag = str(element.get("tag", "")).strip().lower()
    if tag == "text":
        return str(element.get("text", "") or "")
    if tag == "at":
        mentioned_id = str(element.get("open_id", "") or element.get("user_id", "")).strip()
        if mentioned_id and mentioned_id not in mentioned_ids:
            mentioned_ids.append(mentioned_id)
        display_name = (
            str(element.get("user_name", "") or "").strip()
            or str(element.get("name", "") or "").strip()
            or str(element.get("text", "") or "").strip()
            or mentioned_id
        )
        return f"@{display_name}" if display_name else "@"
    if tag in {"img", "image"}:
        image_key = str(element.get("image_key", "") or "").strip()
        if image_key and image_key not in image_keys:
            image_keys.append(image_key)
        alt = (
            str(element.get("text", "") or "").strip()
            or str(element.get("alt", "") or "").strip()
        )
        return f"[Image: {alt}]" if alt else "[Image]"
    if tag in {"media", "file", "audio", "video"}:
        file_key = str(element.get("file_key", "") or "").strip()
        file_name = (
            str(element.get("file_name", "") or "").strip()
            or str(element.get("title", "") or "").strip()
            or str(element.get("text", "") or "").strip()
        )
        if file_key:
            media_refs.append(
                FeishuPostMediaRef(
                    file_key=file_key,
                    file_name=file_name,
                    resource_type=tag if tag in {"audio", "video"} else "file",
                )
            )
        return f"[Attachment: {file_name}]" if file_name else "[Attachment]"
    if tag == "br":
        return "\n"
    if tag in {"hr", "divider"}:
        return "\n---\n"
    return _render_nested_post(element.get("content"), image_keys, media_refs, mentioned_ids)


def _render_nested_post(
    value: Any,
    image_keys: list[str],
    media_refs: list[FeishuPostMediaRef],
    mentioned_ids: list[str],
) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(
            part
            for item in value
            for part in [_render_nested_post(item, image_keys, media_refs, mentioned_ids)]
            if part
        )
    if isinstance(value, dict):
        direct = _render_post_element(value, image_keys, media_refs, mentioned_ids)
        if direct:
            return direct
        return " ".join(
            part
            for item in value.values()
            for part in [_render_nested_post(item, image_keys, media_refs, mentioned_ids)]
            if part
        )
    return ""


class FeishuChannel(BaseChannel):
    """Feishu/Lark messaging channel."""

    name = "feishu"
    _MAX_MESSAGE_LEN = 8000

    def __init__(self, config: FeishuChannelConfig) -> None:
        self._config = config
        self._client: Any = None
        self._bus: BaseMessageBus | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws_client: Any = None
        self._ws_future: asyncio.Future | None = None
        self._event_handler: Any = None
        self._webhook_runner: Any = None
        self._webhook_site: Any = None
        self._domain_name = config.domain
        self._connection_mode = config.connection_mode
        self._webhook_host = config.webhook_host
        self._webhook_port = config.webhook_port
        self._webhook_path = config.webhook_path
        self._verification_token = secret_value(config.verification_token)
        self._encrypt_key = secret_value(config.encrypt_key)
        self._tool_call_buffer: dict[str, dict[str, Any]] = {}
        self._webhook_rate_counts: dict[str, tuple[int, float]] = {}

    def is_enabled(self) -> bool:
        return self._config.enabled and bool(self._config.app_id) and bool(self._config.app_secret)

    async def start(self, bus: BaseMessageBus) -> None:
        if not FEISHU_AVAILABLE:
            raise ImportError(
                "FeishuChannel requires lark-oapi. Install with: uv add 'langclaw[feishu]'"
            )

        self._bus = bus
        self._loop = asyncio.get_running_loop()
        logger.info(f"FeishuChannel starting in {self._connection_mode} mode")
        if self._connection_mode == "webhook":
            await self._connect_webhook()
        else:
            await self._connect_websocket()

        while True:
            await asyncio.sleep(1)

    async def send_tool_progress(self, msg: OutboundMessage) -> None:
        if is_cron_context_id(msg.context_id):
            return
        tc_id = msg.metadata.get("tool_call_id", "")
        if tc_id:
            self._tool_call_buffer[tc_id] = {
                "tool": msg.metadata.get("tool", ""),
                "args": msg.metadata.get("args") or {},
            }

    async def send_tool_result(self, msg: OutboundMessage) -> None:
        if is_cron_context_id(msg.context_id):
            return
        tc_id = msg.metadata.get("tool_call_id", "")
        call_info = self._tool_call_buffer.pop(tc_id, {})
        if not call_info:
            return
        header = format_tool_progress(
            call_info.get("tool", ""),
            call_info.get("args") or {},
            markup="markdown",
        )
        combined = f"{header}\n```\n{msg.content or ''}\n```"
        from langclaw.bus.base import OutboundMessage

        await self.send_ai_message(
            OutboundMessage(
                channel=self.name,
                user_id=msg.user_id,
                context_id=msg.context_id,
                chat_id=msg.chat_id,
                content=combined,
                metadata=msg.metadata,
            )
        )

    async def send_ai_chunk(self, msg: OutboundMessage) -> None:
        await super().send_ai_chunk(msg)

    async def send_ai_message(self, msg: OutboundMessage) -> None:
        if self._client is None or not msg.content:
            return
        try:
            for chunk in split_message(msg.content, max_len=self._MAX_MESSAGE_LEN):
                msg_type, payload = self._build_outbound_payload(chunk)
                request_body = self._build_create_message_body(msg_type=msg_type, content=payload)
                request = self._build_create_message_request(
                    chat_id=msg.chat_id,
                    request_body=request_body,
                )
                await asyncio.to_thread(self._client.im.v1.message.create, request)
        except Exception as exc:
            logger.error(f"Feishu send_ai_message failed for {msg.chat_id}: {exc}")

    async def edit_message(self, chat_id: str, message_id: str, content: str) -> None:
        if self._client is None or not content:
            return
        try:
            msg_type, payload = self._build_outbound_payload(content)
            request_body = self._build_update_message_body(msg_type=msg_type, content=payload)
            request = self._build_update_message_request(
                message_id=message_id,
                request_body=request_body,
            )
            await asyncio.to_thread(self._client.im.v1.message.update, request)
        except Exception as exc:
            logger.error(f"Feishu edit_message failed for {chat_id}/{message_id}: {exc}")

    async def stop(self) -> None:
        if self._ws_client is not None:
            stop_fn = getattr(self._ws_client, "stop", None) or getattr(
                self._ws_client,
                "close",
                None,
            )
            if callable(stop_fn):
                try:
                    maybe_result = stop_fn()
                    if asyncio.iscoroutine(maybe_result):
                        await maybe_result
                except Exception as exc:
                    logger.debug(f"Feishu ws client stop failed: {exc}")

        if self._ws_future is not None:
            self._ws_future.cancel()
            try:
                await self._ws_future
            except Exception:
                pass

        if self._webhook_runner is not None:
            try:
                await self._webhook_runner.cleanup()
            except Exception as exc:
                logger.debug(f"Feishu webhook cleanup failed: {exc}")

        self._ws_client = None
        self._ws_future = None
        self._webhook_runner = None
        self._webhook_site = None
        self._event_handler = None
        self._loop = None
        self._bus = None
        self._client = None
        logger.info("FeishuChannel stopped")

    async def _connect_websocket(self) -> None:
        if not FEISHU_WEBSOCKET_AVAILABLE or FeishuWSClient is None or lark is None:
            raise RuntimeError("websocket mode unavailable")
        if self._loop is None:
            raise RuntimeError("channel loop is not ready")

        domain = FEISHU_DOMAIN if self._domain_name != "lark" else LARK_DOMAIN
        self._client = self._build_lark_client(domain)
        self._event_handler = self._build_event_handler()
        await self._hydrate_bot_identity()
        self._ws_client = FeishuWSClient(
            app_id=self._config.app_id,
            app_secret=secret_value(self._config.app_secret),
            log_level=lark.LogLevel.INFO,
            event_handler=self._event_handler,
            domain=domain,
        )
        self._ws_future = self._loop.run_in_executor(
            None,
            _run_official_feishu_ws_client,
            self._ws_client,
            self,
        )

    async def _connect_webhook(self) -> None:
        if not FEISHU_WEBHOOK_AVAILABLE or web is None:
            raise RuntimeError("webhook mode unavailable")
        if not self._verification_token and not self._encrypt_key:
            raise RuntimeError(
                "webhook mode requires a verification token or encrypt key"
            )

        domain = FEISHU_DOMAIN if self._domain_name != "lark" else LARK_DOMAIN
        self._client = self._build_lark_client(domain)
        self._event_handler = self._build_event_handler()
        await self._hydrate_bot_identity()
        app = web.Application()
        app.router.add_post(self._webhook_path, self._handle_webhook_request)
        self._webhook_runner = web.AppRunner(app)
        await self._webhook_runner.setup()
        self._webhook_site = web.TCPSite(
            self._webhook_runner,
            self._webhook_host,
            self._webhook_port,
        )
        await self._webhook_site.start()

    def _build_lark_client(self, domain: Any) -> Any:
        if lark is None:
            raise RuntimeError("lark-oapi not installed")
        return (
            lark.Client.builder()
            .app_id(self._config.app_id)
            .app_secret(secret_value(self._config.app_secret))
            .domain(domain)
            .log_level(lark.LogLevel.WARNING)
            .build()
        )

    async def _handle_webhook_request(self, request: Any) -> Any:
        if web is None:
            raise RuntimeError("aiohttp.web not available")

        remote_ip = getattr(request, "remote", "") or "unknown"
        rate_key = f"{self._config.app_id}:{self._webhook_path}:{remote_ip}"
        if not self._check_webhook_rate_limit(rate_key):
            return web.Response(status=429, text="Too Many Requests")

        body_bytes = await request.read()
        payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

        if payload.get("type") == "url_verification":
            return web.json_response({"challenge": payload.get("challenge", "")})

        timestamp = str(request.headers.get("x-lark-request-timestamp", "") or "")
        if not timestamp or not self._is_recent_webhook_timestamp(timestamp):
            return web.Response(status=401, text="Missing or stale timestamp")

        if self._verification_token:
            header = payload.get("header") or {}
            incoming_token = str(header.get("token") or payload.get("token") or "")
            if (
                not incoming_token
                or not hmac.compare_digest(incoming_token, self._verification_token)
            ):
                return web.Response(status=401, text="Invalid verification token")

        if self._encrypt_key and not self._is_webhook_signature_valid(request.headers, body_bytes):
            return web.Response(status=401, text="Invalid signature")

        if payload.get("encrypt"):
            return web.json_response(
                {"code": 400, "msg": "encrypted webhook payloads are not supported"},
                status=400,
            )

        event_type = str((payload.get("header") or {}).get("event_type") or "")
        data = self._namespace_from_mapping(payload)
        if event_type == "im.message.receive_v1":
            self._on_message_event(data)
        return web.json_response({"code": 0, "msg": "ok"})

    def _is_recent_webhook_timestamp(self, timestamp: str) -> bool:
        try:
            return abs(__import__("time").time() - int(timestamp)) <= 300
        except (ValueError, TypeError):
            return False

    def _is_webhook_signature_valid(self, headers: Any, body_bytes: bytes) -> bool:
        timestamp = str(headers.get("x-lark-request-timestamp", "") or "")
        nonce = str(headers.get("x-lark-request-nonce", "") or "")
        signature = str(headers.get("x-lark-signature", "") or "")
        if not timestamp or not nonce or not signature:
            return False
        if not self._is_recent_webhook_timestamp(timestamp):
            return False
        body_str = body_bytes.decode("utf-8", errors="replace")
        computed = hashlib.sha256(
            f"{timestamp}{nonce}{self._encrypt_key}{body_str}".encode()
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    def _check_webhook_rate_limit(self, rate_key: str) -> bool:
        now = __import__("time").time()
        count, window_start = self._webhook_rate_counts.get(rate_key, (0, now))
        if now - window_start >= 60:
            count, window_start = 0, now
        if count >= 120:
            self._webhook_rate_counts[rate_key] = (count, window_start)
            return False
        self._webhook_rate_counts[rate_key] = (count + 1, window_start)
        return True

    def _namespace_from_mapping(self, value: Any) -> Any:
        if isinstance(value, dict):
            return SimpleNamespace(**{k: self._namespace_from_mapping(v) for k, v in value.items()})
        if isinstance(value, list):
            return [self._namespace_from_mapping(item) for item in value]
        return value

    def _build_event_handler(self) -> Any:
        if EventDispatcherHandler is None:
            return self._handle_message_event_data
        return (
            EventDispatcherHandler.builder(
                self._encrypt_key,
                self._verification_token,
            )
            .register_p2_im_message_receive_v1(self._on_message_event)
            .build()
        )

    def _on_message_event(self, data: Any) -> None:
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self._handle_message_event_data(data), self._loop)

        def _log_exception(done_future: Any) -> None:
            exc = done_future.exception()
            if exc is not None:
                logger.error(f"Feishu event handler failed: {exc}")

        future.add_done_callback(_log_exception)

    async def _hydrate_bot_identity(self) -> None:
        return None

    async def _handle_message_event_data(self, data: Any) -> None:
        if self._bus is None:
            return

        event = getattr(data, "event", None)
        message = getattr(event, "message", None)
        sender = getattr(event, "sender", None)
        sender_id = getattr(sender, "sender_id", None)
        user_id = str(
            getattr(sender_id, "open_id", "")
            or getattr(sender_id, "user_id", "")
            or ""
        ).strip()

        if not message or not user_id:
            return
        if getattr(sender, "sender_type", "") == "bot":
            return
        if not self._is_allowed(user_id):
            return

        message_type = str(getattr(message, "message_type", "") or "").strip().lower()
        raw_content = str(getattr(message, "content", "") or "")
        if message_type == "text":
            try:
                payload = json.loads(raw_content) if raw_content else {}
            except json.JSONDecodeError:
                payload = {"text": raw_content}
            content = str(payload.get("text", "") or "").strip()
        elif message_type == "post":
            content = parse_feishu_post_content(raw_content).text_content
        else:
            content = ""

        if not content:
            return

        chat_id = str(getattr(message, "chat_id", "") or user_id)

        if content.startswith("/") and self._command_router is not None:
            parts = content.split()
            cmd = parts[0].lstrip("/").lower() if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            if cmd:
                ctx = CommandContext(
                    channel=self.name,
                    user_id=user_id,
                    context_id=chat_id,
                    chat_id=chat_id,
                    args=args,
                )
                response = await self._command_router.dispatch(cmd, ctx)
                if response:
                    from langclaw.bus.base import OutboundMessage

                    await self.send_ai_message(
                        OutboundMessage(
                            channel=self.name,
                            user_id=user_id,
                            context_id=chat_id,
                            chat_id=chat_id,
                            content=response,
                        )
                    )
                return

        await self._bus.publish(
            InboundMessage(
                channel=self.name,
                user_id=user_id,
                context_id=chat_id,
                chat_id=chat_id,
                content=content,
                origin="channel",
                metadata={"message_id": getattr(message, "message_id", "")},
            )
        )

    def _is_allowed(self, user_id: str, username: str | None = None) -> bool:
        return is_allowed(self._config.allow_from, user_id, username)

    def _build_outbound_payload(self, content: str) -> tuple[str, str]:
        if _MARKDOWN_HINT_RE.search(content):
            return "post", _build_markdown_post_payload(content)
        return "text", json.dumps({"text": content}, ensure_ascii=False)

    @staticmethod
    def _build_create_message_body(*, msg_type: str, content: str) -> Any:
        if CreateMessageRequestBody is not None:
            return (
                CreateMessageRequestBody.builder()
                .msg_type(msg_type)
                .content(content)
                .uuid(str(uuid.uuid4()))
                .build()
            )
        return SimpleNamespace(msg_type=msg_type, content=content, uuid=str(uuid.uuid4()))

    @staticmethod
    def _build_create_message_request(*, chat_id: str, request_body: Any) -> Any:
        if CreateMessageRequest is not None:
            return (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .receive_id(chat_id)
                .request_body(request_body)
                .build()
            )
        return SimpleNamespace(
            receive_id_type="chat_id",
            receive_id=chat_id,
            request_body=request_body,
        )

    @staticmethod
    def _build_update_message_body(*, msg_type: str, content: str) -> Any:
        if UpdateMessageRequestBody is not None:
            return UpdateMessageRequestBody.builder().msg_type(msg_type).content(content).build()
        return SimpleNamespace(msg_type=msg_type, content=content)

    @staticmethod
    def _build_update_message_request(*, message_id: str, request_body: Any) -> Any:
        if UpdateMessageRequest is not None:
            return (
                UpdateMessageRequest.builder()
                .message_id(message_id)
                .request_body(request_body)
                .build()
            )
        return SimpleNamespace(message_id=message_id, request_body=request_body)
