"""Web search adapters and tool wrapper."""

from __future__ import annotations

from urllib.parse import quote_plus
from typing import Any, cast

from debug_utils import sentinel

from tools.base.tool import Tool

# DuckDuckGo JSON endpoint is used in Phase 4 to avoid API key requirements.
DDG_API_URL = "https://api.duckduckgo.com/?q={}&format=json"


@sentinel
def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    print(f"--- SEARCHING WEB FOR: '{query}' ---")
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

        if not results:
            return [
                {
                    "Title": "Search Status",
                    "Snippet": f"Search for '{query}' executed, no specific summary found.",
                    "URL": "n/a",
                }
            ]

        return results
    except Exception as exc:
        print(f"[ERROR] Web search tool failed: {exc}")
        return [
            {
                "Title": "Search Error",
                "Snippet": f"Search failed for '{query}': {exc}",
                "URL": "n/a",
            }
        ]


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
