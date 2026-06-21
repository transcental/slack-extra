from slack_extra.tables import UserSettings


async def get_user_settings(user_id: str) -> UserSettings | None:
    return await UserSettings.objects().where(UserSettings.user_id == user_id).first()


async def set_move_enabled(user_id: str, move_type: str, enabled: bool):
    opt_out = not enabled
    if move_type == "manual":
        column = UserSettings.manual_move_opt_out
        insert_values = {"manual_move_opt_out": opt_out}
    elif move_type == "auto":
        column = UserSettings.auto_move_opt_out
        insert_values = {"auto_move_opt_out": opt_out}
    else:
        raise ValueError(f"unknown type?? {move_type}")

    settings = await get_user_settings(user_id)
    if settings:
        await UserSettings.update({column: opt_out}).where(
            UserSettings.user_id == user_id
        )
    else:
        await UserSettings.insert(UserSettings(user_id=user_id, **insert_values))


async def is_move_opted_out(user_id: str, move_type: str) -> bool:
    settings = await get_user_settings(user_id)
    if settings is None:
        return False
    if move_type == "manual":
        return settings.manual_move_opt_out
    if move_type == "auto":
        return settings.auto_move_opt_out
    raise ValueError(f"unknown type?? {move_type}")
