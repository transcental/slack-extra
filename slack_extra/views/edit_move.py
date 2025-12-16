from blockkit import Input
from blockkit import Modal
from blockkit import MultiChannelsSelect
from blockkit import PlainTextInput
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.tables import MigrationChannel
from slack_extra.tables import MigrationConfig
from slack_extra.utils.error import generate_error_view


async def edit_move_handler(ack: AsyncAck, body: dict, client: AsyncWebClient):
    view = body["view"]
    values = view["state"]["values"]
    config_val = int(values["config"]["config"]["selected_option"]["value"])

    migration = (
        await MigrationConfig.objects().where(MigrationConfig.id == config_val).first()
    )

    if not migration:
        view = generate_error_view(
            "No config found",
            f"We couldn't find your config! If you keep running into this, please post in {config.slack.support_channel}",
        )
        return await ack(response_action="update", view=view)

    channels = await MigrationChannel.objects().where(
        MigrationChannel.config == config_val
    )
    channels_list = [c.channel_id for c in channels]

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
            .element(PlainTextInput().action_id("name").initial_value(migration.name))
            .block_id("name")
        )
        .add_block(
            Input()
            .label("Channels")
            .element(
                MultiChannelsSelect()
                .action_id("channels")
                .initial_channels(*channels_list)
            )
            .block_id("channels")
        )
        .private_metadata(f"edit:{config_val}")
        .submit("Update!")
        .close("Cancel")
    ).build()

    return await ack(response_action="push", view=view)
