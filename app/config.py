"""Environment configuration.

All env vars are loaded from `.env` (via python-dotenv) and the process
environment. `load()` returns a frozen Settings object the rest of the
package depends on.

Multiple Postgres databases are supported. Add them in `.env` with a
per-database name prefix:

    POSTGRES_<NAME>_HOST=...
    POSTGRES_<NAME>_PORT=...        (optional, defaults to 5432)
    POSTGRES_<NAME>_USER=...
    POSTGRES_<NAME>_PASSWORD=...
    POSTGRES_<NAME>_DB=...

Each database appears in Claude as `pg_<name>_query`, etc.
"""

import os
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


@dataclass(frozen=True)
class PostgresDB:
    name: str          # lowercased, used as the MCP namespace (pg_<name>_*)
    host: str
    port: str
    user: str
    password: str
    db: str

    @property
    def url(self) -> str:
        """postgresql:// URL with password URL-encoded."""
        return (
            f"postgresql://{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.db}"
        )


@dataclass(frozen=True)
class Settings:
    base_url: str
    port: int

    google_client_id: str
    google_client_secret: str

    postgres_dbs: list[PostgresDB]
    mongo_url: str | None


_POSTGRES_HOST_PATTERN = re.compile(r"^POSTGRES_(?P<name>.+)_HOST$")


def _discover_postgres_dbs() -> list[PostgresDB]:
    """Walk env vars and assemble PostgresDB list.

    Supports both patterns:
      1. Named (preferred for multiple DBs):
           POSTGRES_<NAME>_HOST, POSTGRES_<NAME>_PORT, ...
      2. Unnamed single DB (for back-compat):
           POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
         → namespace is derived from POSTGRES_DB.
    """
    dbs: list[PostgresDB] = []

    # Pattern 1: named DBs
    names = sorted(
        m.group("name")
        for key in os.environ
        if (m := _POSTGRES_HOST_PATTERN.match(key))
    )
    for name in names:
        dbs.append(
            PostgresDB(
                name=name.lower(),
                host=_require(f"POSTGRES_{name}_HOST"),
                port=os.environ.get(f"POSTGRES_{name}_PORT", "5432"),
                user=_require(f"POSTGRES_{name}_USER"),
                password=_require(f"POSTGRES_{name}_PASSWORD"),
                db=_require(f"POSTGRES_{name}_DB"),
            )
        )

    # Pattern 2: single unnamed DB
    if "POSTGRES_HOST" in os.environ:
        dbs.append(
            PostgresDB(
                name=_require("POSTGRES_DB").lower(),
                host=os.environ["POSTGRES_HOST"],
                port=os.environ.get("POSTGRES_PORT", "5432"),
                user=_require("POSTGRES_USER"),
                password=_require("POSTGRES_PASSWORD"),
                db=_require("POSTGRES_DB"),
            )
        )

    return dbs


def load() -> Settings:
    return Settings(
        base_url=os.environ.get("BASE_URL", "http://localhost:8080"),
        port=int(os.environ.get("PORT", "8080")),
        google_client_id=_require("GOOGLE_CLIENT_ID"),
        google_client_secret=_require("GOOGLE_CLIENT_SECRET"),
        postgres_dbs=_discover_postgres_dbs(),
        mongo_url=os.environ.get("MONGO_URL"),
    )
