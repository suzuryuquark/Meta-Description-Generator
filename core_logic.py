from services.website_fetch_service import WebsiteFetchService


def fetch_website_content(url: str) -> str:
    """Compatibility wrapper for callers outside the Flet application."""

    return WebsiteFetchService().fetch_text(url)
