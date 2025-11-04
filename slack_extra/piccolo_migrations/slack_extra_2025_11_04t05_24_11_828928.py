from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import JSON
from piccolo.columns.column_types import Varchar


ID = "2025-11-04T05:24:11:828928"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_id",
        db_column_name="bot_id",
        params={"null": True},
        old_params={"null": False},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    manager.alter_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_user_id",
        db_column_name="bot_user_id",
        params={"null": True},
        old_params={"null": False},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    manager.alter_column(
        table_class_name="SlackOAuthInstallation",
        tablename="slack_o_auth_installation",
        column_name="bot_scopes",
        db_column_name="bot_scopes",
        params={"null": True},
        old_params={"null": False},
        column_class=JSON,
        old_column_class=JSON,
        schema=None,
    )

    return manager
