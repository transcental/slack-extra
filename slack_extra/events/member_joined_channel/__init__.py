from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.events.member_joined_channel.move import mover_handler


async def member_joined_channel_handler(
    ack: AsyncAck, body: dict, event: dict, client: AsyncWebClient
):
    await ack()

    await mover_handler(body, event, client)
