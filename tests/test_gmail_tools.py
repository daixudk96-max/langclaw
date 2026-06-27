"""Tests for Gmail tools, auth, config, and build_gmail_tools builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# GmailConfig defaults
# ---------------------------------------------------------------------------


class TestGmailConfigDefaults:
    def test_gmail_disabled_by_default(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig()
        assert cfg.enabled is False
        assert cfg.client_id == ""
        assert cfg.client_secret.get_secret_value() == ""
        assert cfg.readonly is True

    def test_gmail_nested_in_tools_config(self):
        from langclaw.config.schema import ToolsConfig

        tools = ToolsConfig()
        assert hasattr(tools, "gmail")
        assert tools.gmail.enabled is False

    def test_gmail_config_env_override(self, monkeypatch):
        monkeypatch.setenv("LANGCLAW__TOOLS__GMAIL__ENABLED", "true")
        monkeypatch.setenv("LANGCLAW__TOOLS__GMAIL__CLIENT_ID", "test-id")
        monkeypatch.setenv("LANGCLAW__TOOLS__GMAIL__CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("LANGCLAW__TOOLS__GMAIL__READONLY", "false")

        from langclaw.config.schema import LangclawConfig

        cfg = LangclawConfig()
        assert cfg.tools.gmail.enabled is True
        assert cfg.tools.gmail.client_id == "test-id"
        assert cfg.tools.gmail.client_secret.get_secret_value() == "test-secret"
        assert cfg.tools.gmail.readonly is False

    def test_gmail_token_path_default(self):
        from pathlib import Path

        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig()
        assert "gmail_token.json" in cfg.token_path
        assert ".langclaw" in cfg.token_path
        assert not cfg.token_path.startswith("~")
        assert Path(cfg.token_path).is_absolute()


# ---------------------------------------------------------------------------
# build_gmail_tools — readonly flag logic
# ---------------------------------------------------------------------------


def _gmail_config(*, enabled=True, client_id="cid", client_secret="csec", readonly=True):
    """Return a minimal LangclawConfig with Gmail configured."""
    from langclaw.config.schema import GmailConfig, LangclawConfig

    gmail = GmailConfig(
        enabled=enabled,
        client_id=client_id,
        client_secret=client_secret,
        readonly=readonly,
    )
    return LangclawConfig(tools={"gmail": gmail.model_dump()})


class TestBuildGmailTools:
    def test_disabled_returns_empty(self):
        from langclaw.agents.tools import build_gmail_tools

        cfg = _gmail_config(enabled=False)
        assert build_gmail_tools(cfg) == []

    def test_missing_client_id_returns_empty(self):
        from langclaw.agents.tools import build_gmail_tools

        cfg = _gmail_config(client_id="")
        assert build_gmail_tools(cfg) == []

    def test_readonly_returns_two_tools(self):
        from langclaw.agents.tools import build_gmail_tools

        cfg = _gmail_config(readonly=True)
        tools = build_gmail_tools(cfg)
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"read_email", "search_emails"}

    def test_full_access_returns_six_tools(self):
        from langclaw.agents.tools import build_gmail_tools

        cfg = _gmail_config(readonly=False)
        tools = build_gmail_tools(cfg)
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert names == {
            "read_email",
            "search_emails",
            "send_email",
            "draft_email",
            "reply_email",
            "manage_labels",
        }


# ---------------------------------------------------------------------------
# Gmail auth — credential flow
# ---------------------------------------------------------------------------


class TestGmailAuth:
    def test_missing_credentials_raises(self):
        from langclaw.agents.tools.gmail_auth import get_gmail_credentials
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="", client_secret="")
        with pytest.raises(RuntimeError, match="client_id"):
            get_gmail_credentials(cfg)

    def test_scopes_readonly(self):
        from langclaw.agents.tools.gmail_auth import SCOPES_FULL, SCOPES_READONLY

        assert "readonly" in SCOPES_READONLY[0]
        assert "readonly" not in SCOPES_FULL[0]

    def test_clear_cached_credentials(self):
        from langclaw.agents.tools import gmail_auth

        gmail_auth._cached_credentials = "fake"
        gmail_auth.clear_cached_credentials()
        assert gmail_auth._cached_credentials is None


# ---------------------------------------------------------------------------
# Individual tool output shapes (mocked Gmail API)
# ---------------------------------------------------------------------------

_FAKE_MESSAGE = {
    "id": "msg123",
    "threadId": "thread456",
    "snippet": "Hello there...",
    "labelIds": ["INBOX", "UNREAD"],
    "payload": {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "alice@example.com"},
            {"name": "To", "value": "bob@example.com"},
            {"name": "Cc", "value": ""},
            {"name": "Date", "value": "Mon, 1 Jan 2026 10:00:00 +0000"},
            {"name": "Message-ID", "value": "<abc@mail.example.com>"},
        ],
        "body": {
            "data": "SGVsbG8gdGhlcmU=",  # base64("Hello there")
            "size": 11,
        },
        "parts": [],
    },
}


def _mock_service():
    """Return a deeply-mocked Gmail API service."""
    svc = MagicMock()
    users = svc.users.return_value

    messages = users.messages.return_value
    messages.get.return_value.execute.return_value = _FAKE_MESSAGE
    messages.list.return_value.execute.return_value = {
        "messages": [{"id": "msg123", "threadId": "thread456"}],
    }
    messages.send.return_value.execute.return_value = {
        "id": "sent789",
        "threadId": "thread456",
        "labelIds": ["SENT"],
    }
    messages.modify.return_value.execute.return_value = {
        "id": "msg123",
        "labelIds": ["INBOX"],
    }

    drafts = users.drafts.return_value
    drafts.create.return_value.execute.return_value = {
        "id": "draft001",
        "message": {"id": "msg_draft"},
    }

    return svc


@pytest.mark.asyncio
class TestReadEmailTool:
    async def test_read_email_returns_expected_shape(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec")

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_read_email_tool

            t = make_read_email_tool(cfg)
            result = await t.ainvoke({"message_id": "msg123"})

        assert result["id"] == "msg123"
        assert result["subject"] == "Test Subject"
        assert result["from"] == "alice@example.com"
        assert "Hello there" in result["body"]
        assert isinstance(result["attachments"], list)


@pytest.mark.asyncio
class TestSearchEmailsTool:
    async def test_search_emails_returns_list(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec")

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_search_emails_tool

            t = make_search_emails_tool(cfg)
            result = await t.ainvoke({"query": "from:alice", "max_results": 5})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "msg123"
        assert result[0]["subject"] == "Test Subject"


@pytest.mark.asyncio
class TestSendEmailTool:
    async def test_send_email_returns_sent_status(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec", readonly=False)

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_send_email_tool

            t = make_send_email_tool(cfg)
            result = await t.ainvoke({"to": "bob@example.com", "subject": "Hi", "body": "Hello"})

        assert result["status"] == "sent"
        assert result["id"] == "sent789"


@pytest.mark.asyncio
class TestDraftEmailTool:
    async def test_draft_email_returns_draft_id(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec", readonly=False)

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_draft_email_tool

            t = make_draft_email_tool(cfg)
            result = await t.ainvoke({"to": "bob@example.com", "subject": "Draft", "body": "WIP"})

        assert result["status"] == "drafted"
        assert result["draft_id"] == "draft001"


@pytest.mark.asyncio
class TestReplyEmailTool:
    async def test_reply_email_returns_replied_status(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec", readonly=False)

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_reply_email_tool

            t = make_reply_email_tool(cfg)
            result = await t.ainvoke({"message_id": "msg123", "body": "Thanks!"})

        assert result["status"] == "replied"


@pytest.mark.asyncio
class TestManageLabelsTool:
    async def test_manage_labels_modifies_labels(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec", readonly=False)

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_manage_labels_tool

            t = make_manage_labels_tool(cfg)
            result = await t.ainvoke({"message_id": "msg123", "remove_labels": ["UNREAD"]})

        assert result["status"] == "modified"
        assert result["id"] == "msg123"

    async def test_manage_labels_no_ops_returns_error(self):
        from langclaw.config.schema import GmailConfig

        cfg = GmailConfig(enabled=True, client_id="cid", client_secret="csec", readonly=False)

        with patch("langclaw.agents.tools.gmail._get_gmail_service", return_value=_mock_service()):
            from langclaw.agents.tools.gmail import make_manage_labels_tool

            t = make_manage_labels_tool(cfg)
            result = await t.ainvoke({"message_id": "msg123"})

        assert "error" in result
