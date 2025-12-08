from piccolo.columns import Boolean
from piccolo.columns import ForeignKey
from piccolo.columns import Integer
from piccolo.columns import JSON
from piccolo.columns import Secret
from piccolo.columns import Serial
from piccolo.columns import Text
from piccolo.columns import Timestamptz
from piccolo.columns import Varchar
from piccolo.table import Table


class SlackOAuthInstallation(Table):
    id = Serial(primary_key=True)
    team_id = Varchar(length=20, index=True)
    team_name = Varchar(length=255, null=True)
    enterprise_id = Varchar(length=20, null=True, index=True)
    enterprise_name = Varchar(length=255, null=True)

    bot_token = Secret()
    bot_id = Varchar(length=20, null=True)
    bot_user_id = Varchar(length=20, null=True)
    bot_scopes = JSON(null=True, default=[])

    user_id = Varchar(length=20, index=True)
    user_token = Secret(null=True)
    user_scopes = JSON(null=True, default=[])

    incoming_webhook_url = Text(null=True)
    incoming_webhook_channel = Varchar(length=255, null=True)
    incoming_webhook_channel_id = Varchar(length=20, null=True)
    incoming_webhook_configuration_url = Text(null=True)

    is_enterprise_install = Boolean(default=False)
    token_type = Varchar(length=20, default="bot")

    installed_at = Timestamptz()


class SlackOAuthState(Table):
    id = Serial(primary_key=True)
    state = Varchar(length=255, unique=True, index=True)
    expire_at = Integer()


class AnchorConfig(Table):
    id = Serial(primary_key=True)
    channel_id = Varchar(length=20, index=True)
    enabled = Boolean(default=True)
    message = JSON(null=True)
    message_ts = Varchar(length=20)
    user_id = Varchar(length=20)
    created_at = Timestamptz()
    updated_at = Timestamptz()


class Spoiler(Table):
    id = Serial(primary_key=True)
    channel = Varchar(length=20)
    message_ts = Varchar(length=20)
    message = JSON()
    user = Varchar(length=20)
    created_at = Timestamptz()


class MigrationConfig(Table):
    id = Serial(primary_key=True)
    name = Varchar(length=255)
    user_id = Varchar(length=20)
    created_at = Timestamptz()


class MigrationChannel(Table):
    id = Serial(primary_key=True)
    channel_id = Varchar(unique=True)
    config = ForeignKey(references=MigrationConfig)
