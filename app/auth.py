"""Google OAuth provider for FastMCP.

The provider implements the full MCP authorization spec (discovery,
Dynamic Client Registration, PKCE) so a Claude client connects with just
a URL and gets the Google sign-in popup automatically.

Restrict sign-in to a specific Workspace domain (e.g. @vetic.in) by
setting the Google OAuth consent screen to "Internal" — enforced by
Google, no code change needed here.
"""

from fastmcp.server.auth.providers.google import GoogleProvider

from .config import Settings


def google_auth(settings: Settings) -> GoogleProvider:
    return GoogleProvider(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        base_url=settings.base_url,
    )
