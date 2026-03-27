import random

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient


async def love_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    location: str,
    command: dict,
):
    await ack()
    responses = [
        "awh, i love you too <3",
        "<3",
        ":orange_heart:",
        ":heart-eng:",
        "you're so sweet :pleading_face:",
        ":rac_shy:",
    ]
    await respond(random.choice(responses))
