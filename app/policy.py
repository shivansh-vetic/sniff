"""Per-session policy enforcement.

`EnforceContextLoaded` is a FastMCP middleware that **blocks every tool call**
until the special `load_vetic_context` tool has been invoked in the current
MCP session. This guarantees that Claude has read Vetic's rules (PII handling,
time-window limits, query budgets, schema map) before it touches any data.

The check is per-session — each new Claude session must load context once.
Once loaded, all subsequent tool calls in that session pass through.
"""

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

CONTEXT_TOOL_NAME = "load_vetic_context"


class EnforceContextLoaded(Middleware):
    """Reject any tool call before the context-load tool has run."""

    def __init__(self) -> None:
        self._loaded_sessions: set[str] = set()

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name

        # Identify the calling session. Fall back to "anonymous" if FastMCP
        # didn't attach a context (shouldn't happen for HTTP transport).
        fctx = context.fastmcp_context
        session_id = fctx.session_id if fctx else "anonymous"

        # The context-load tool is always allowed and marks the session ready.
        if tool_name == CONTEXT_TOOL_NAME:
            self._loaded_sessions.add(session_id)
            return await call_next(context)

        # Everything else is blocked until the session has loaded context.
        if session_id not in self._loaded_sessions:
            raise ToolError(
                f"Call `{CONTEXT_TOOL_NAME}` first. That tool returns the required "
                "rules for querying Vetic data (PII handling, time-window limits, "
                "query budgets, schema map). Once it has run in this session, retry "
                "your tool call."
            )

        return await call_next(context)
