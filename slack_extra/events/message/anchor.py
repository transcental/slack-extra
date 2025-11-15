import json

from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.tables import AnchorConfig


async def anchor_message_handler(body: dict, event: dict, client: AsyncWebClient):
    channel = event["channel"]
    subtype = event.get("subtype")
    subtypes = ["bot_message", "file_share", "me_message", "thread_broadcast", None]

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

    await client.chat_delete(
        channel=channel, ts=anchor_config.message_ts, token=installation.user_token
    )

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
    )

    await AnchorConfig.update({AnchorConfig.message_ts: msg["ts"]}).where(
        AnchorConfig.channel_id == channel
    )

    await client.pins_add(channel=channel, timestamp=msg["ts"])
