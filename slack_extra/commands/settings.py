from blockkit import Checkboxes
from blockkit import Input
from blockkit import Modal
from blockkit import Option
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.preferences import get_user_settings
from slack_extra.preferences import set_move_enabled


MANUAL_MOVE_OPTION = Option(
    text="Manual moves",
    value="manual",
    description="Allow being added to a single channel as a one off by a channel manager running a command.",
)
AUTO_MOVE_OPTION = Option(
    text="Automatic moves",
    value="auto",
    description="Allow being automatically added to related channels (eg. YSWS bulletin, help & chat)",
)


async def settings_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    command: dict,
):
    await ack()

    settings = await get_user_settings(performer)
    initial_options = []
    if settings is None or not settings.manual_move_opt_out:
        initial_options.append(MANUAL_MOVE_OPTION)
    if settings is None or not settings.auto_move_opt_out:
        initial_options.append(AUTO_MOVE_OPTION)

    move_checkboxes = Checkboxes(action_id="move_settings")
    move_checkboxes.add_option(MANUAL_MOVE_OPTION)
    move_checkboxes.add_option(AUTO_MOVE_OPTION)
    for option in initial_options:
        move_checkboxes.add_initial_option(option)

    view = (
        Modal()
        .callback_id("settings")
        .title("Settings")
        .add_block(Section(text="Choose how Slack Extra can add you to channels."))
        .add_block(
            Input().label("Move").element(move_checkboxes).block_id("move_settings")
        )
        .submit("Save")
        .close("Cancel")
    ).build()

    await client.views_open(trigger_id=command["trigger_id"], view=view)


async def settings_move_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    move_type: str,
    state: str,
):
    await ack()

    enabled = state == "on"
    await set_move_enabled(performer, move_type, enabled)

    move_label = "manual moves" if move_type == "manual" else "automatic moves"
    state_label = "on" if enabled else "off"
    await respond(f"Turned {move_label} {state_label} for you.")
