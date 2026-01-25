from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.utils.oauth import generate_oauth_url
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

    if (channel_id.startswith("D") and author == user_id) or author == user_id:
        # do oauth logic and use user token
        team_info = await client.team_info()
        team_id = team_info.get("team", {}).get("id") or "T0266FRGM"

        installation_store = PiccoloInstallationStore()
        installation = await installation_store.async_find_installation(
            enterprise_id=None, team_id=team_id, user_id=user_id
        )

        if not installation or not installation.user_token:
            oauth_url = await generate_oauth_url(user_scopes=["chat:write"])

            await respond(
                f"Click here to authorise: <{oauth_url}|Authorise App>\n\n"
                f"_This will grant the app permission to delete your messages on your behalf with the `chat:write` scope._"
            )
            return
        if installation.user_scopes and "chat:write" not in installation.user_scopes:
            scopes: list = installation.user_scopes  # type: ignore (This is a list)
            scopes.append("chat:write")
            oauth_url = await generate_oauth_url(user_scopes=scopes)

            await respond(
                f"Click here to authorise: <{oauth_url}|Authorise App>\n\n"
                f"_This will grant the app permission to delete your messages on your behalf with the `chat:write` scope._"
            )
            return

        user_token = installation.user_token
        await client.chat_delete(ts=ts, channel=channel_id, token=user_token)
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
