from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config


async def send_heartbeat(
    heartbeat: str, messages: list[str] = [], client: AsyncWebClient | None = None
):
    if not client:
        from slack_extra.env import env

        client = env.slack_client
    if config.slack.heartbeat_channel:
        msg = await client.chat_postMessage(
            channel=config.slack.heartbeat_channel, text=heartbeat
        )
        if messages:
            for message in messages:
                await client.chat_postMessage(
                    channel=config.slack.heartbeat_channel,
                    text=message,
                    thread_ts=msg["ts"],
                )
