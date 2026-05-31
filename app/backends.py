"""Mounts the registry MCP servers (Postgres × N, Mongo) onto the gateway.

Each backend MCP server runs as a stdio child process spawned by FastMCP via
`npx`. They are not reachable from outside — only the gateway is exposed.

Backends used:
    Postgres → `@modelcontextprotocol/server-postgres` (npm, Anthropic official)
    Mongo    → `mongodb-mcp-server`                     (npm, MongoDB official)

Mongo runs with `--readOnly` so the LLM can never INSERT/UPDATE/DELETE.
"""

import logging

from fastmcp import FastMCP
from fastmcp.client.transports import NpxStdioTransport
from fastmcp.server import create_proxy

from .config import PostgresDB, Settings

logger = logging.getLogger(__name__)
_MONGO_NPX_CACHE_DIR = "/tmp/mongodb-mcp-server-npx-cache-v2"


class NonInteractiveNpxStdioTransport(NpxStdioTransport):
    """Force `npx` to auto-install packages instead of prompting on first run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = ["--yes", *self.args]


def mongo_child_env(mongo_url: str) -> dict[str, str]:
    return {
        "MDB_MCP_CONNECTION_STRING": mongo_url,
        "NPM_CONFIG_CACHE": _MONGO_NPX_CACHE_DIR,
        "npm_config_cache": _MONGO_NPX_CACHE_DIR,
        # Avoid host crashes from optional native modules like kerberos.
        "NPM_CONFIG_OMIT": "optional",
        "npm_config_omit": "optional",
        "NPM_CONFIG_OPTIONAL": "false",
        "npm_config_optional": "false",
    }


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
            _MONGO_NPX_CACHE_DIR,
        )
        mount_mongo(gateway, settings, settings.mongo_url)
    else:
        logger.warning("Skipping Mongo backend because MONGO_URL is not set")
