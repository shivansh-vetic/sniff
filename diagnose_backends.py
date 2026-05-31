"""Backend diagnostic for Postgres and Mongo MCP child servers.

Run this on the target host to verify that the gateway can spawn each child
server and list its tools:

    .venv/bin/python diagnose_backends.py
"""

from __future__ import annotations

import asyncio
import shutil

from fastmcp.client import Client

from app.backends import NonInteractiveNpxStdioTransport, mongo_child_env
from app.config import PostgresDB, Settings, load

TIMEOUT_SECONDS = 60


def _redact(text: str, settings: Settings) -> str:
    secrets = [db.url for db in settings.postgres_dbs]
    if settings.mongo_url:
        secrets.append(settings.mongo_url)
    for value in secrets:
        text = text.replace(value, "<redacted>")
    return text


async def _list_tools(
    package: str,
    args: list[str],
    env_vars: dict[str, str] | None = None,
) -> list[str]:
    transport = NonInteractiveNpxStdioTransport(
        package=package,
        args=args,
        env_vars=env_vars,
    )
    client = Client(transport)
    async with client:
        tools = await client.list_tools()
    return [tool.name for tool in tools]


async def _check_postgres(db: PostgresDB, settings: Settings) -> bool:
    namespace = f"pg_{db.name}"
    print(f"[{namespace}]")
    try:
        names = await asyncio.wait_for(
            _list_tools(settings.postgres_mcp_package, [db.url]),
            timeout=TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"status=error detail={_redact(f'{type(exc).__name__}: {exc}', settings)}")
        return False
    preview = ", ".join(names[:5]) or "-"
    print(f"status=ok tool_count={len(names)} sample={preview}")
    return True


async def _check_mongo(settings: Settings) -> bool:
    print("[mongo]")
    if not settings.mongo_url:
        print("status=skipped detail=MONGO_URL is not set")
        return False
    try:
        names = await asyncio.wait_for(
            _list_tools(
                settings.mongo_mcp_package,
                ["--readOnly"],
                mongo_child_env(settings.mongo_url),
            ),
            timeout=TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"status=error detail={_redact(f'{type(exc).__name__}: {exc}', settings)}")
        return False
    preview = ", ".join(names[:5]) or "-"
    print(f"status=ok tool_count={len(names)} sample={preview}")
    return True


async def main() -> int:
    settings = load()
    postgres_names = ", ".join(db.name for db in settings.postgres_dbs) or "none"
    print("Config")
    print(f"node={shutil.which('node') or 'missing'}")
    print(f"npx={shutil.which('npx') or 'missing'}")
    print(f"postgres_dbs={postgres_names}")
    print(f"mongo_configured={'yes' if settings.mongo_url else 'no'}")
    print(f"postgres_package={settings.postgres_mcp_package}")
    print(f"mongo_package={settings.mongo_mcp_package}")
    print()

    ok = True
    for db in settings.postgres_dbs:
        ok &= await _check_postgres(db, settings)
    ok &= await _check_mongo(settings)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
