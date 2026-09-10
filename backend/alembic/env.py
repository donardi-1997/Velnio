from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, inspect, pool, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.db.base import Base
from app.models import *  # noqa: F401,F403 - Alembic needs all model metadata loaded

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

VERSION_TABLE_NAME = "alembic_version"
VERSION_COLUMN_LENGTH = 128


def _ensure_version_table_capacity(connection) -> None:
    """Keep Alembic revision storage large enough for Velnio revision IDs.

    Alembic's default version table uses VARCHAR(32), while Velnio has a
    historical revision identifier longer than 32 characters. Renaming that
    revision would invalidate databases that already know it, so we preserve
    the identifier and widen the version column instead.
    """
    inspector = inspect(connection)
    table_names = inspector.get_table_names()

    if VERSION_TABLE_NAME not in table_names:
        connection.execute(
            text(
                f"CREATE TABLE {VERSION_TABLE_NAME} ("
                f"version_num VARCHAR({VERSION_COLUMN_LENGTH}) NOT NULL PRIMARY KEY"
                ")"
            )
        )
        connection.commit()
        return

    version_column = next(
        (
            column
            for column in inspector.get_columns(VERSION_TABLE_NAME)
            if column["name"] == "version_num"
        ),
        None,
    )
    if version_column is None:
        raise RuntimeError("Alembic version table is missing version_num")

    current_length = getattr(version_column["type"], "length", None)
    if current_length is not None and current_length < VERSION_COLUMN_LENGTH:
        if connection.dialect.name != "postgresql":
            raise RuntimeError(
                "Alembic version_num is too short and automatic widening is "
                f"not implemented for {connection.dialect.name}"
            )
        connection.execute(
            text(
                f"ALTER TABLE {VERSION_TABLE_NAME} "
                f"ALTER COLUMN version_num TYPE VARCHAR({VERSION_COLUMN_LENGTH})"
            )
        )
        connection.commit()


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE_NAME,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_version_table_capacity(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE_NAME,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
