import re

SEARCH_RE = re.compile(
    r"\b(today|today's|tonight|latest|most recent|this (week|month|year)|"
    r"currently|current|right now|news|headlines|price of|exchange rate|weather|forecast)\b",
    re.I)


def needs_search(prompt: str) -> bool:
    return bool(SEARCH_RE.search(prompt))


def route(prompt: str, search_tier: str = "cheap") -> dict:
    """Return the tier to use and whether to run web search."""
    search = needs_search(prompt)
    return {"tier": search_tier if search else "free", "search": search}
