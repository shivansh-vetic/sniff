"""Per-user policy enforcement.

`EnforceContextLoaded` blocks every tool call until the special
`load_vetic_context` tool has been invoked by the calling user. Once a user
loads context, all subsequent tool calls from that user pass through for the
lifetime of their bearer token.

We key the cache on a hash of the user's bearer token (not the MCP
`session_id`, which is unstable across requests under stateless HTTP / cloud
load-balanced clients like claude.ai).
"""

import hashlib

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

CONTEXT_TOOL_NAME = "load_vetic_context"


def _principal(context: MiddlewareContext) -> str:
    """Stable identifier for the caller.

    Prefer a hash of the bearer token (one per Google-authenticated user,
    stable for the token's lifetime). Fall back to MCP `session_id`, then
    "anonymous".
    """
    # Read the underlying HTTP request via the documented helper.
    try:
        req = get_http_request()
        auth = req.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
            return "tok:" + hashlib.sha256(token.encode()).hexdigest()[:16]
    except Exception:
        pass  # No HTTP request in scope (e.g. in-memory client).

    fctx = context.fastmcp_context
    if fctx is not None:
        sid = getattr(fctx, "session_id", None)
        if sid:
            return f"sess:{sid}"
    return "anonymous"


class EnforceContextLoaded(Middleware):
    """Reject any tool call until `load_vetic_context` has run for this user."""

    def __init__(self) -> None:
        self._loaded: set[str] = set()

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        principal = _principal(context)
        tool_name = context.message.name

        if tool_name == CONTEXT_TOOL_NAME:
            self._loaded.add(principal)
            return await call_next(context)

        if principal not in self._loaded:
            raise ToolError(
                f"Call `{CONTEXT_TOOL_NAME}` first. That tool returns the required "
                "rules for querying Vetic data (PII handling, time-window limits, "
                "query budgets, schema map). Once it has run in this session, retry "
                "your tool call."
            )

        return await call_next(context)
