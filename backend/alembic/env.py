import os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
from dotenv import load_dotenv

# load env
load_dotenv(".env.dev")

config = context.config
fileConfig(config.config_file_name)

# import models
from app.db.base import Base
from app.db.models import *

target_metadata = Base.metadata


def get_url():
    return os.getenv("DATABASE_URL")


def run_migrations_online():
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    context.configure(url=get_url(), target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()