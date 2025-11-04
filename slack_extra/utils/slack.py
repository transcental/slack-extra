from slack_extra.config import config


async def is_channel_manager(user_id: str, channel_id: str):
    from slack_extra.env import env

    data = {"token": config.slack.xoxc_token, "entity_id": channel_id}
    headers = {"Cookie": f"d={config.slack.xoxd_token}"}

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
