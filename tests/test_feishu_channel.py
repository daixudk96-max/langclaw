"""
Tests for Feishu channel configuration and basic functionality.
"""

from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class TestFeishuConfig:
    """Test Feishu channel configuration."""

    def test_feishu_config_default(self):
        """Test that Feishu config has correct defaults."""
        from langclaw.config.schema import FeishuChannelConfig

        config = FeishuChannelConfig()
        assert config.enabled is False
        assert config.app_id == ""
        assert config.app_secret.get_secret_value() == ""
        assert config.verification_token.get_secret_value() == ""
        assert config.encrypt_key.get_secret_value() == ""
        assert config.allow_from == []
        assert config.user_roles == {}

    def test_feishu_config_in_channels_config(self):
        """Test that Feishu config is wired into ChannelsConfig."""
        from langclaw.config.schema import ChannelsConfig, FeishuChannelConfig

        channels = ChannelsConfig()
        assert isinstance(channels.feishu, FeishuChannelConfig)
        assert channels.feishu.enabled is False

    def test_feishu_config_transport_defaults(self):
        """Feishu transport defaults include websocket mode and local webhook settings."""
        from langclaw.config.schema import FeishuChannelConfig

        config = FeishuChannelConfig()
        assert config.domain == "feishu"
        assert config.connection_mode == "websocket"
        assert config.webhook_host == "127.0.0.1"
        assert config.webhook_port == 8765
        assert config.webhook_path == "/feishu/webhook"


class TestFeishuChannel:
    """Test Feishu channel implementation."""

    def test_feishu_channel_import(self):
        """Test that FeishuChannel can be imported."""
        from langclaw.gateway.feishu import FeishuChannel

        assert FeishuChannel is not None
        assert FeishuChannel.name == "feishu"

    def test_feishu_channel_is_enabled_false_by_default(self):
        """Channel is disabled when required credentials are missing."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        config = FeishuChannelConfig(enabled=True)
        channel = FeishuChannel(config)
        assert channel.is_enabled() is False

    def test_feishu_channel_in_build_all_channels(self, monkeypatch):
        """Feishu channel is built when enabled in config with credentials."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.app import Langclaw
        from langclaw.config.schema import LangclawConfig

        monkeypatch.setattr(
            feishu_module,
            "check_feishu_requirements",
            lambda *args, **kwargs: True,
        )

        config = LangclawConfig()
        config.channels.feishu.enabled = True
        config.channels.feishu.app_id = "cli_test"
        config.channels.feishu.app_secret = "secret"

        app = Langclaw(config=config)
        channels = app._build_all_channels()

        assert "feishu" in [channel.name for channel in channels]

    def test_feishu_channel_not_built_without_runtime_dependency(self, monkeypatch):
        """Feishu channel is skipped when its runtime dependency is unavailable."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.app import Langclaw
        from langclaw.config.schema import LangclawConfig

        monkeypatch.setattr(
            feishu_module,
            "check_feishu_requirements",
            lambda *args, **kwargs: False,
        )

        config = LangclawConfig()
        config.channels.feishu.enabled = True
        config.channels.feishu.app_id = "cli_test"
        config.channels.feishu.app_secret = "secret"

        app = Langclaw(config=config)
        channels = app._build_all_channels()

        assert "feishu" not in [channel.name for channel in channels]


class TestFeishuPayloadHelpers:
    """Test Feishu payload builder helpers."""

    def test_build_markdown_post_payload(self):
        """Markdown payloads are wrapped in the Feishu post JSON envelope."""
        from langclaw.gateway.feishu import _build_markdown_post_payload

        payload = json.loads(_build_markdown_post_payload("hello **world**"))
        assert payload == {
            "zh_cn": {
                "content": [[{"tag": "md", "text": "hello **world**"}]],
            }
        }

    def test_parse_feishu_post_content_extracts_text_mentions_and_media_refs(self):
        """Rich Feishu post payloads are flattened into readable text and references."""
        from langclaw.gateway.feishu import parse_feishu_post_content

        result = parse_feishu_post_content(
            json.dumps(
                {
                    "en_us": {
                        "title": "Rich message",
                        "content": [
                            [{"tag": "img", "image_key": "img_1", "alt": "diagram"}],
                            [{"tag": "at", "user_name": "Alice", "open_id": "ou_alice"}],
                            [{"tag": "media", "file_key": "file_1", "file_name": "spec.pdf"}],
                        ],
                    }
                }
            )
        )

        assert result.text_content == (
            "Rich message\n[Image: diagram]\n@Alice\n[Attachment: spec.pdf]"
        )
        assert result.image_keys == ["img_1"]
        assert result.mentioned_ids == ["ou_alice"]
        assert len(result.media_refs) == 1
        assert result.media_refs[0].file_key == "file_1"
        assert result.media_refs[0].file_name == "spec.pdf"
        assert result.media_refs[0].resource_type == "file"


class TestFeishuSending:
    """Test outbound Feishu message sending."""

    @pytest.mark.asyncio
    async def test_send_ai_message_uses_text_payload_for_plain_text(self):
        """Plain text responses are sent with Feishu text payloads."""
        from langclaw.bus.base import OutboundMessage
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        sent_requests: list[SimpleNamespace] = []

        def _create(request: SimpleNamespace) -> SimpleNamespace:
            sent_requests.append(request)
            return SimpleNamespace(success=lambda: True, data=SimpleNamespace(message_id="msg_1"))

        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._client = SimpleNamespace(
            im=SimpleNamespace(
                v1=SimpleNamespace(message=SimpleNamespace(create=_create))
            )
        )

        await channel.send_ai_message(
            OutboundMessage(
                channel="feishu",
                user_id="user-1",
                context_id="ctx-1",
                chat_id="oc_chat_1",
                content="hello world",
            )
        )

        assert len(sent_requests) == 1
        request = sent_requests[0]
        assert request.receive_id_type == "chat_id"
        assert request.request_body.msg_type == "text"
        assert json.loads(request.request_body.content) == {"text": "hello world"}

    @pytest.mark.asyncio
    async def test_tool_progress_buffers_then_tool_result_sends_combined_message(self):
        """Tool progress is buffered and rendered together with the final tool result."""
        from langclaw.bus.base import OutboundMessage
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        sent_requests: list[SimpleNamespace] = []

        def _create(request: SimpleNamespace) -> SimpleNamespace:
            sent_requests.append(request)
            return SimpleNamespace(
                success=lambda: True,
                data=SimpleNamespace(message_id="msg_tool"),
            )

        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._client = SimpleNamespace(
            im=SimpleNamespace(v1=SimpleNamespace(message=SimpleNamespace(create=_create)))
        )

        await channel.send_tool_progress(
            OutboundMessage(
                channel="feishu",
                user_id="user-1",
                context_id="ctx-1",
                chat_id="oc_chat_1",
                content="",
                type="tool_progress",
                metadata={
                    "tool_call_id": "call_1",
                    "tool": "read_file",
                    "args": {"file_path": "notes.txt"},
                },
            )
        )
        await channel.send_tool_result(
            OutboundMessage(
                channel="feishu",
                user_id="user-1",
                context_id="ctx-1",
                chat_id="oc_chat_1",
                content="done",
                type="tool_result",
                metadata={"tool_call_id": "call_1"},
            )
        )

        assert len(sent_requests) == 1
        payload = sent_requests[0].request_body.content
        assert "notes.txt" in payload
        assert "done" in payload

    @pytest.mark.asyncio
    async def test_tool_progress_ignores_cron_contexts(self):
        """Cron-delivered tool progress and results are not pushed to Feishu chats."""
        from langclaw.bus.base import OutboundMessage
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        sent_requests: list[SimpleNamespace] = []

        def _create(request: SimpleNamespace) -> SimpleNamespace:
            sent_requests.append(request)
            return SimpleNamespace(
                success=lambda: True,
                data=SimpleNamespace(message_id="msg_cron"),
            )

        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._client = SimpleNamespace(
            im=SimpleNamespace(v1=SimpleNamespace(message=SimpleNamespace(create=_create)))
        )

        await channel.send_tool_progress(
            OutboundMessage(
                channel="feishu",
                user_id="user-1",
                context_id="cron:task:123",
                chat_id="oc_chat_1",
                content="",
                type="tool_progress",
                metadata={"tool_call_id": "call_2", "tool": "read_file", "args": {}},
            )
        )
        await channel.send_tool_result(
            OutboundMessage(
                channel="feishu",
                user_id="user-1",
                context_id="cron:task:123",
                chat_id="oc_chat_1",
                content="done",
                type="tool_result",
                metadata={"tool_call_id": "call_2"},
            )
        )

        assert sent_requests == []


class TestFeishuInbound:
    """Test inbound Feishu event handling."""

    @pytest.mark.asyncio
    async def test_handle_message_event_data_publishes_dm_text_to_bus(self):
        """Direct-message text events are published to the Langclaw bus."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        bus = AsyncMock()
        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._bus = bus

        data = SimpleNamespace(
            event=SimpleNamespace(
                message=SimpleNamespace(
                    message_id="om_1",
                    message_type="text",
                    chat_type="p2p",
                    chat_id="oc_chat_1",
                    content=json.dumps({"text": "hello from feishu"}),
                ),
                sender=SimpleNamespace(
                    sender_type="user",
                    sender_id=SimpleNamespace(open_id="ou_user_1"),
                ),
            )
        )

        await channel._handle_message_event_data(data)

        bus.publish.assert_awaited_once()
        inbound = bus.publish.await_args.args[0]
        assert inbound.channel == "feishu"
        assert inbound.user_id == "ou_user_1"
        assert inbound.chat_id == "oc_chat_1"
        assert inbound.context_id == "oc_chat_1"
        assert inbound.origin == "channel"
        assert inbound.content == "hello from feishu"

    @pytest.mark.asyncio
    async def test_handle_message_event_data_routes_commands_to_command_router(self):
        """Slash commands bypass the agent bus and go straight to the command router."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        bus = AsyncMock()
        command_router = SimpleNamespace(dispatch=AsyncMock(return_value="done"))
        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._bus = bus
        channel._command_router = command_router

        data = SimpleNamespace(
            event=SimpleNamespace(
                message=SimpleNamespace(
                    message_id="om_2",
                    message_type="text",
                    chat_type="p2p",
                    chat_id="oc_chat_1",
                    content=json.dumps({"text": "/help foo"}),
                ),
                sender=SimpleNamespace(
                    sender_type="user",
                    sender_id=SimpleNamespace(open_id="ou_user_1"),
                ),
            )
        )

        await channel._handle_message_event_data(data)

        command_router.dispatch.assert_awaited_once()
        assert command_router.dispatch.await_args.args[0] == "help"
        assert command_router.dispatch.await_args.args[1].args == ["foo"]
        bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_event_data_sends_command_response(self):
        """Command router responses are sent back to Feishu instead of being dropped."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        sent_requests: list[SimpleNamespace] = []

        def _create(request: SimpleNamespace) -> SimpleNamespace:
            sent_requests.append(request)
            return SimpleNamespace(success=lambda: True, data=SimpleNamespace(message_id="msg_2"))

        bus = AsyncMock()
        command_router = SimpleNamespace(dispatch=AsyncMock(return_value="done"))
        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._bus = bus
        channel._command_router = command_router
        channel._client = SimpleNamespace(
            im=SimpleNamespace(v1=SimpleNamespace(message=SimpleNamespace(create=_create)))
        )

        data = SimpleNamespace(
            event=SimpleNamespace(
                message=SimpleNamespace(
                    message_id="om_3",
                    message_type="text",
                    chat_type="p2p",
                    chat_id="oc_chat_1",
                    content=json.dumps({"text": "/help"}),
                ),
                sender=SimpleNamespace(
                    sender_type="user",
                    sender_id=SimpleNamespace(open_id="ou_user_1"),
                ),
            )
        )

        await channel._handle_message_event_data(data)

        bus.publish.assert_not_called()
        assert len(sent_requests) == 1
        assert json.loads(sent_requests[0].request_body.content) == {"text": "done"}


class TestFeishuTransport:
    """Test Feishu transport wiring."""

    @pytest.mark.asyncio
    async def test_connect_webhook_starts_local_server(self, monkeypatch):
        """Webhook mode builds the SDK client and starts a local aiohttp server."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        added_routes: list[tuple[str, object]] = []
        runner = AsyncMock()
        site = AsyncMock()
        fake_web = SimpleNamespace(
            Application=lambda: SimpleNamespace(
                router=SimpleNamespace(
                    add_post=lambda path, handler: added_routes.append((path, handler))
                )
            ),
            AppRunner=lambda app: runner,
            TCPSite=lambda _runner, host, port: SimpleNamespace(
                start=site.start,
                host=host,
                port=port,
            ),
        )

        config = FeishuChannelConfig(
            enabled=True,
            app_id="cli_test",
            app_secret="secret",
            connection_mode="webhook",
            webhook_host="127.0.0.1",
            webhook_port=9001,
            webhook_path="/hook",
            verification_token="vt_test",
        )
        channel = FeishuChannel(config)

        monkeypatch.setattr(feishu_module, "FEISHU_AVAILABLE", True, raising=False)
        monkeypatch.setattr(feishu_module, "FEISHU_WEBHOOK_AVAILABLE", True, raising=False)
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)
        monkeypatch.setattr(
            channel,
            "_build_lark_client",
            lambda domain: SimpleNamespace(client_domain=domain),
        )
        monkeypatch.setattr(channel, "_build_event_handler", lambda: object())
        monkeypatch.setattr(channel, "_hydrate_bot_identity", AsyncMock())

        await channel._connect_webhook()

        assert channel._client is not None
        assert channel._event_handler is not None
        assert added_routes and added_routes[0][0] == "/hook"
        runner.setup.assert_awaited_once()
        site.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_request_returns_challenge(self, monkeypatch):
        """URL verification requests echo the challenge value."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        fake_web = SimpleNamespace(
            Response=lambda **kwargs: SimpleNamespace(kind="response", **kwargs),
            json_response=lambda data, status=200: SimpleNamespace(
                kind="json",
                data=data,
                status=status,
            ),
        )
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
            )
        )

        request = SimpleNamespace(
            remote="127.0.0.1",
            headers={"Content-Type": "application/json"},
            content_length=None,
            read=AsyncMock(
                return_value=json.dumps(
                    {"type": "url_verification", "challenge": "abc123"}
                ).encode("utf-8")
            ),
        )

        response = await channel._handle_webhook_request(request)

        assert response.kind == "json"
        assert response.data == {"challenge": "abc123"}
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_handle_webhook_request_routes_message_receive_event(self, monkeypatch):
        """Webhook message.receive events are routed into the Feishu event handler."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        fake_web = SimpleNamespace(
            Response=lambda **kwargs: SimpleNamespace(kind="response", **kwargs),
            json_response=lambda data, status=200: SimpleNamespace(
                kind="json",
                data=data,
                status=status,
            ),
        )
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
            )
        )
        channel._on_message_event = lambda data: setattr(channel, "_last_event_type", "message")

        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "om_1",
                    "message_type": "text",
                    "chat_type": "p2p",
                    "chat_id": "oc_chat_1",
                    "content": json.dumps({"text": "hello"}),
                },
                "sender": {
                    "sender_type": "user",
                    "sender_id": {"open_id": "ou_user_1"},
                },
            },
        }
        request = SimpleNamespace(
            remote="127.0.0.1",
            headers={
                "Content-Type": "application/json",
                "x-lark-request-timestamp": str(int(time.time())),
                "x-lark-request-nonce": "n1",
            },
            content_length=None,
            read=AsyncMock(return_value=json.dumps(payload).encode("utf-8")),
        )

        response = await channel._handle_webhook_request(request)

        assert getattr(channel, "_last_event_type", None) == "message"
        assert response.kind == "json"
        assert response.data == {"code": 0, "msg": "ok"}

    @pytest.mark.asyncio
    async def test_handle_webhook_request_rejects_rate_limited_sender(self, monkeypatch):
        """Webhook requests are rejected early when the per-IP rate limiter trips."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        fake_web = SimpleNamespace(
            Response=lambda **kwargs: SimpleNamespace(kind="response", **kwargs),
            json_response=lambda data, status=200: SimpleNamespace(
                kind="json",
                data=data,
                status=status,
            ),
        )
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
            )
        )
        channel._check_webhook_rate_limit = lambda rate_key: False

        request = SimpleNamespace(
            remote="127.0.0.1",
            headers={"Content-Type": "application/json"},
            content_length=None,
            read=AsyncMock(return_value=b"{}"),
        )

        response = await channel._handle_webhook_request(request)

        assert response.kind == "response"
        assert response.status == 429

    @pytest.mark.asyncio
    async def test_webhook_token_only_rejects_stale_timestamp(self, monkeypatch):
        """Reject stale webhook timestamps when only verification_token is configured."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        fake_web = SimpleNamespace(
            Response=lambda **kwargs: SimpleNamespace(kind="response", **kwargs),
            json_response=lambda data, status=200: SimpleNamespace(
                kind="json",
                data=data,
                status=status,
            ),
        )
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
                verification_token="vt_test",
            )
        )

        payload = {
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "vt_test",
            },
            "event": {
                "message": {
                    "message_id": "om_1",
                    "message_type": "text",
                    "chat_type": "p2p",
                    "chat_id": "oc_chat_1",
                    "content": json.dumps({"text": "hello"}),
                },
                "sender": {
                    "sender_type": "user",
                    "sender_id": {"open_id": "ou_user_1"},
                },
            },
        }
        stale_timestamp = str(int(time.time()) - 3600)
        request = SimpleNamespace(
            remote="127.0.0.1",
            headers={
                "Content-Type": "application/json",
                "x-lark-request-timestamp": stale_timestamp,
                "x-lark-request-nonce": "n1",
            },
            content_length=None,
            read=AsyncMock(return_value=json.dumps(payload).encode("utf-8")),
        )

        response = await channel._handle_webhook_request(request)

        assert response.kind == "response"
        assert response.status == 401
        assert response.text == "Missing or stale timestamp"

    @pytest.mark.asyncio
    async def test_webhook_token_only_rejects_missing_timestamp(self, monkeypatch):
        """Reject webhook requests without timestamps in verification-token mode."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        fake_web = SimpleNamespace(
            Response=lambda **kwargs: SimpleNamespace(kind="response", **kwargs),
            json_response=lambda data, status=200: SimpleNamespace(
                kind="json",
                data=data,
                status=status,
            ),
        )
        monkeypatch.setattr(feishu_module, "web", fake_web, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
                verification_token="vt_test",
            )
        )

        payload = {
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "vt_test",
            }
        }
        request = SimpleNamespace(
            remote="127.0.0.1",
            headers={"Content-Type": "application/json"},
            content_length=None,
            read=AsyncMock(return_value=json.dumps(payload).encode("utf-8")),
        )

        response = await channel._handle_webhook_request(request)

        assert response.kind == "response"
        assert response.status == 401
        assert response.text == "Missing or stale timestamp"

    @pytest.mark.asyncio
    async def test_connect_webhook_requires_verification_material(self):
        """Webhook mode refuses to start without a verification token or encrypt key."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
            )
        )

        with pytest.raises(RuntimeError, match="verification token or encrypt key"):
            await channel._connect_webhook()

    def test_webhook_signature_validation_rejects_stale_timestamp(self):
        """Signed webhook requests outside the replay window are rejected."""
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        channel = FeishuChannel(
            FeishuChannelConfig(
                enabled=True,
                app_id="cli_test",
                app_secret="secret",
                connection_mode="webhook",
                encrypt_key="enc_key",
            )
        )

        body = b'{"ok": true}'
        timestamp = str(int(time.time()) - 3600)
        nonce = "n1"
        body_str = body.decode("utf-8")
        signature = __import__("hashlib").sha256(
            f"{timestamp}{nonce}{channel._encrypt_key}{body_str}".encode()
        ).hexdigest()
        headers = {
            "x-lark-request-timestamp": timestamp,
            "x-lark-request-nonce": nonce,
            "x-lark-signature": signature,
        }

        assert channel._is_webhook_signature_valid(headers, body) is False

    def test_build_event_handler_uses_dispatcher_builder(self, monkeypatch):
        """Event handler is built through Lark's dispatcher builder instead of a bare callback."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        registered: dict[str, object] = {}

        class _Builder:
            def register_p2_im_message_receive_v1(self, callback):
                registered["receive"] = callback
                return self

            def build(self):
                return "handler-object"

        fake_dispatcher = SimpleNamespace(
            builder=lambda encrypt_key, verification_token: _Builder()
        )
        monkeypatch.setattr(feishu_module, "EventDispatcherHandler", fake_dispatcher, raising=False)

        channel = FeishuChannel(
            FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        )
        handler = channel._build_event_handler()

        assert handler == "handler-object"
        assert "receive" in registered

    @pytest.mark.asyncio
    async def test_connect_websocket_builds_clients_and_handler(self, monkeypatch):
        """Websocket connect wires lark client, event handler, and ws client together."""
        import langclaw.gateway.feishu as feishu_module
        from langclaw.config.schema import FeishuChannelConfig
        from langclaw.gateway.feishu import FeishuChannel

        captured: dict[str, object] = {}
        fake_ws_client = SimpleNamespace()
        fake_lark = SimpleNamespace(LogLevel=SimpleNamespace(INFO="INFO", WARNING="WARNING"))

        config = FeishuChannelConfig(enabled=True, app_id="cli_test", app_secret="secret")
        channel = FeishuChannel(config)
        channel._loop = asyncio.get_running_loop()

        monkeypatch.setattr(feishu_module, "FEISHU_AVAILABLE", True, raising=False)
        monkeypatch.setattr(feishu_module, "FEISHU_WEBSOCKET_AVAILABLE", True, raising=False)
        monkeypatch.setattr(feishu_module, "lark", fake_lark, raising=False)
        monkeypatch.setattr(
            feishu_module,
            "FeishuWSClient",
            lambda **kwargs: captured.update(kwargs) or fake_ws_client,
            raising=False,
        )
        monkeypatch.setattr(
            channel,
            "_build_lark_client",
            lambda domain: SimpleNamespace(client_domain=domain),
        )
        monkeypatch.setattr(channel, "_build_event_handler", lambda: object())
        monkeypatch.setattr(channel, "_hydrate_bot_identity", AsyncMock())

        started: list[tuple[object, object, object]] = []

        def _run_in_executor(executor, fn, ws_client, adapter):
            started.append((fn, ws_client, adapter))
            future = asyncio.get_running_loop().create_future()
            future.set_result(None)
            return future

        monkeypatch.setattr(channel._loop, "run_in_executor", _run_in_executor)

        await channel._connect_websocket()

        assert channel._client is not None
        assert channel._ws_client is fake_ws_client
        assert channel._event_handler is not None
        assert captured["app_id"] == "cli_test"
        assert captured["app_secret"] == "secret"
        assert started and started[0][1] is fake_ws_client and started[0][2] is channel
