import re
from typing import Optional

from blockkit import Button
from blockkit import Message
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.utils.logging import send_heartbeat


async def spoiler_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
    spoiler: Optional[str] = None,
):
    await ack()
    text = spoiler

    try:
        channel_info = await client.conversations_info(channel=channel)
    except SlackApiError as e:
        if e.response["error"] == "channel_not_found":
            await respond(
                "i couldn't find that channel :(\ntry making sure i'm in the channel?"
            )
            return
        elif e.response["error"] == "not_in_channel":
            channel_info = await client.conversations_join(channel=channel)
        else:
            await respond("oops, something went wrong fetching that channel!")
            await send_heartbeat(
                heartbeat="Error in spoiler_handler",
                messages=[f"Error details: {e.response['error']}"],
            )
            return

    in_channel = channel_info.get("channel", {}).get("is_channel", False)
    if not in_channel:
        await respond("I need access to the channel! Please add me :3")
        return

    if text:
        spoiler_regex = r"\|\|(.*?)\|\|"
        spoilers = re.findall(spoiler_regex, text)
        new_text = text
        if spoilers:
            for phrase in spoilers:
                new_text = new_text.replace(f"||{phrase}||", "`[spoiler hidden]`")
        else:
            return await respond(
                "how do you expect me to spoiler text without spoilers :disappointed:"
            )

        message = (
            Message().add_block(
                Section(text=new_text)
                .accessory(
                    Button()
                    .text(f"View {'spoiler' if len(spoilers) == 1 else 'spoilers'}")
                    .action_id("view_spoiler")
                    .value("metadata")
                )
                .text(new_text)
            )
        ).build()

        parsed_text = text.replace("||", "")
        if "*" not in parsed_text:
            for phrase in spoilers:
                parsed_text = parsed_text.replace(phrase, f"*{phrase}*")
        message["metadata"] = {
            "event_type": "spoiler",
            "event_payload": {"text": parsed_text, "poster": performer},
        }

        slack_user = await client.users_info(user=performer)
        display_name = (
            slack_user.get("user", {}).get("profile", {}).get("display_name")
            or slack_user.get("user", {}).get("real_name")
            or "Unknown User"
        )
        pfp = slack_user.get("user", {}).get("profile", {}).get("image_512") or None
        await client.chat_postMessage(
            channel=channel, username=display_name, icon_url=pfp, **message
        )
