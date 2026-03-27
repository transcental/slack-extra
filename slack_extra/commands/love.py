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
        ":amber_heart:",
        ":heart-eng:",
        "you're so sweet :pleading_face:",
        ":rac_shy:",
        ":3",
        ":rac_love:",
        ":neodog_heart:",
        "love you too <3",
        ":dogheart:",
    ]
    await respond(random.choice(responses))
