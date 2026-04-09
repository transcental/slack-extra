from typing import Literal

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.utils.slack import add_channel_manager
from slack_extra.utils.slack import get_channel_managers
from slack_extra.utils.slack import is_channel_manager
from slack_extra.utils.slack import remove_channel_manager


async def manager_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    location: str,
    raw_command: str,
    action: Literal["get", "add", "remove"],
    user: str | None = None,
):
    await ack()
    ran = f"\n_You ran `{raw_command}`_"

    managers = await get_channel_managers(location)
    match action:
        case "get":
            if performer in managers:
                return await respond(f"You're already a channel manager!{ran}")

            allowed = await is_channel_manager(performer, location)
            if managers and (not allowed or performer in managers):
                manager_mentions = ", ".join([f"<@{mgr}>" for mgr in managers])
                return await respond(
                    f"There are already managers for this channel - please get one of them to give you channel manager.\nManagers: {manager_mentions}{ran}"
                )

            channel_info = await client.conversations_info(channel=location)
            creator = channel_info.get("channel", {}).get("creator")

            if not creator and not allowed:
                return await respond(
                    f"Something went wrong fetching channel info!{ran}"
                )

            success, res = await add_channel_manager(performer, location)

            if success:
                return await respond(
                    f"You're now the channel manager for <#{location}>{ran}"
                )
            else:
                if res.get("error", "") == "no_valid_users":
                    return await respond(
                        f"You must be in the channel to be set as a channel manager{ran}"
                    )
                return await respond(
                    f"Something went wrong setting you as the channel manager :({ran}"
                )
        case "add" | "remove":
            if not user:
                return await respond(f"You need to specify a user to update!{ran}")

            allowed = await is_channel_manager(performer, location)
            if not allowed:
                return await respond(
                    f"You need to be a channel manager to manage channel managers! Created this channel? Try `/se manager get`{ran}"
                )
            if action == "add":
                if user in managers:
                    return await respond(
                        f"<@{user}> is already a channel manager!{ran}"
                    )
                success, res = await add_channel_manager(user, location)
                if success:
                    return await respond(f"<@{user}> is now a channel manager!{ran}")
                else:
                    error = res.get("error", "")
                    if error == "no_valid_users":
                        return await respond(
                            f"<@{user}> must be in the channel to be a channel manager!{ran}"
                        )
                    else:
                        return await respond(
                            f"Failed to add <@{user}> as a channel manager - `{error}`!{ran}"
                        )
            elif action == "remove":
                if user not in managers:
                    return await respond(f"<@{user}> is not a channel manager!{ran}")
                success, res = await remove_channel_manager(user, location)
                if success:
                    return await respond(
                        f"<@{user}> is no longer a channel manager!{ran}"
                    )
                else:
                    error = res.get("error", "")
                    return await respond(
                        f"Failed to remove <@{user}> as a channel manager - `{error}`!{ran}"
                    )
