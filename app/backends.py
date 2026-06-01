import logging

from fastmcp import FastMCP
from fastmcp.server import create_proxy

from .settings import PostgresDB, Settings
from .transports import (
    MONGO_NPX_CACHE_DIR,
    NonInteractiveNpxStdioTransport,
    mongo_child_env,
)

logger = logging.getLogger(__name__)


def mount_postgres(gateway: FastMCP, db: PostgresDB, package: str) -> None:
    gateway.mount(
        create_proxy(
            NonInteractiveNpxStdioTransport(
                package=package,
                args=[db.url],
            )
        ),
        namespace=f"pg_{db.name}",
    )


def mount_mongo(gateway: FastMCP, settings: Settings, mongo_url: str) -> None:
    gateway.mount(
        create_proxy(
            NonInteractiveNpxStdioTransport(
                package=settings.mongo_mcp_package,
                args=["--readOnly"],
                env_vars=mongo_child_env(mongo_url),
            )
        ),
        namespace="mongo",
    )


def mount_all(gateway: FastMCP, settings: Settings) -> None:
    for db in settings.postgres_dbs:
        logger.info(
            "Mounting Postgres backend namespace=%s package=%s",
            f"pg_{db.name}",
            settings.postgres_mcp_package,
        )
        mount_postgres(gateway, db, settings.postgres_mcp_package)

    if settings.mongo_url:
        logger.info(
            "Mounting Mongo backend namespace=mongo package=%s cache=%s",
            settings.mongo_mcp_package,
            MONGO_NPX_CACHE_DIR,
        )
        mount_mongo(gateway, settings, settings.mongo_url)
    else:
        logger.warning("Skipping Mongo backend because MONGO_URL is not set")
