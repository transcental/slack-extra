from typing import Literal

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient


async def group_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    action: Literal["join", "leave"],
    group: str,
    raw_command: str,
):
    await ack()
    ran = f"\n_You ran `{raw_command}`_"
    try:
        users = await client.usergroups_users_list(usergroup=group)
    except SlackApiError as e:
        await respond(f"Error fetching group members: {e.response['error']}{ran}")
        return
    users = users.get("users", [])

    match action:
        case "join":
            if performer in users:
                await respond(f"you're already in <!subteam^{group}>!.{ran}")
                return
            users.append(performer)
            try:
                await client.usergroups_users_update(usergroup=group, users=users)
            except SlackApiError as e:
                await respond(
                    f"Error adding you to the group: {e.response['error']}{ran}"
                )
                return
            await respond(f"i just added you to <!subteam^{group}>!")
        case "leave":
            if performer not in users:
                await respond(
                    f"how do you expect to leave a group you're not in? :p{ran}"
                )
                return
            users.remove(performer)
            try:
                await client.usergroups_users_update(usergroup=group, users=users)
            except SlackApiError as e:
                await respond(
                    f"Error removing you from the group: {e.response['error']}{ran}"
                )
                return
            await respond(f"just removed you from <!subteam^{group}> :)")
