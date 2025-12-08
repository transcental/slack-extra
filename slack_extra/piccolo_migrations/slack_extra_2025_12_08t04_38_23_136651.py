from piccolo.apps.migrations.auto.migration_manager import MigrationManager


ID = "2025-12-08T04:38:23:136651"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.rename_column(
        table_class_name="MigrationChannel",
        tablename="migration_channel",
        old_column_name="config_id",
        new_column_name="config",
        old_db_column_name="config_id",
        new_db_column_name="config",
        schema=None,
    )

    return manager
