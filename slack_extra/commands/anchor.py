from blockkit import Divider
from blockkit import Input
from blockkit import Modal
from blockkit import RichTextInput
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.tables import AnchorConfig
from slack_extra.utils.oauth import generate_oauth_url
from slack_extra.utils.slack import is_channel_manager


async def anchor_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
    command: dict,
    action: str | None,
):
    await ack()

    allowed = await is_channel_manager(performer, channel)
    if not allowed:
        await respond(
            "looks like you're not a channel manager! only channel managers can configure Anchor."
        )
        return

    anchor_config = (
        await AnchorConfig.objects().where(AnchorConfig.channel_id == channel).first()
    )

    if action and anchor_config:
        match action:
            case "enable":
                await AnchorConfig.update({AnchorConfig.enabled: True}).where(
                    AnchorConfig.channel_id == channel
                )
                return await respond("yay! i've enabled anchor for this channel :D")
            case "disable":
                await AnchorConfig.update({AnchorConfig.enabled: False}).where(
                    AnchorConfig.channel_id == channel
                )
                return await respond("hey! i've disabled anchor for this channel :)")

    installation_store = PiccoloInstallationStore()
    installation = await installation_store.async_find_installation(
        user_id=performer, team_id=None, enterprise_id=None
    )
    if not installation:
        oauth_url = await generate_oauth_url(user_scopes=["chat:write"])
        await respond(
            f"Hi there! To configure Anchor, please authorise me by clicking this link: {oauth_url}"
        )
        return
    elif installation.user_scopes and "chat:write" not in installation.user_scopes:
        scopes: list = installation.user_scopes  # type: ignore (This is a list)
        scopes.append("chat:write")
        oauth_url = await generate_oauth_url(user_scopes=scopes)
        await respond(
            f"Hi there! To configure Anchor, please authorise me by clicking this link: {oauth_url}"
        )
        return
    else:
        if not installation.user_token:
            await respond(
                "Hi there! To configure Anchor, please authorise me by clicking this link: "
                f"{await generate_oauth_url(user_scopes=['chat:write'])}"
            )
            return

    enabled = False

    if anchor_config:
        enabled = anchor_config.enabled

    modal = (
        Modal()
        .callback_id("configure_anchor")
        .title("Anchor Configuration")
        .add_block(
            Section(
                text=f"_You are editing the Anchor configuration for <#{channel}>._",
            )
        )
        .add_block(Divider())
        .add_block(
            Section(
                text=f":neodog: Anchor is {'enabled' if enabled else 'disabled'} for this channel!"
                if anchor_config
                else ":neodog: Anchor is not yet configured for this channel."
            )
        )
        .add_block(
            Input()
            .label("Anchored message content")
            .element(
                RichTextInput()
                .action_id("anchor_input")
                .placeholder("deep at the bottom of the ocean lies....")
            )
            .block_id("anchor_input")
        )
    )

    modal.private_metadata(f"{channel}|{'edit' if anchor_config else 'create'}")
    modal.close("Cancel")
    modal.submit("Edit" if anchor_config else "Create")

    await client.views_open(
        trigger_id=command.get("trigger_id"),
        view=modal.build(),
    )
