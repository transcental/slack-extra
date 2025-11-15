from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.events.message.anchor import anchor_message_handler


async def message_handler(
    ack: AsyncAck, body: dict, event: dict, client: AsyncWebClient
):
    await ack()

    await anchor_message_handler(body, event, client)
