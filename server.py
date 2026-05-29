"""Vetic MCP gateway — entry point.

Wires the parts together and runs the HTTP server:

    config  → loads env vars
    auth    → Google OAuth provider
    backends → mount Postgres + Mongo MCP servers

Run (either works):
    python server.py
    uvicorn server:app
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


# Build once at import so uvicorn (and any other ASGI server) can serve it:
#     uvicorn server:app --host 0.0.0.0 --port 8080
gateway, settings = build_gateway()
app = gateway.http_app()


def main() -> None:
    gateway.run(transport="http", port=settings.port)


if __name__ == "__main__":
    main()
