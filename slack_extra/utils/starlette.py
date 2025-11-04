import logging

from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from slack_sdk.errors import SlackApiError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.responses import JSONResponse
from starlette.routing import Route

from slack_extra.config import config
from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.datastore import PiccoloOAuthStateStore
from slack_extra.env import env

logger = logging.getLogger(__name__)

req_handler = AsyncSlackRequestHandler(env.app)


async def endpoint(req: Request):
    return await req_handler.handle(req)


async def health(req: Request):
    try:
        await env.slack_client.api_test()
        slack_healthy = True
    except Exception:
        slack_healthy = False

    return JSONResponse(
        {
            "healthy": slack_healthy,
            "slack": slack_healthy,
        }
    )


async def oauth_redirect(req: Request):
    code = req.query_params.get("code")
    state = req.query_params.get("state")
    error = req.query_params.get("error")

    if error:
        logger.error(f"OAuth error: {error}")
        return HTMLResponse(
            content=f"<html><body><h1>OAuth Error</h1><p>{error}</p></body></html>",
            status_code=400,
        )

    if not code or not state:
        return HTMLResponse(
            content="<html><body><h1>OAuth Error</h1><p>Missing code or state parameter</p></body></html>",
            status_code=400,
        )

    state_store = PiccoloOAuthStateStore()
    is_valid_state = await state_store.async_consume(state)

    if not is_valid_state:
        return HTMLResponse(
            content="<html><body><h1>OAuth Error</h1><p>Invalid or expired state parameter</p></body></html>",
            status_code=400,
        )

    try:
        response = await env.slack_client.oauth_v2_access(
            client_id=config.slack.client_id,
            client_secret=config.slack.client_secret,
            code=code,
            redirect_uri=config.slack.redirect_uri,
        )

        if not response.get("ok"):
            error_msg = response.get("error", "Unknown error")
            logger.error(f"OAuth token exchange failed: {error_msg}")
            return HTMLResponse(
                content=f"<html><body><h1>OAuth Error</h1><p>Failed to exchange code for token: {error_msg}</p></body></html>",
                status_code=400,
            )

        from slack_sdk.oauth.installation_store import Installation
        from datetime import UTC, datetime

        authed_user = response.get("authed_user", {})
        team = response.get("team", {})
        enterprise = response.get("enterprise")

        bot_token = response.get("access_token") or config.slack.bot_token
        bot_user_id = response.get("bot_user_id")
        bot_scopes = (
            response.get("scope", "").split(",") if response.get("scope") else []
        )

        installation = Installation(
            app_id=response.get("app_id"),
            enterprise_id=enterprise.get("id") if enterprise else None,
            enterprise_name=enterprise.get("name") if enterprise else None,
            team_id=team.get("id"),
            team_name=team.get("name"),
            bot_token=bot_token,
            bot_id=bot_user_id,
            bot_user_id=bot_user_id,
            bot_scopes=bot_scopes,
            user_id=authed_user.get("id"),
            user_token=authed_user.get("access_token"),
            user_scopes=authed_user.get("scope", "").split(",")
            if authed_user.get("scope")
            else [],
            installed_at=datetime.now(UTC).timestamp(),
        )

        installation_store = PiccoloInstallationStore()
        await installation_store.async_save(installation)

        return HTMLResponse(
            content="""
            <html>
            <body>
                <h1>✅ Authorization Successful!</h1>
                <p>You have successfully authorized the app. You can now close this window and return to Slack.</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
            </body>
            </html>
            """,
            status_code=200,
        )

    except SlackApiError as e:
        logger.error(f"Slack API error during OAuth: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>OAuth Error</h1><p>Slack API error: {e.response.get('error', str(e))}</p></body></html>",
            status_code=500,
        )
    except Exception as e:
        logger.exception("Unexpected error during OAuth callback")
        return HTMLResponse(
            content=f"<html><body><h1>OAuth Error</h1><p>Unexpected error: {str(e)}</p></body></html>",
            status_code=500,
        )


app = Starlette(
    debug=True if config.environment != "production" else False,
    routes=[
        Route(path="/slack/events", endpoint=endpoint, methods=["POST"]),
        Route(path="/slack/oauth_redirect", endpoint=oauth_redirect, methods=["GET"]),
        Route(path="/health", endpoint=health, methods=["GET"]),
    ],
    lifespan=env.enter,
)
