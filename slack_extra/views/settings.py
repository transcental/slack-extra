from blockkit import Modal
from blockkit import Section
from slack_bolt.async_app import AsyncAck

from slack_extra.preferences import set_move_enabled


async def settings_view_handler(ack: AsyncAck, body: dict):
    user_id = body["user"]["id"]
    values = body["view"]["state"]["values"]
    selected_options = values["move_settings"]["move_settings"].get(
        "selected_options", []
    )
    enabled_moves = {option["value"] for option in selected_options}

    await set_move_enabled(user_id, "manual", "manual" in enabled_moves)
    await set_move_enabled(user_id, "auto", "auto" in enabled_moves)

    view = (
        Modal()
        .title("Saved!")
        .add_block(Section(text="Your preferences have been saved! :D"))
        .close("Done")
    ).build()
    await ack(response_action="update", view=view)
