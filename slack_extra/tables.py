from piccolo.columns import Boolean
from piccolo.columns import Integer
from piccolo.columns import JSON
from piccolo.columns import Secret
from piccolo.columns import Text
from piccolo.columns import Timestamptz
from piccolo.columns import Varchar
from piccolo.table import Table


class SlackOAuthInstallation(Table):
    team_id = Varchar(length=20, index=True)
    team_name = Varchar(length=255, null=True)
    enterprise_id = Varchar(length=20, null=True, index=True)
    enterprise_name = Varchar(length=255, null=True)

    bot_token = Secret()
    bot_id = Varchar(length=20, null=True)
    bot_user_id = Varchar(length=20, null=True)
    bot_scopes = JSON(null=True)

    user_id = Varchar(length=20, index=True)
    user_token = Secret(null=True)
    user_scopes = JSON(null=True)

    incoming_webhook_url = Text(null=True)
    incoming_webhook_channel = Varchar(length=255, null=True)
    incoming_webhook_channel_id = Varchar(length=20, null=True)
    incoming_webhook_configuration_url = Text(null=True)

    is_enterprise_install = Boolean(default=False)
    token_type = Varchar(length=20, default="bot")

    installed_at = Timestamptz()


class SlackOAuthState(Table):
    state = Varchar(length=255, unique=True, index=True)
    expire_at = Integer()
