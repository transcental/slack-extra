from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.events.channel_created.join_channel import join_channel_handler
from slack_extra.events.message.anchor import anchor_message_handler


async def channel_created_handler(
    ack: AsyncAck, body: dict, event: dict, client: AsyncWebClient
):
    await ack()

    await anchor_message_handler(body, event, client)
    await join_channel_handler(body, event, client)
