from piccolo.apps.migrations.auto.migration_manager import MigrationManager


ID = "2025-12-08T04:27:54:126213"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="slack_extra", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="MigrationConfig",
        tablename="migration_config",
        column_name="channels",
        db_column_name="channels",
        schema=None,
    )

    return manager
