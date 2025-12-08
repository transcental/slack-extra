from blockkit import Actions
from blockkit import Button
from blockkit import Input
from blockkit import Modal
from blockkit import Option
from blockkit import Section
from blockkit import StaticSelect
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.tables import MigrationConfig


async def edit_movers_handler(
    ack: AsyncAck, client: AsyncWebClient, respond: AsyncRespond, body: dict
):
    await ack()

    user_id = body["user"]["id"]

    configs = await MigrationConfig.objects().where(MigrationConfig.user_id == user_id)
    select = StaticSelect().action_id("config")
    for config in configs:
        select.add_option(Option(text=config.name, value=str(config.id)))

    view = (
        Modal()
        .callback_id("edit_move")
        .title("Edit Movers")
        .add_block(Section(text="You can edit your existing auto move configs here!"))
        .add_block(
            (
                Input()
                .label("Select a config to edit")
                .element(select)
                .block_id("config")
            )
            if configs
            else (
                Actions().add_element(
                    Button()
                    .text("No configs found! Create one?")
                    .action_id("create_mover")
                    .style("primary")
                )
            )
        )
        .submit("Edit!")
        .close("Back")
    ).build()

    await client.views_push(view=view, trigger_id=body["trigger_id"])
