"""Web search adapters and tool wrapper.

Priority:
1. Tavily (``TAVILY_API_KEY`` env var) — structured search results with snippets.
2. DuckDuckGo Instant Answer JSON — no API key required, fallback.
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus
from typing import Any, cast

from debug_utils import sentinel

from tools.base.tool import Tool

# DuckDuckGo JSON endpoint — used as no-key fallback.
DDG_API_URL = "https://api.duckduckgo.com/?q={}&format=json"


def _tavily_search(query: str, max_results: int) -> list[dict[str, str]] | None:
    """Try a Tavily search.  Returns None when the library or key is missing."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from tavily import TavilyClient  # type: ignore[import-untyped]

        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results)
        results: list[dict[str, str]] = []
        for item in response.get("results", []):
            results.append(
                {
                    "Title": str(item.get("title", "")),
                    "Snippet": str(item.get("content", "")),
                    "URL": str(item.get("url", "")),
                }
            )
        return results or None
    except Exception:
        return None


def _ddg_search(query: str, max_results: int) -> list[dict[str, str]]:
    """DuckDuckGo Instant Answer JSON fallback."""
    try:
        import requests  # type: ignore[import-untyped]

        encoded_query = quote_plus(query)
        response = requests.get(DDG_API_URL.format(encoded_query), timeout=15)
        response.raise_for_status()
        data = cast(dict[str, Any], response.json())

        results: list[dict[str, str]] = []
        if data.get("Abstract"):
            results.append(
                {
                    "Title": "Abstract",
                    "Snippet": data["Abstract"],
                    "URL": data.get("AbstractURL", ""),
                }
            )

        for topic in data.get("RelatedTopics", [])[:max_results]:
            if "Text" in topic:
                results.append(
                    {
                        "Title": topic.get("FirstURL", "Topic"),
                        "Snippet": topic["Text"],
                        "URL": topic.get("FirstURL", ""),
                    }
                )

        return results or [
            {
                "Title": "Search Status",
                "Snippet": f"Search for '{query}' executed, no specific summary found.",
                "URL": "n/a",
            }
        ]
    except Exception as exc:
        return [
            {
                "Title": "Search Error",
                "Snippet": f"DDG search failed for '{query}': {exc}",
                "URL": "n/a",
            }
        ]


@sentinel
def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web.  Uses Tavily when TAVILY_API_KEY is set; DDG otherwise."""
    print(f"--- SEARCHING WEB FOR: '{query}' ---")
    tavily_results = _tavily_search(query, max_results)
    if tavily_results is not None:
        return tavily_results
    return _ddg_search(query, max_results)


class WebSearchTool(Tool):
    name = "web.search"

    def run(self, **kwargs: Any) -> list[dict[str, str]]:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        max_results = int(kwargs.get("max_results", 5))
        return search_web(query=query, max_results=max_results)


def run_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    tool = WebSearchTool()
    return tool.run(query=query, max_results=max_results)


__all__ = ["WebSearchTool", "run_search", "search_web"]
