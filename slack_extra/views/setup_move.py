from blockkit import Modal
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.tables import MigrationChannel
from slack_extra.tables import MigrationConfig
from slack_extra.utils.logging import send_heartbeat
from slack_extra.utils.slack import is_channel_manager


async def setup_move_handler(ack: AsyncAck, body: dict, client: AsyncWebClient):
    user_id = body["user"]["id"]
    view = body["view"]
    values = view["state"]["values"]
    name = values["name"]["name"]["value"]
    channels = values["channels"]["channels"]["selected_channels"]

    allowed = [await is_channel_manager(user_id, c) for c in channels]

    if not all(allowed):
        return await ack(
            response_action="errors",
            errors={
                "channels": "You must be a channel manager of all selected channels to set up migrations."
            },
        )

    exist = []
    for c in channels:
        db_channel = (
            await MigrationChannel.objects()
            .where(MigrationChannel.channel_id == c)
            .first()
        )
        if db_channel:
            exist.append(c)

    if exist:
        existing_channels = ", ".join([f"<#{c}>" for c in exist])
        return await ack(
            response_action="errors",
            errors={
                "channels": f"These channels are already configured for migration: {existing_channels}"
            },
        )

    for c in channels:
        try:
            await client.conversations_join(channel=c)
        except Exception as e:
            await send_heartbeat(f"Error joining channel {c} for user {user_id}: {e}")
            return await ack(
                response_action="errors",
                errors={
                    "channels": f"An unexpected error occurred while joining <#{c}>. Please ensure the bot is invited to the channel and try again."
                },
            )

    try:
        async with MigrationConfig._meta.db.transaction():
            conf = await MigrationConfig.insert(
                MigrationConfig(name=name, user_id=user_id)
            ).returning(MigrationConfig.id)
            config_id = conf[0]["id"]
            migration_channels = [
                MigrationChannel(channel_id=c, config=config_id) for c in channels
            ]
            await MigrationChannel.insert(*migration_channels)
    except Exception as e:
        await send_heartbeat(f"Error setting up migration for user {user_id}: {e}")
        return await ack(
            response_action="errors",
            errors={
                "name": "An unexpected error occurred while setting up the migration. Please try again later."
            },
        )

    view = (
        Modal()
        .title("Migration Setup!")
        .add_block(Section(text="Your migration has been setup successfully :D"))
        .close("Yippee!")
    ).build()
    await ack(response_action="update", view=view)
