# Slack Channel Setup Guide

This guide walks you through setting up the Slack channel for Langclaw using Socket Mode.

## Prerequisites

- A Slack workspace where you have permission to create apps
- Python 3.11+
- Langclaw installed with Slack support: `uv add "langclaw[slack]"`

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Enter an App Name (e.g., "Langclaw Bot")
5. Select your workspace
6. Click "Create App"

## Step 2: Configure Bot Permissions

1. In the left sidebar, go to **OAuth & Permissions**
2. Under **Scopes → Bot Token Scopes**, add these permissions:
   - `app_mentions:read` - View messages that mention your bot
   - `channels:history` - View messages in public channels
   - `chat:write` - Send messages as the bot
   - `files:read` - View files in channels/conversations
   - `im:history` - View messages in DMs
   - `im:write` - Send DMs
   - `users:read` - View people in the workspace

3. Scroll up and click **Install to Workspace**
4. Authorize the app
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
   - Save this as `LANGCLAW__CHANNELS__SLACK__BOT_TOKEN`

## Step 3: Enable Socket Mode

1. In the left sidebar, go to **Socket Mode**
2. Toggle **Enable Socket Mode** to On
3. Under **App-Level Tokens**, click **Generate Token and Scopes**
4. Enter a token name (e.g., "socket-token")
5. Add the `connections:write` scope
6. Click **Generate**
7. Copy the **App-Level Token** (starts with `xapp-`)
   - Save this as `LANGCLAW__CHANNELS__SLACK__APP_TOKEN`

## Step 4: Enable Event Subscriptions

1. In the left sidebar, go to **Event Subscriptions**
2. Toggle **Enable Events** to On
3. Under **Subscribe to bot events**, add:
   - `app_mention` - Your bot is mentioned in a channel
   - `message.im` - A message is posted in a DM with your bot

4. Click **Save Changes**

## Step 5: Configure Langclaw

### Option A: Environment Variables

Add to your `.env` file:

```bash
LANGCLAW__CHANNELS__SLACK__ENABLED=true
LANGCLAW__CHANNELS__SLACK__BOT_TOKEN=xoxb-your-bot-token-here
LANGCLAW__CHANNELS__SLACK__APP_TOKEN=xapp-your-app-token-here

# Optional: Restrict to specific user IDs (comma-separated)
LANGCLAW__CHANNELS__SLACK__ALLOW_FROM=U123456,U789012
```

### Option B: Config File

Edit `~/.langclaw/config.json`:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "bot_token": "xoxb-your-bot-token-here",
      "app_token": "xapp-your-app-token-here",
      "allow_from": ["U123456", "U789012"]
    }
  }
}
```

## Step 6: Run Langclaw

```bash
langclaw gateway
```

You should see:
```
SlackChannel starting…
```

## Features

### Direct Messages
Send a DM to your bot - it will respond automatically.

### Channel Mentions
In any channel where the bot is a member, mention it:
```
@YourBot What's the weather today?
```

### Slash Commands
Built-in commands like `/start`, `/help`, `/reset`, `/cron` work automatically.

### File Attachments
Upload images, documents, or other files - they'll be processed by the agent.

### Threads
The bot maintains conversation context in threads automatically.

## User Permissions (RBAC)

Restrict tool access by user:

```json
{
  "channels": {
    "slack": {
      "user_roles": {
        "U123456": "admin",
        "U789012": "viewer"
      }
    }
  },
  "permissions": {
    "enabled": true,
    "default_role": "viewer",
    "roles": {
      "admin": {
        "tools": ["*"]
      },
      "viewer": {
        "tools": ["web_search"]
      }
    }
  }
}
```

## Finding Your User ID

To find Slack user IDs for `allow_from`:

1. Right-click on a user's profile in Slack
2. Select **View full profile**
3. Click **⋯ More actions**
4. Select **Copy member ID**

## Troubleshooting

### Bot doesn't respond to DMs
- Verify `im:history` and `im:write` scopes are added
- Check that Event Subscriptions includes `message.im`
- Reinstall the app to workspace

### Bot doesn't respond to mentions
- Verify `app_mentions:read` scope is added
- Check that Event Subscriptions includes `app_mention`
- Make sure the bot is invited to the channel (`/invite @YourBot`)

### "SlackChannel requires 'langclaw[slack]'" error
```bash
uv add "langclaw[slack]"
```

### Socket connection fails
- Verify both tokens are correct (bot token starts with `xoxb-`, app token with `xapp-`)
- Check that Socket Mode is enabled in app settings
- Ensure app-level token has `connections:write` scope

## Architecture

The Slack channel uses:
- **slack-bolt** framework for event handling
- **Socket Mode** for real-time WebSocket connection (no public URL needed)
- **AsyncSocketModeHandler** for non-blocking async operation

Messages flow:
```
Slack → Socket Mode → SlackChannel → Bus → GatewayManager → Agent
```

Responses flow:
```
Agent → OutboundMessage → SlackChannel → Slack API
```
