"""
MCP Connector — Confluence Cloud (REST API v2).

Operations: Spaces, Pages, Comments.
Auth: Atlassian API token (same style as Jira).

Env vars (shared .env):
  CONFLUENCE_URL        e.g. https://yourcompany.atlassian.net
  CONFLUENCE_EMAIL
  CONFLUENCE_API_TOKEN
"""

import argparse
import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")

mcp = FastMCP(
    name="confluence-connector",
    instructions="CRUD operations against Confluence spaces, pages and comments.",
)

CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "").rstrip("/")
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")


def _require_config():
    if not (CONFLUENCE_URL and CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN):
        raise RuntimeError("CONFLUENCE_URL, CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN must be set.")


async def _cf(method: str, path: str, json_body: dict | None = None, params: dict | None = None):
    _require_config()
    url = f"{CONFLUENCE_URL}/wiki/api/v2/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method, url,
            json=json_body,
            params=params,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


# --- Spaces --------------------------------------------------------------

@mcp.tool()
async def confluence_list_spaces() -> list:
    """List all Confluence spaces."""
    data = await _cf("GET", "spaces")
    return data.get("results", [])


@mcp.tool()
async def confluence_get_space(space_key: str) -> dict:
    """Get a Confluence space by key."""
    data = await _cf("GET", "spaces", params={"keys": space_key})
    results = data.get("results", [])
    return results[0] if results else {}


# --- Pages ---------------------------------------------------------------

@mcp.tool()
async def confluence_list_pages(space_id: str) -> list:
    """List pages in a Confluence space."""
    data = await _cf("GET", "pages", params={"spaceId": space_id, "limit": 50})
    return data.get("results", [])


@mcp.tool()
async def confluence_get_page(page_id: str) -> dict:
    """Get a Confluence page by ID (includes body content)."""
    return await _cf("GET", f"pages/{page_id}", params={"body-format": "storage"})


@mcp.tool()
async def confluence_create_page(
    space_id: str, title: str, content: str, parent_id: str | None = None
) -> dict:
    """
    Create a Confluence page. content is plain text — it is wrapped in
    Confluence Storage Format automatically.
    """
    payload: dict = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": f"<p>{content}</p>"},
    }
    if parent_id:
        payload["parentId"] = parent_id
    return await _cf("POST", "pages", payload)


@mcp.tool()
async def confluence_update_page(page_id: str, title: str, content: str, version: int) -> dict:
    """
    Update a Confluence page. version must be the CURRENT version number + 1
    (fetch it first with confluence_get_page). content is plain text.
    """
    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": f"<p>{content}</p>"},
        "version": {"number": version},
    }
    return await _cf("PUT", f"pages/{page_id}", payload)


@mcp.tool()
async def confluence_delete_page(page_id: str) -> dict:
    """Delete (trash) a Confluence page. Irreversible via API."""
    await _cf("DELETE", f"pages/{page_id}")
    return {"deleted_page_id": page_id}


@mcp.tool()
async def confluence_search_pages(query: str, space_key: str | None = None) -> list:
    """Search Confluence pages by title keyword, optionally scoped to a space."""
    cql = f'type=page AND title ~ "{query}"'
    if space_key:
        cql += f' AND space.key = "{space_key}"'
    data = await _cf("GET", "search", params={"cql": cql, "limit": 20})
    return data.get("results", [])


# --- Comments ------------------------------------------------------------

@mcp.tool()
async def confluence_list_comments(page_id: str) -> list:
    """List footer comments on a Confluence page."""
    data = await _cf("GET", "footer-comments", params={"pageId": page_id})
    return data.get("results", [])


@mcp.tool()
async def confluence_add_comment(page_id: str, body: str) -> dict:
    """Add a footer comment to a Confluence page."""
    payload = {
        "pageId": page_id,
        "body": {"representation": "storage", "value": f"<p>{body}</p>"},
    }
    return await _cf("POST", "footer-comments", payload)


@mcp.tool()
async def confluence_delete_comment(comment_id: str) -> dict:
    """Delete a footer comment from a Confluence page."""
    await _cf("DELETE", f"footer-comments/{comment_id}")
    return {"deleted_comment_id": comment_id}


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if CONFLUENCE_URL and CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN:
        print("Credentials found — listing spaces...")
        spaces = await confluence_list_spaces()
        print(f"  OK: {len(spaces)} space(s) found.")
    else:
        print("CONFLUENCE_URL / CONFLUENCE_EMAIL / CONFLUENCE_API_TOKEN not set — skipping live call.")
    print("\nTo serve:\n  python confluence.py --serve\n  python confluence.py --serve --transport http --port 8006")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8006)
    args = parser.parse_args()
    if not args.serve:
        asyncio.run(_smoke_test())
        return
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"Serving at http://{args.host}:{args.port}/mcp")
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
