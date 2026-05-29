"""Mounts the registry MCP servers (Postgres × N, Mongo) onto the gateway.

Each backend MCP server runs as a stdio child process spawned by FastMCP.
They are not reachable from outside — only the gateway is exposed.

Tools from each backend are auto-prefixed with the namespace, e.g.
`pg_vetic_query`, `pg_analytics_query`, `mongo_find`.
"""

from fastmcp import FastMCP
from fastmcp.client.transports import NpxStdioTransport
from fastmcp.server import create_proxy

from .config import PostgresDB, Settings


def mount_postgres(gateway: FastMCP, db: PostgresDB) -> None:
    gateway.mount(
        create_proxy(
            NpxStdioTransport(
                package="@modelcontextprotocol/server-postgres",
                args=[db.url],
            )
        ),
        namespace=f"pg_{db.name}",
    )


def mount_mongo(gateway: FastMCP, mongo_url: str) -> None:
    gateway.mount(
        create_proxy(
            NpxStdioTransport(
                package="mongo-mcp",
                args=[mongo_url],
            )
        ),
        namespace="mongo",
    )


def mount_all(gateway: FastMCP, settings: Settings) -> None:
    for db in settings.postgres_dbs:
        mount_postgres(gateway, db)
    if settings.mongo_url:
        mount_mongo(gateway, settings.mongo_url)
