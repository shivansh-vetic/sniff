"""Mounts the registry MCP servers (Postgres × N, Mongo) onto the gateway.

Each backend MCP server runs as a stdio child process spawned by FastMCP via
`npx`. They are not reachable from outside — only the gateway is exposed.

Backends used:
    Postgres → `@modelcontextprotocol/server-postgres` (npm, Anthropic official)
    Mongo    → `mongodb-mcp-server`                     (npm, MongoDB official)

Mongo runs with `--readOnly` so the LLM can never INSERT/UPDATE/DELETE.

Requires Node + npx on the host:
    sudo apt -y install nodejs npm    # Ubuntu
    brew install node                  # macOS

Tools from each backend are auto-prefixed with the namespace, e.g.
`pg_vetic_query`, `pg_analytics_query`, `mongo_find`.
"""

import logging

from fastmcp import FastMCP
from fastmcp.client.transports import NpxStdioTransport
from fastmcp.server import create_proxy

from .config import PostgresDB, Settings

logger = logging.getLogger(__name__)


class NonInteractiveNpxStdioTransport(NpxStdioTransport):
    """Force `npx` to auto-install packages instead of prompting on first run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = ["--yes", *self.args]


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


def mount_mongo(gateway: FastMCP, mongo_url: str, package: str) -> None:
    # Prefer the environment variable over the deprecated --connectionString flag.
    gateway.mount(
        create_proxy(
            NonInteractiveNpxStdioTransport(
                package=package,
                args=["--readOnly"],
                env_vars={"MDB_MCP_CONNECTION_STRING": mongo_url},
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
            "Mounting Mongo backend namespace=mongo package=%s",
            settings.mongo_mcp_package,
        )
        mount_mongo(gateway, settings.mongo_url, settings.mongo_mcp_package)
    else:
        logger.warning("Skipping Mongo backend because MONGO_URL is not set")
