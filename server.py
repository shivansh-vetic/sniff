"""Vetic MCP gateway — entry point.

Wires the parts together and runs the HTTP server:

    config  → loads env vars
    auth    → Google OAuth provider
    backends → mount Postgres + Mongo MCP servers

Run:
    python server.py
"""

from fastmcp import FastMCP

from app import config
from app.auth import google_auth
from app.backends import mount_all


def build_gateway() -> tuple[FastMCP, config.Settings]:
    settings = config.load()
    gateway = FastMCP("Vetic Gateway", auth=google_auth(settings))
    mount_all(gateway, settings)
    return gateway, settings


def main() -> None:
    gateway, settings = build_gateway()
    gateway.run(transport="http", port=settings.port)


if __name__ == "__main__":
    main()
