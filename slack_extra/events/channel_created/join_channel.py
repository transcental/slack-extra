from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config


async def join_channel_handler(body: dict, event: dict, client: AsyncWebClient):
    channel = event["channel"]["id"]
    user = event["channel"]["creator"]
    if config.environment == "production" or user == config.slack.maintainer_id:
        await client.conversations_join(channel=channel)
        await client.chat_postEphemeral(
            channel=channel,
            user=user,
            text="Hey! I provide useful features to improve your experience on Slack! If you don't want me here please bear in mind that several features may stop working. You can remove me using `/kick @Slack Extra`",
        )
