from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.tables import MigrationChannel
from slack_extra.utils.logging import send_heartbeat


async def mover_handler(body: dict, event: dict, client: AsyncWebClient):
    channel_id = event["channel"]
    user_id = event["user"]

    migration_channel = await MigrationChannel.objects().where(
        MigrationChannel.channel_id == channel_id
    )
    if migration_channel:
        migration_channel = migration_channel[0]
        channels = await MigrationChannel.objects().where(
            MigrationChannel.config == migration_channel.config
        )
        channels = [chan.channel_id for chan in channels]
        for chan in channels:
            if chan != channel_id:
                try:
                    await client.conversations_invite(channel=chan, users=[user_id])
                except SlackApiError as e:
                    if e.response["error"] == "already_in_channel":
                        pass
                    else:
                        await send_heartbeat(
                            f"Error inviting user {user_id} to channel {chan}: {e}"
                        )
        c_str = ", ".join([f"<#{chan}>" for chan in channels if chan != channel_id])
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"hi! i've just added you to {c_str}!\nyou should check them out :)",
        )
