"""Gmail OAuth 2.0 credential management.

Handles loading, refreshing, and persisting Gmail API credentials.
First-time use triggers an interactive browser-based consent flow via
``google_auth_oauthlib.flow.InstalledAppFlow``.

Tokens are stored as JSON at ``~/.langclaw/gmail_token.json`` by default
(configurable via ``GmailConfig.token_path``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from langclaw.config.schema import secret_value

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

    from langclaw.config.schema import GmailConfig

SCOPES_FULL = ["https://mail.google.com/"]
SCOPES_READONLY = ["https://www.googleapis.com/auth/gmail.readonly"]

_cached_credentials: Credentials | None = None


def _resolve_token_path(config: GmailConfig) -> Path:
    return Path(config.token_path).expanduser()


def _build_client_config(config: GmailConfig) -> dict:
    """Build the client config dict expected by InstalledAppFlow."""
    return {
        "installed": {
            "client_id": config.client_id,
            "client_secret": secret_value(config.client_secret),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def save_credentials(creds: Credentials, path: Path) -> None:
    """Persist credentials to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")
    logger.debug("Gmail token saved to {}", path)


def get_gmail_credentials(config: GmailConfig) -> Credentials:
    """Return valid Gmail API credentials, refreshing or initiating OAuth as needed.

    The resolution order is:
      1. In-memory cache (process-lifetime).
      2. Token file on disk — refresh if expired.
      3. Full interactive OAuth consent flow (opens browser).

    Raises:
        ImportError: If ``google-auth`` / ``google-auth-oauthlib`` are missing.
        RuntimeError: If ``client_id`` or ``client_secret`` are blank.
    """
    global _cached_credentials  # noqa: PLW0603

    if not config.client_id or not config.client_secret:
        raise RuntimeError(
            "Gmail OAuth requires tools.gmail.client_id and "
            "tools.gmail.client_secret to be configured."
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials as OAuthCredentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client, google-auth, and google-auth-oauthlib "
            "are required for Gmail tools. "
            "Install with: pip install langclaw[gmail]"
        ) from exc

    scopes = SCOPES_READONLY if config.readonly else SCOPES_FULL

    if _cached_credentials and _cached_credentials.valid:
        return _cached_credentials

    token_path = _resolve_token_path(config)
    creds: OAuthCredentials | None = None

    if token_path.exists():
        try:
            creds = OAuthCredentials.from_authorized_user_file(str(token_path), scopes)
            logger.debug("Loaded Gmail token from {}", token_path)
        except (json.JSONDecodeError, ValueError, KeyError):
            logger.warning("Corrupt Gmail token at {}; re-authenticating", token_path)
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(creds, token_path)
            logger.info("Gmail token refreshed")
        except Exception:
            logger.warning("Gmail token refresh failed; re-authenticating")
            creds = None

    if not creds or not creds.valid:
        logger.info("Starting Gmail OAuth consent flow (opens browser)...")
        client_config = _build_client_config(config)
        flow = InstalledAppFlow.from_client_config(client_config, scopes)
        creds = flow.run_local_server(port=0)
        save_credentials(creds, token_path)
        logger.info("Gmail OAuth consent completed")

    _cached_credentials = creds
    return creds


def clear_cached_credentials() -> None:
    """Clear the in-memory credential cache (useful for testing)."""
    global _cached_credentials  # noqa: PLW0603
    _cached_credentials = None


__all__ = [
    "SCOPES_FULL",
    "SCOPES_READONLY",
    "clear_cached_credentials",
    "get_gmail_credentials",
    "save_credentials",
]
