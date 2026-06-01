from fastmcp.server.auth.providers.google import GoogleProvider

from .settings import Settings


def google_auth(settings: Settings) -> GoogleProvider:
    return GoogleProvider(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        base_url=settings.base_url,
    )
