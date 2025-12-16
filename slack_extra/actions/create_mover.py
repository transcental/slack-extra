from blockkit import Input
from blockkit import Modal
from blockkit import MultiChannelsSelect
from blockkit import PlainTextInput
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient


async def create_mover_handler(
    ack: AsyncAck, client: AsyncWebClient, respond: AsyncRespond, body: dict
):
    await ack()

    view = (
        Modal()
        .callback_id("setup_move")
        .title("Setup Mover")
        .add_block(
            Section(
                text="Users who join any of the channels you select will be added to all other selected channels automatically. You must be a workspace admin or channel manager of all selected channels to set this up."
            )
        )
        .add_block(
            Input()
            .label("Name")
            .element(PlainTextInput().action_id("name"))
            .block_id("name")
        )
        .add_block(
            Input()
            .label("Channels")
            .element(MultiChannelsSelect().action_id("channels"))
            .block_id("channels")
        )
        .private_metadata("create")
        .submit("Setup!")
        .close("Cancel")
    ).build()

    await client.views_push(view=view, trigger_id=body["trigger_id"])
