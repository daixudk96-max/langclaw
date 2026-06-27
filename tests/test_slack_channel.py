"""
Tests for Slack channel configuration and basic functionality.
"""

from __future__ import annotations


class TestSlackConfig:
    """Test Slack channel configuration."""

    def test_slack_config_default(self):
        """Test that Slack config has correct defaults."""
        from langclaw.config.schema import SlackChannelConfig

        config = SlackChannelConfig()
        assert config.enabled is False
        assert config.bot_token.get_secret_value() == ""
        assert config.app_token.get_secret_value() == ""
        assert config.allow_from == []
        assert config.user_roles == {}
        assert config.reaction_feedback_enabled is True
        assert config.reaction_processing == "eyes"
        assert config.reaction_complete == "white_check_mark"

    def test_slack_config_from_dict(self):
        """Test creating Slack config from dict."""
        from langclaw.config.schema import SlackChannelConfig

        config = SlackChannelConfig(
            enabled=True,
            bot_token="xoxb-test",
            app_token="xapp-test",
            allow_from=["U123456"],
            user_roles={"U123456": "admin"},
        )
        assert config.enabled is True
        assert config.bot_token.get_secret_value() == "xoxb-test"
        assert config.app_token.get_secret_value() == "xapp-test"
        assert config.allow_from == ["U123456"]
        assert config.user_roles == {"U123456": "admin"}

    def test_slack_config_reaction_customization(self):
        """Test custom reaction emoji configuration."""
        from langclaw.config.schema import SlackChannelConfig

        config = SlackChannelConfig(
            enabled=True,
            bot_token="xoxb-test",
            app_token="xapp-test",
            reaction_feedback_enabled=False,
            reaction_processing="hourglass",
            reaction_complete="tada",
        )
        assert config.reaction_feedback_enabled is False
        assert config.reaction_processing == "hourglass"
        assert config.reaction_complete == "tada"


class TestSlackChannel:
    """Test Slack channel implementation."""

    def test_slack_channel_import(self):
        """Test that SlackChannel can be imported."""
        from langclaw.gateway.slack import SlackChannel

        assert SlackChannel is not None
        assert SlackChannel.name == "slack"

    def test_slack_channel_instantiation(self):
        """Test that SlackChannel can be instantiated with config."""
        from langclaw.config.schema import SlackChannelConfig
        from langclaw.gateway.slack import SlackChannel

        config = SlackChannelConfig(
            enabled=True,
            bot_token="xoxb-test",
            app_token="xapp-test",
        )
        channel = SlackChannel(config)
        assert channel.name == "slack"
        assert channel._config == config

    def test_slack_channel_is_enabled_false_by_default(self):
        """Test that channel is disabled when tokens are missing."""
        from langclaw.config.schema import SlackChannelConfig
        from langclaw.gateway.slack import SlackChannel

        config = SlackChannelConfig(enabled=True)  # enabled but no tokens
        channel = SlackChannel(config)
        assert channel.is_enabled() is False

    def test_slack_channel_is_enabled_with_tokens(self):
        """Test that channel is enabled when tokens are provided."""
        from langclaw.config.schema import SlackChannelConfig
        from langclaw.gateway.slack import SlackChannel

        config = SlackChannelConfig(
            enabled=True,
            bot_token="xoxb-test",
            app_token="xapp-test",
        )
        channel = SlackChannel(config)
        assert channel.is_enabled() is True

    def test_slack_channel_allow_from(self):
        """Test user whitelist checking."""
        from langclaw.config.schema import SlackChannelConfig
        from langclaw.gateway.slack import SlackChannel

        config = SlackChannelConfig(
            enabled=True,
            bot_token="xoxb-test",
            app_token="xapp-test",
            allow_from=["U123456", "alice"],
        )
        channel = SlackChannel(config)

        # Should allow listed user ID
        assert channel._is_allowed("U123456", "alice") is True
        # Should allow listed username
        assert channel._is_allowed("U789", "alice") is True
        # Should reject unlisted user
        assert channel._is_allowed("U999", "bob") is False
        # Empty allow_from means allow all
        config.allow_from = []
        channel = SlackChannel(config)
        assert channel._is_allowed("U999", "bob") is True
