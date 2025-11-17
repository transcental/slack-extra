from blockkit import FileInput
from blockkit import Input
from blockkit import Modal
from blockkit import RichTextInput
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient


async def spoiler_handler(
    ack: AsyncAck, respond: AsyncRespond, shortcut: dict, client: AsyncWebClient
):
    await ack()
    channel = shortcut["channel"]["id"]
    thread_ts = shortcut.get("message", {}).get("ts")
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
        .private_metadata(f"{channel};{thread_ts}")
        .submit("Send Spoiler")
        .close("Cancel")
    ).build()

    trigger_id = shortcut.get("trigger_id")
    await client.views_open(
        trigger_id=trigger_id,
        view=modal,
    )
