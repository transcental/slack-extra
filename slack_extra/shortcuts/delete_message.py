from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.utils.slack import is_admin
from slack_extra.utils.slack import is_channel_manager


async def delete_message_handler(
    ack: AsyncAck, respond: AsyncRespond, shortcut: dict, client: AsyncWebClient
):
    await ack()
    channel_id = shortcut.get("channel", {}).get("id")
    user_id = shortcut.get("user", {}).get("id")
    ts = shortcut.get("message_ts")
    if not channel_id or not user_id or not ts:
        return await respond("Something went quite badly wrong")
    bot_id = shortcut.get("message", {}).get("bot_id")
    author = shortcut.get("message", {}).get("user")

    if author == user_id:
        await client.chat_delete(
            ts=ts, channel=channel_id, token=config.slack.user_token
        )
        return

    admin = await is_admin(user_id)
    if admin:
        await client.chat_delete(
            ts=ts, channel=channel_id, token=config.slack.user_token
        )
        return

    if bot_id or author == "USLACKBOT":
        can_delete = await is_channel_manager(user_id, channel_id)
        if not can_delete:
            return await respond("Only the channel manager can delete these messages")
        await client.chat_delete(
            ts=ts, channel=channel_id, token=config.slack.user_token
        )
    else:
        await respond("Only messages from Slackbot or apps can be deleted")
