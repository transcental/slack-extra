from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar


ID = "2025-11-15T00:52:03:367514"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="AnchorConfig",
        tablename="anchor_config",
        column_name="message_ts",
        db_column_name="message_ts",
        params={"null": False},
        old_params={"null": True},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
