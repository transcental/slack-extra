from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean
from piccolo.columns.column_types import Integer
from piccolo.columns.column_types import JSON
from piccolo.columns.column_types import Secret
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod


ID = "2025-11-04T05:20:13:313051"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.add_table(
        class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="SlackOAuthState",
        tablename="slack_o_auth_state",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="team_id",
        db_column_name="team_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="team_name",
        db_column_name="team_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="enterprise_id",
        db_column_name="enterprise_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="enterprise_name",
        db_column_name="enterprise_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_token",
        db_column_name="bot_token",
        column_class_name="Secret",
        column_class=Secret,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": True,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_id",
        db_column_name="bot_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_user_id",
        db_column_name="bot_user_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_scopes",
        db_column_name="bot_scopes",
        column_class_name="JSON",
        column_class=JSON,
        params={
            "default": "{}",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="user_id",
        db_column_name="user_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="user_token",
        db_column_name="user_token",
        column_class_name="Secret",
        column_class=Secret,
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": True,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="user_scopes",
        db_column_name="user_scopes",
        column_class_name="JSON",
        column_class=JSON,
        params={
            "default": "{}",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="incoming_webhook_url",
        db_column_name="incoming_webhook_url",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="incoming_webhook_channel",
        db_column_name="incoming_webhook_channel",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="incoming_webhook_channel_id",
        db_column_name="incoming_webhook_channel_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="incoming_webhook_configuration_url",
        db_column_name="incoming_webhook_configuration_url",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="is_enterprise_install",
        db_column_name="is_enterprise_install",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="token_type",
        db_column_name="token_type",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "bot",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="installed_at",
        db_column_name="installed_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthState",
        tablename="slack_o_auth_state",
        column_name="state",
        db_column_name="state",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SlackOAuthState",
        tablename="slack_o_auth_state",
        column_name="expire_at",
        db_column_name="expire_at",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
