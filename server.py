from fastmcp import FastMCP

from app.auth import google_auth
from app.backends import mount_all
from app.config import load
from app.instructions import load_instructions
from app.settings import Settings


def build_gateway() -> tuple[FastMCP, Settings]:
    settings = load()
    gateway = FastMCP(
        "Vetic Gateway",
        instructions=load_instructions(),
        auth=google_auth(settings),
    )
    mount_all(gateway, settings)
    return gateway, settings


gateway, settings = build_gateway()
app = gateway.http_app()


def main() -> None:
    gateway.run(transport="http", port=settings.port)


if __name__ == "__main__":
    main()
