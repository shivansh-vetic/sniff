from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class PostgresDB:
    name: str
    host: str
    port: str
    user: str
    password: str
    db: str

    @property
    def url(self) -> str:
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
    postgres_mcp_package: str
    mongo_mcp_package: str
