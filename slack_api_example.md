# Slack API Examples

## Using the Streaming API with Slack

The streaming API now supports enhanced Slack integration with the ability to specify:
- Channel types (public, private, direct messages)
- Data types (messages, files)
- Optional Slack bot token

### Example 1: Basic Slack Integration

```bash
curl -X POST http://192.168.1.36:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "uri": "slack://general",
    "trigger": "manual",
    "metadata": {
      "slack": {
        "channelTypes": ["public"],
        "dataTypes": ["messages"]
      }
    }
  }'
```

### Example 2: Comprehensive Slack Integration

```bash
curl -X POST http://192.168.1.36:5001/api/streaming \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "uri": "slack://all",
    "trigger": "manual",
    "metadata": {
      "slack": {
        "channelTypes": ["public", "private", "dm"],
        "dataTypes": ["messages", "files"],
        "slackBotToken": "xoxb-your-slack-bot-token"
      }
    }
  }'
```

### Example 3: Using the Dedicated Slack Endpoint

```bash
curl -X POST http://192.168.1.36:5001/fetch-from-slack \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["public", "private"],
    "dataTypes": ["messages", "files"],
    "slackBotToken": "xoxb-your-slack-bot-token"
  }'
```

## Getting a Slack Bot Token

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" and select "From scratch"
3. Name your app and select your workspace
4. Go to "OAuth & Permissions" in the sidebar
5. Under "Bot Token Scopes", add the following scopes:
   - `channels:history` - View messages in public channels
   - `channels:read` - View basic information about public channels
   - `files:read` - View files shared in channels
   - `groups:history` - View messages in private channels
   - `groups:read` - View basic information about private channels
   - `im:history` - View messages in direct messages
   - `im:read` - View basic information about direct messages
   - `users:read` - View basic information about users
6. Install the app to your workspace
7. Copy the "Bot User OAuth Token" that starts with `xoxb-`

## Notes

- The Slack bot token can be provided in three ways:
  1. Directly in the API call (as shown in examples 2 and 3)
  2. Saved in `user_credentials/slack_credentials.env` file
  3. Saved in the default `.env` file
- The system will check for the token in the order listed above
- If no token is found, the API will return an error
- The `uri` parameter in the streaming API is currently not used for Slack integration but is required by the API
