import logging

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.utils.oauth import generate_oauth_url

logger = logging.getLogger(__name__)

MANAGER_FIELD_ID = "Xf09727DH1J8"


async def _is_admin_or_owner(
    client: AsyncWebClient, user_id: str, team_id: str
) -> bool:
    try:
        user_info = await client.users_info(user=user_id)
        if not user_info.get("ok"):
            return False

        user_data = user_info.get("user", {})
        is_admin = user_data.get("is_admin", False)
        is_owner = user_data.get("is_owner", False)
        is_primary_owner = user_data.get("is_primary_owner", False)

        return is_admin or is_owner or is_primary_owner
    except SlackApiError as e:
        logger.error(f"Error checking user admin status: {e}")
        return False


async def _get_current_managers(client: AsyncWebClient, user_id: str) -> list[str]:
    try:
        profile_response = await client.users_profile_get(user=user_id)

        if not profile_response.get("ok"):
            logger.error(f"Failed to get user profile: {profile_response}")
            return []

        profile = profile_response.get("profile", {})
        fields = profile.get("fields", {})
        manager_field = fields.get(MANAGER_FIELD_ID, {})

        value = manager_field.get("value")
        if not value:
            return []

        if isinstance(value, str):
            return value.split(",")

        return []
    except SlackApiError as e:
        logger.error(f"Error fetching current managers: {e}")
        return []


async def _update_managers(
    client: AsyncWebClient, user_id: str, managers: list[str], token: str | None = None
) -> bool:
    try:
        profile = {
            "fields": {MANAGER_FIELD_ID: {"value": ",".join(managers), "alt": ""}}
        }

        if not token:
            token = config.slack.user_token

        response = await client.users_profile_set(
            user=user_id, token=token, profile=profile
        )

        return response.get("ok", False)
    except SlackApiError as e:
        logger.error(f"Error updating managers: {e}")
        return False


async def manager_add_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    manager: str,
    ran: str,
):
    await ack()

    user = performer

    team_info = await client.team_info()
    team_id = team_info.get("team", {}).get("id") or "T0266FRGM"

    is_privileged = await _is_admin_or_owner(client, performer, team_id)

    user_token = None
    if is_privileged:
        installation_store = PiccoloInstallationStore()
        installation = await installation_store.async_find_installation(
            enterprise_id=None, team_id=team_id, user_id=performer
        )

        if not installation or not installation.user_token:
            oauth_url = await generate_oauth_url(user_scopes=["users.profile:write"])

            await respond(
                f"⚠️ You are a workspace admin/owner and need to authorize with OAuth to edit your profile.\n\n"
                f"Click here to authorize: <{oauth_url}|Authorise App>\n\n"
                f"_This will grant the app permission to edit your profile on your behalf with the `users.profile:write` scope._{ran}"
            )
            return
        if (
            installation.user_scopes
            and "users.profile:write" not in installation.user_scopes
        ):
            scopes: list = installation.user_scopes  # type: ignore (This is a list)
            scopes.append("users.profile:write")
            oauth_url = await generate_oauth_url(user_scopes=scopes)

            await respond(
                f"⚠️ You are a workspace admin/owner and need to authorize with OAuth to edit your profile.\n\n"
                f"Click here to authorize: <{oauth_url}|Authorise App>\n\n"
                f"_This will grant the app permission to edit your profile on your behalf with the `users.profile:write` scope and any scopes you've previously authorised._{ran}"
            )
            return

        user_token = installation.user_token

    current_managers = await _get_current_managers(client, user)

    if manager in current_managers:
        await respond(f"<@{manager}> is already one of your managers.{ran}")
        return

    updated_managers = current_managers + [manager]

    success = await _update_managers(client, user, updated_managers, user_token)

    if success:
        await respond(f"added <@{manager}> as your manager!")
    else:
        await respond(f"i failed to add your manager. {ran}")


async def manager_remove_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    manager: str,
    ran: str,
):
    await ack()

    user = performer

    team_info = await client.team_info()
    team_id = team_info.get("team", {}).get("id") or "T0266FRGM"

    is_privileged = await _is_admin_or_owner(client, performer, team_id)

    user_token = None
    if is_privileged:
        installation_store = PiccoloInstallationStore()
        installation = await installation_store.async_find_installation(
            enterprise_id=None, team_id=team_id, user_id=performer
        )

        if not installation or not installation.user_token:
            oauth_url = await generate_oauth_url(user_scopes=["users.profile:write"])

            await respond(
                f"⚠️ You are a workspace admin/owner and need to authorize with OAuth to edit your profile.\n\n"
                f"Click here to authorize: <{oauth_url}|Authorize App>\n\n"
                f"_This will grant the app permission to edit your profile on your behalf with the `users.profile:write` scope._{ran}"
            )
            return

        user_token = installation.user_token

    current_managers = await _get_current_managers(client, user)
    logging.debug(f"{manager} vs {current_managers}")

    if manager not in current_managers:
        await respond(f"<@{manager}> is not one of your managers.{ran}")
        return

    updated_managers = [m for m in current_managers if m != manager]

    success = await _update_managers(client, user, updated_managers, user_token)

    if success:
        await respond(f"removed <@{manager}> as your manager.")
    else:
        await respond(f"i couldn't remove your manager :({ran}")


async def manager_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    action: str,
    manager: str,
    raw_command: str,
):
    ran = f"\n_You ran `{raw_command}`_"
    if action == "add":
        await manager_add_handler(ack, client, respond, performer, manager, ran)
    elif action == "remove":
        await manager_remove_handler(ack, client, respond, performer, manager, ran)
