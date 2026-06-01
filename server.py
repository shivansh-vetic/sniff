from fastmcp import FastMCP

from app.auth import google_auth
from app.backends import mount_all
from app.config import load
from app.instructions import load_instructions
from app.policy import CONTEXT_TOOL_NAME, EnforceContextLoaded
from app.settings import Settings


def build_gateway() -> tuple[FastMCP, Settings]:
    settings = load()
    instructions = load_instructions()
    gateway = FastMCP(
        "Vetic Gateway",
        instructions=instructions,
        auth=google_auth(settings),
    )
    mount_all(gateway, settings)

    # Hard-enforce that the context tool runs before any other tool call.
    gateway.add_middleware(EnforceContextLoaded())

    # The tool the LLM is required to call first in every session.
    @gateway.tool(
        name=CONTEXT_TOOL_NAME,
        description=(
            "REQUIRED FIRST CALL. Before using any pg_* or mongo_* tool you MUST "
            "call this to load Vetic's data-query rules (PII masking, time-window "
            "limits, query budgets, schema map). The server will reject every "
            "other tool call until this one has run in the current session."
        ),
    )
    def load_vetic_context() -> str:
        return instructions

    # Also expose the same content as a named prompt — works regardless of
    # whether a given client honors server-level `instructions`.
    @gateway.prompt(name="vetic_context")
    def vetic_context() -> str:
        """Vetic analyst context: schema map, time rules, PII rules, query budgets."""
        return instructions

    return gateway, settings


gateway, settings = build_gateway()
app = gateway.http_app()


def main() -> None:
    gateway.run(transport="http", port=settings.port)


if __name__ == "__main__":
    main()
