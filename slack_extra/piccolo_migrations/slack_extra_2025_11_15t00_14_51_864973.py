from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import JSON
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod


ID = "2025-11-15T00:14:51:864973"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="AnchorConfig",
        tablename="anchor_config",
        column_name="message_ts",
        db_column_name="message_ts",
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

    manager.alter_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_scopes",
        db_column_name="bot_scopes",
        params={"default": "[]"},
        old_params={"default": "{}"},
        column_class=JSON,
        old_column_class=JSON,
        schema=None,
    )

    manager.alter_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="user_scopes",
        db_column_name="user_scopes",
        params={"default": "[]"},
        old_params={"default": "{}"},
        column_class=JSON,
        old_column_class=JSON,
        schema=None,
    )

    return manager
