import re
from typing import Optional

from blockkit import Button
from blockkit import FileInput
from blockkit import Input
from blockkit import Message
from blockkit import Modal
from blockkit import RichTextInput
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
    raw_command: str,
    command: dict,
    spoiler: Optional[str] = None,
):
    await ack()
    ran = f"\n_You ran `{raw_command}`_"
    text = spoiler
    bold = True

    try:
        channel_info = await client.conversations_info(channel=channel)
    except SlackApiError as e:
        if e.response["error"] == "channel_not_found":
            await respond(
                f"i couldn't find that channel :(\ntry making sure i'm in the channel?{ran}"
            )
            return
        elif e.response["error"] == "not_in_channel":
            channel_info = await client.conversations_join(channel=channel)
        else:
            await respond(f"oops, something went wrong fetching that channel!{ran}")
            await send_heartbeat(
                heartbeat="Error in spoiler_handler",
                messages=[f"Error details: {e.response['error']}"],
            )
            return

    in_channel = channel_info.get("channel", {}).get("is_channel", False)
    if not in_channel:
        await respond(f"I need access to the channel! Please add me :3{ran}")
        return

    if text:
        spoiler_regex = r"\|\|(.*?)\|\|"
        spoilers = re.findall(spoiler_regex, text)
        new_text = text
        if spoilers:
            for phrase in spoilers:
                new_text = new_text.replace(f"||{phrase}||", "`[spoiler hidden]`")
        else:
            new_text = "`[spoiler hidden]`"
            spoilers = [text]
            bold = False

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
        if "*" not in parsed_text and bold:
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
    else:
        modal = (
            Modal()
            .callback_id("create_spoiler")
            .title("Send Spoiler 👀")
            .add_block(
                Section(
                    text="Please wrap the phrases you want spoilered in `||` (double vertical bars). For example, `This is a ||spoiler||.`"
                )
            )
            .add_block(
                Input()
                .label("Text")
                .element(
                    RichTextInput()
                    .action_id("spoiler_input")
                    .placeholder("did you know? orpheus loves ||heidi||!")
                )
                .block_id("spoiler_input")
            )
            .add_block(
                Input()
                .label("Files!")
                .element(FileInput().action_id("spoiler_files"))
                .optional(True)
                .block_id("spoiler_files")
            )
            .private_metadata(channel)
            .submit("Send Spoiler")
            .close("Cancel")
        ).build()

        trigger_id = command.get("trigger_id")
        await client.views_open(
            trigger_id=trigger_id,
            view=modal,
        )
