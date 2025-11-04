from slack_extra.config import config


async def is_channel_manager(user_id: str, channel_id: str):
    from slack_extra.env import env

    data = {"token": config.slack.xoxc_token, "entity_id": channel_id}
    headers = {"Cookie": f"d={config.slack.xoxd_token}"}
    user_data = await env.slack_client.users_info(user=user_id)
    user = user_data.get("user", {})
    is_admin = user.get("is_admin")
    is_owner = user.get("is_owner")
    is_primary_owner = user.get("is_primary_owner")
    if is_admin or is_owner or is_primary_owner:
        return True

    async with env.http.post(
        "https://slack.com/api/admin.roles.entity.listAssignments",
        data=data,
        headers=headers,
    ) as resp:
        res = await resp.json()
        if res.get("ok"):
            role_assignments = res.get("role_assignments", [{}]) or [{}]
            channel_managers = role_assignments[0].get("users", [])
            if channel_managers:
                return user_id in channel_managers

        channel_info = await env.slack_client.conversations_info(channel=channel_id)
        creator = channel_info.get("channel", {}).get("creator")
        return user_id == creator
    return False
