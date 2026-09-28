"""
MCP Connector — SharePoint (via Microsoft Graph API).

Operations: Sites, Lists, List Items, Files/Folders (Drive).
Auth: Azure AD app with client credentials (client_id + client_secret).

Env vars (shared .env):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
  SHAREPOINT_SITE_URL  e.g. https://yourcompany.sharepoint.com/sites/yoursite
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
    name="sharepoint-connector",
    instructions="CRUD operations against SharePoint sites, lists, items and files via Microsoft Graph.",
)

TENANT_ID = os.environ.get("AZURE_TENANT_ID")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "")
GRAPH = "https://graph.microsoft.com/v1.0"

_token_cache: dict = {}


async def _get_token() -> str:
    if _token_cache.get("token"):
        return _token_cache["token"]
    if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET must be set.")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        resp.raise_for_status()
        _token_cache["token"] = resp.json()["access_token"]
    return _token_cache["token"]


async def _graph(method: str, path: str, json_body: dict | None = None, params: dict | None = None):
    token = await _get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method,
            f"{GRAPH}/{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=json_body,
            params=params,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


async def _site_id() -> str:
    hostname = SITE_URL.split("/")[2]
    path = "/" + "/".join(SITE_URL.split("/")[3:])
    data = await _graph("GET", f"sites/{hostname}:{path}")
    return data["id"]


# --- Sites ---------------------------------------------------------------

@mcp.tool()
async def sharepoint_get_site() -> dict:
    """Get metadata for the configured SharePoint site."""
    sid = await _site_id()
    return await _graph("GET", f"sites/{sid}")


@mcp.tool()
async def sharepoint_list_subsites() -> list:
    """List subsites of the configured SharePoint site."""
    sid = await _site_id()
    data = await _graph("GET", f"sites/{sid}/sites")
    return data.get("value", [])


# --- Lists ---------------------------------------------------------------

@mcp.tool()
async def sharepoint_list_lists() -> list:
    """List all lists in the SharePoint site."""
    sid = await _site_id()
    data = await _graph("GET", f"sites/{sid}/lists")
    return [{"id": l["id"], "name": l["name"]} for l in data.get("value", [])]


@mcp.tool()
async def sharepoint_create_list(name: str, columns: list[dict] | None = None) -> dict:
    """Create a list. columns e.g. [{"name": "Status", "text": {}}]."""
    sid = await _site_id()
    payload: dict = {"displayName": name, "list": {}}
    if columns:
        payload["columns"] = columns
    return await _graph("POST", f"sites/{sid}/lists", payload)


@mcp.tool()
async def sharepoint_delete_list(list_id: str) -> dict:
    """Delete a SharePoint list. Irreversible."""
    sid = await _site_id()
    await _graph("DELETE", f"sites/{sid}/lists/{list_id}")
    return {"deleted_list_id": list_id}


# --- List Items ----------------------------------------------------------

@mcp.tool()
async def sharepoint_list_items(list_id: str) -> list:
    """Get all items in a SharePoint list (with field values)."""
    sid = await _site_id()
    data = await _graph("GET", f"sites/{sid}/lists/{list_id}/items", params={"expand": "fields"})
    return data.get("value", [])


@mcp.tool()
async def sharepoint_create_item(list_id: str, fields: dict) -> dict:
    """Create an item in a SharePoint list. fields maps column name -> value."""
    sid = await _site_id()
    return await _graph("POST", f"sites/{sid}/lists/{list_id}/items", {"fields": fields})


@mcp.tool()
async def sharepoint_update_item(list_id: str, item_id: str, fields: dict) -> dict:
    """Update fields on an existing list item."""
    sid = await _site_id()
    return await _graph("PATCH", f"sites/{sid}/lists/{list_id}/items/{item_id}/fields", fields)


@mcp.tool()
async def sharepoint_delete_item(list_id: str, item_id: str) -> dict:
    """Delete a list item. Irreversible."""
    sid = await _site_id()
    await _graph("DELETE", f"sites/{sid}/lists/{list_id}/items/{item_id}")
    return {"deleted_item_id": item_id}


# --- Files (Drive) -------------------------------------------------------

@mcp.tool()
async def sharepoint_list_files(folder_path: str = "root") -> list:
    """List files and folders at a drive path. folder_path e.g. 'root' or 'root:/Documents'."""
    sid = await _site_id()
    data = await _graph("GET", f"sites/{sid}/drive/{folder_path}:/children")
    return [{"name": i["name"], "id": i["id"], "size": i.get("size"), "type": "folder" if "folder" in i else "file"} for i in data.get("value", [])]


@mcp.tool()
async def sharepoint_read_file(file_path: str) -> str:
    """Read a text file's content from SharePoint drive. file_path e.g. 'root:/Documents/notes.txt'."""
    sid = await _site_id()
    token = await _get_token()
    meta = await _graph("GET", f"sites/{sid}/drive/{file_path}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            meta["@microsoft.graph.downloadUrl"],
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.text


@mcp.tool()
async def sharepoint_upload_file(folder_path: str, file_name: str, content: str) -> dict:
    """Upload (create or overwrite) a text file into a SharePoint drive folder."""
    sid = await _site_id()
    token = await _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{GRAPH}/sites/{sid}/drive/{folder_path}/{file_name}:/content",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
            content=content.encode("utf-8"),
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def sharepoint_delete_file(file_path: str) -> dict:
    """Delete a file or folder from SharePoint drive. Irreversible."""
    sid = await _site_id()
    await _graph("DELETE", f"sites/{sid}/drive/{file_path}")
    return {"deleted_path": file_path}


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if TENANT_ID and CLIENT_ID and CLIENT_SECRET:
        print("Azure credentials found — fetching site metadata...")
        data = await sharepoint_get_site()
        print(f"  OK: site '{data.get('name')}' ({data.get('webUrl')})")
    else:
        print("AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET not set — skipping live call.")
    print("\nTo serve:\n  python sharepoint.py --serve\n  python sharepoint.py --serve --transport http --port 8004")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8004)
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
