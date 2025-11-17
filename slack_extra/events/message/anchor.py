import json

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.tables import AnchorConfig
from slack_extra.utils.logging import send_heartbeat


async def anchor_message_handler(body: dict, event: dict, client: AsyncWebClient):
    channel = event["channel"]
    subtype = event.get("subtype")
    subtypes = [
        "bot_message",
        "file_share",
        "me_message",
        "thread_broadcast",
        None,
        "channel_convert_to_private",
        "channel_convert_to_public",
        "channel_join",
        "channel_leave",
        "channel_name",
        "channel_purpose",
        "channel_posting_permissions",
        "channel_topic",
        "channel_unarchive",
        "group_join",
        "group_leave",
        "group_name",
        "group_purpose",
        "group_topic",
        "group_unarchive",
    ]

    if subtype not in subtypes:
        return

    anchor_config = (
        await AnchorConfig.objects().where(AnchorConfig.channel_id == channel).first()
    )
    if not anchor_config or not anchor_config.enabled:
        return

    thread_ts = event.get("thread_ts")

    if thread_ts == anchor_config.message_ts:
        await client.chat_delete(
            channel=channel, ts=event["ts"], token=config.slack.user_token
        )
        await client.chat_postEphemeral(
            channel=channel,
            user=event["user"],
            text="Hey! Please don't reply directly to the anchor message. Instead, start a new thread.",
            thread_ts=anchor_config.message_ts,
        )

    if thread_ts and not subtype == "thread_broadcast":
        return

    metadata = event.get("metadata")
    if metadata and metadata.get("event_type") == "anchor":
        return

    installation_store = PiccoloInstallationStore()
    installation = await installation_store.async_find_installation(
        user_id=anchor_config.user_id, team_id=None, enterprise_id=None
    )

    if not installation or not installation.user_token:
        return

    try:
        await client.chat_delete(
            channel=channel, ts=anchor_config.message_ts, token=installation.user_token
        )
    except SlackApiError as e:
        await send_heartbeat(
            f"Failed to delete anchor message in channel <#{channel}>: {e.response['error']}"
        )

    try:
        msg = await client.chat_postMessage(
            channel=channel,
            blocks=[json.loads(anchor_config.message)],
            metadata={
                "event_type": "anchor",
                "event_payload": {
                    "channel": channel,
                },
            },
            token=installation.user_token,
            unfurl_links=True,
            unfurl_media=True,
        )
    except SlackApiError as e:
        error = e.response["error"]
        await send_heartbeat(
            f"Failed to post anchor message in channel <#{channel}> with error {error}."
        )
        if error in ["invalid_auth", "no_permission", "token_expired", "token_revoked"]:
            await AnchorConfig.update({AnchorConfig.enabled: False}).where(
                AnchorConfig.channel_id == channel
            )
            await client.chat_postMessage(
                channel=anchor_config.user_id,
                text=f"hey! i had to disable anchor messages in <#{channel}> because i got this error - `{error}`.\nif you're confused, maybe check out <#{config.slack.support_channel}> for help!",
                token=config.slack.bot_token,
            )
        return

    await AnchorConfig.update({AnchorConfig.message_ts: msg["ts"]}).where(
        AnchorConfig.channel_id == channel
    )

    if installation.user_scopes and "pins:write" in installation.user_scopes:
        pin_token = installation.user_token
    else:
        pin_token = config.slack.bot_token

    await client.pins_add(channel=channel, timestamp=msg["ts"], token=pin_token)
