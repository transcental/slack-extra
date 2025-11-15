import json
import logging
from datetime import datetime
from datetime import UTC

from slack_sdk.oauth.installation_store import Bot
from slack_sdk.oauth.installation_store import Installation
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.state_store.async_state_store import AsyncOAuthStateStore

from slack_extra.tables import SlackOAuthInstallation
from slack_extra.tables import SlackOAuthState

logger = logging.getLogger(__name__)


class PiccoloInstallationStore(AsyncInstallationStore):
    async def async_save(self, installation: Installation) -> None:
        logger.debug(f"Saving installation for team {installation.team_id}")

        await SlackOAuthInstallation.insert(
            SlackOAuthInstallation(
                team_id=installation.team_id,
                team_name=installation.team_name,
                enterprise_id=installation.enterprise_id,
                enterprise_name=installation.enterprise_name,
                bot_token=installation.bot_token,
                bot_id=installation.bot_id,
                bot_user_id=installation.bot_user_id,
                bot_scopes=installation.bot_scopes,
                user_id=installation.user_id,
                user_token=installation.user_token,
                user_scopes=installation.user_scopes,
                incoming_webhook_url=installation.incoming_webhook_url,
                incoming_webhook_channel=installation.incoming_webhook_channel,
                incoming_webhook_channel_id=installation.incoming_webhook_channel_id,
                incoming_webhook_configuration_url=installation.incoming_webhook_configuration_url,
                is_enterprise_install=installation.is_enterprise_install or False,
                token_type=installation.token_type or "bot",
                installed_at=datetime.now(UTC),
            )
        )

    async def async_find_installation(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        user_id: str | None = None,
        is_enterprise_install: bool | None = False,
    ) -> Installation | None:
        logger.debug(
            f"Finding installation: enterprise={enterprise_id}, team={team_id}, user={user_id}"
        )

        query = SlackOAuthInstallation.select().order_by(
            SlackOAuthInstallation.installed_at, ascending=False
        )

        if enterprise_id:
            query = query.where(SlackOAuthInstallation.enterprise_id == enterprise_id)
        if team_id:
            query = query.where(SlackOAuthInstallation.team_id == team_id)
        if user_id:
            query = query.where(SlackOAuthInstallation.user_id == user_id)

        result = await query.first()
        if not result:
            logger.debug("No installation found")
            return None

        return Installation(
            team_id=result["team_id"],
            team_name=result["team_name"],
            enterprise_id=result["enterprise_id"],
            enterprise_name=result["enterprise_name"],
            bot_token=result["bot_token"],
            bot_id=result["bot_id"],
            bot_user_id=result["bot_user_id"],
            bot_scopes=json.loads(result["bot_scopes"]),
            user_id=result["user_id"],
            user_token=result["user_token"],
            user_scopes=json.loads(result["user_scopes"]),
            incoming_webhook_url=result["incoming_webhook_url"],
            incoming_webhook_channel=result["incoming_webhook_channel"],
            incoming_webhook_channel_id=result["incoming_webhook_channel_id"],
            incoming_webhook_configuration_url=result[
                "incoming_webhook_configuration_url"
            ],
            is_enterprise_install=result["is_enterprise_install"],
            token_type=result["token_type"],
            installed_at=result["installed_at"].timestamp(),
        )

    async def async_find_bot(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        is_enterprise_install: bool | None = False,
    ) -> Bot | None:
        logger.debug(f"Finding bot: enterprise={enterprise_id}, team={team_id}")

        installation = await self.async_find_installation(
            enterprise_id=enterprise_id,
            team_id=team_id,
            is_enterprise_install=is_enterprise_install,
        )
        if installation:
            return installation.to_bot()
        return None

    async def async_delete_installation(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        user_id: str | None = None,
    ) -> None:
        logger.debug(
            f"Deleting installation: enterprise={enterprise_id}, team={team_id}, user={user_id}"
        )

        query = SlackOAuthInstallation.delete()

        if enterprise_id:
            query = query.where(SlackOAuthInstallation.enterprise_id == enterprise_id)
        if team_id:
            query = query.where(SlackOAuthInstallation.team_id == team_id)
        if user_id:
            query = query.where(SlackOAuthInstallation.user_id == user_id)

        await query


class PiccoloOAuthStateStore(AsyncOAuthStateStore):
    async def async_consume(self, state: str) -> bool:
        logger.debug(f"Consuming OAuth state: {state}")

        result = await (
            SlackOAuthState.select().where(SlackOAuthState.state == state).first()
        )

        if not result:
            logger.debug("State not found")
            return False

        if result["expire_at"] < datetime.now(UTC).timestamp():
            logger.debug("State expired")
            await SlackOAuthState.delete().where(SlackOAuthState.state == state)
            return False

        await SlackOAuthState.delete().where(SlackOAuthState.state == state)
        return True

    async def async_issue(self, *, expiration_seconds: int = 600) -> str:
        import secrets

        state = secrets.token_urlsafe(32)
        expire_at = int(datetime.now(UTC).timestamp()) + expiration_seconds

        logger.debug(f"Issuing OAuth state: {state}")

        await SlackOAuthState.insert(SlackOAuthState(state=state, expire_at=expire_at))

        return state
