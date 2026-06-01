import os
import re

from dotenv import load_dotenv

from .settings import PostgresDB, Settings

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


_POSTGRES_HOST_PATTERN = re.compile(r"^POSTGRES_(?P<name>.+)_HOST$")


def _postgres_names() -> list[str]:
    return sorted(
        match.group("name")
        for key in os.environ
        if (match := _POSTGRES_HOST_PATTERN.match(key))
    )


def _named_postgres_db(name: str) -> PostgresDB:
    return PostgresDB(
        name=name.lower(),
        host=_require(f"POSTGRES_{name}_HOST"),
        port=os.environ.get(f"POSTGRES_{name}_PORT", "5432"),
        user=_require(f"POSTGRES_{name}_USER"),
        password=_require(f"POSTGRES_{name}_PASSWORD"),
        db=_require(f"POSTGRES_{name}_DB"),
    )


def _default_postgres_db() -> PostgresDB:
    return PostgresDB(
        name=_require("POSTGRES_DB").lower(),
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=_require("POSTGRES_USER"),
        password=_require("POSTGRES_PASSWORD"),
        db=_require("POSTGRES_DB"),
    )


def _discover_postgres_dbs() -> list[PostgresDB]:
    dbs = [_named_postgres_db(name) for name in _postgres_names()]
    if "POSTGRES_HOST" in os.environ:
        dbs.append(_default_postgres_db())
    return dbs


def load() -> Settings:
    return Settings(
        base_url=os.environ.get("BASE_URL", "http://localhost:8080"),
        port=int(os.environ.get("PORT", "8080")),
        google_client_id=_require("GOOGLE_CLIENT_ID"),
        google_client_secret=_require("GOOGLE_CLIENT_SECRET"),
        postgres_dbs=_discover_postgres_dbs(),
        mongo_url=os.environ.get("MONGO_URL"),
        postgres_mcp_package=os.environ.get(
            "POSTGRES_MCP_PACKAGE",
            "@modelcontextprotocol/server-postgres",
        ),
        mongo_mcp_package=os.environ.get(
            "MONGO_MCP_PACKAGE",
            "mongodb-mcp-server@1.11.0",
        ),
    )
