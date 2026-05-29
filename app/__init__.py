"""Vetic MCP gateway — internals.

Layout:
    config.py    — loads + validates environment variables
    auth.py      — Google OAuth provider for FastMCP
    backends.py  — mounts the registry MCP servers (Postgres, Mongo, …)
"""
