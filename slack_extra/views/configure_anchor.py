from slack_bolt.async_app import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.tables import AnchorConfig


async def configure_anchor_handler(ack: AsyncAck, body: dict, client: AsyncWebClient):
    await ack()

    user_id = body["user"]["id"]
    view = body["view"]
    values = view["state"]["values"]
    channel, operation = view.get("private_metadata", "").split("|")
    rich_text_value = values["anchor_input"]["anchor_input"]["rich_text_value"]

    installation_store = PiccoloInstallationStore()
    installation = await installation_store.async_find_installation(
        user_id=user_id, team_id=None, enterprise_id=None
    )
    if not installation or not installation.user_token:
        await client.chat_postMessage(
            channel=user_id,
            text="It seems you need to authorise the app again. Please re-run the `/se anchor` command to start the process.",
        )
        return

    user_token = installation.user_token
    if installation.user_scopes and "pins:write" in installation.user_scopes:
        pin_token = user_token
    else:
        pin_token = config.slack.bot_token

    msg = await client.chat_postMessage(
        channel=channel,
        blocks=[rich_text_value],
        metadata={
            "event_type": "anchor",
            "event_payload": {
                "channel": channel,
            },
        },
        token=user_token,
    )
    await client.pins_add(channel=channel, timestamp=msg["ts"], token=pin_token)

    match operation:
        case "create":
            anchor_config = AnchorConfig(
                channel_id=channel,
                message=rich_text_value,
                enabled=True,
                message_ts=msg["ts"],
                user_id=user_id,
            )
            await AnchorConfig.insert(anchor_config)
            return
        case "edit":
            anchor_config = (
                await AnchorConfig.objects()
                .where(AnchorConfig.channel_id == channel)
                .first()
            )
            if anchor_config:
                await anchor_config.update(
                    {
                        AnchorConfig.message: rich_text_value,
                        AnchorConfig.message_ts: msg["ts"],
                        AnchorConfig.user_id: user_id,
                    }
                ).where(AnchorConfig.channel_id == channel)
                return
            else:
                await client.chat_postMessage(
                    channel=user_id,
                    text=f"No existing Anchor configuration found for this channel. Please message <@{config.slack.maintainer_id}>",
                )
                return
