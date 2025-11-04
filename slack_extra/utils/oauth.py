import logging
from urllib.parse import urlencode

from slack_extra.config import config
from slack_extra.datastore import PiccoloOAuthStateStore

logger = logging.getLogger(__name__)


async def generate_oauth_url(
    scopes: list[str] | None = None,
    user_scopes: list[str] | None = None,
) -> str:
    state_store = PiccoloOAuthStateStore()
    state = await state_store.async_issue(expiration_seconds=600)

    params = {
        "client_id": config.slack.client_id,
        "redirect_uri": config.slack.redirect_uri,
        "state": state,
    }

    if scopes:
        params["scope"] = " ".join(scopes)

    if user_scopes:
        params["user_scope"] = " ".join(user_scopes)

    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
