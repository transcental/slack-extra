from slack_extra.config import config
from slack_extra.utils.logging import send_heartbeat


async def get_channel_managers(channel_id: str) -> list[str]:
    from slack_extra.env import env

    data = {
        "token": config.slack.xoxc_token,
        "entity_id": channel_id,
        "role_id": "Rl0A",
    }
    headers = {"Cookie": f"d={config.slack.xoxd_token}"}

    async with env.http.post(
        "https://slack.com/api/admin.roles.entity.listAssignments?_x_gantry=false",
        data=data,
        headers=headers,
    ) as resp:
        res = await resp.json()
        if res.get("ok"):
            role_assigments = res.get("role_assignments")
            if not role_assigments:
                return []
            assignment = [
                assignment
                for assignment in role_assigments
                if assignment.get("role_id") == "Rl0A"
            ][0]
            channel_managers = assignment.get("users")
            return channel_managers
        else:
            await send_heartbeat(
                f":warning: Failed to get channel managers for <#{channel_id}> - {channel_id}",
                messages=[f"```{res}```"],
            )
            return []


async def is_channel_manager(user_id: str, channel_id: str):
    from slack_extra.env import env

    if await is_admin(user_id):
        return True

    channel_managers = await get_channel_managers(channel_id)
    if channel_managers:
        return user_id in channel_managers

    channel_info = await env.slack_client.conversations_info(channel=channel_id)
    creator = channel_info.get("channel", {}).get("creator")
    return user_id == creator


async def is_admin(user_id: str):
    from slack_extra.env import env

    user_data = await env.slack_client.users_info(user=user_id)
    user = user_data.get("user", {})
    is_admin = user.get("is_admin")
    is_owner = user.get("is_owner")
    is_primary_owner = user.get("is_primary_owner")
    return is_admin or is_owner or is_primary_owner
