"""
MCP Connector — OneDrive (via Microsoft Graph API).

Operations: Files, Folders (personal or shared drive).
Auth: Azure AD app — same credentials as sharepoint.py.

Env vars (shared .env):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
  OUTLOOK_USER_ID  (the user's UPN or object ID whose OneDrive to access)
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
    name="onedrive-connector",
    instructions="CRUD operations on OneDrive files and folders via Microsoft Graph.",
)

TENANT_ID = os.environ.get("AZURE_TENANT_ID")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
USER_ID = os.environ.get("OUTLOOK_USER_ID")
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


def _drive_root() -> str:
    if not USER_ID:
        raise RuntimeError("OUTLOOK_USER_ID must be set (user's UPN or object ID).")
    return f"users/{USER_ID}/drive"


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


# --- Browse --------------------------------------------------------------

@mcp.tool()
async def onedrive_list_items(folder_path: str = "root") -> list:
    """List files and folders at a OneDrive path. folder_path: 'root' or 'root:/Documents'."""
    dr = _drive_root()
    data = await _graph("GET", f"{dr}/{folder_path}:/children")
    return [
        {"name": i["name"], "id": i["id"], "size": i.get("size"),
         "type": "folder" if "folder" in i else "file"}
        for i in data.get("value", [])
    ]


@mcp.tool()
async def onedrive_get_item(item_path: str) -> dict:
    """Get metadata for a file or folder by path, e.g. 'root:/Reports/Q3.xlsx'."""
    dr = _drive_root()
    return await _graph("GET", f"{dr}/{item_path}")


# --- Read ----------------------------------------------------------------

@mcp.tool()
async def onedrive_read_file(file_path: str) -> str:
    """Read a text file's content from OneDrive. file_path e.g. 'root:/Notes/todo.txt'."""
    dr = _drive_root()
    token = await _get_token()
    meta = await _graph("GET", f"{dr}/{file_path}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            meta["@microsoft.graph.downloadUrl"],
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.text


# --- Write / Create / Update ---------------------------------------------

@mcp.tool()
async def onedrive_create_folder(parent_path: str, folder_name: str) -> dict:
    """Create a folder in OneDrive. parent_path e.g. 'root:/Documents'."""
    dr = _drive_root()
    return await _graph(
        "POST", f"{dr}/{parent_path}:/children",
        {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"},
    )


@mcp.tool()
async def onedrive_upload_file(folder_path: str, file_name: str, content: str) -> dict:
    """Upload (create or overwrite) a text file into a OneDrive folder."""
    dr = _drive_root()
    token = await _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{GRAPH}/{dr}/{folder_path}/{file_name}:/content",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
            content=content.encode("utf-8"),
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def onedrive_move_item(item_id: str, new_parent_id: str, new_name: str | None = None) -> dict:
    """Move (or rename) a OneDrive item. item_id and new_parent_id come from list/get calls."""
    dr = _drive_root()
    payload: dict = {"parentReference": {"id": new_parent_id}}
    if new_name:
        payload["name"] = new_name
    return await _graph("PATCH", f"{dr}/items/{item_id}", payload)


@mcp.tool()
async def onedrive_copy_item(item_id: str, destination_parent_id: str, new_name: str | None = None) -> dict:
    """Copy a OneDrive item to another folder."""
    dr = _drive_root()
    payload: dict = {"parentReference": {"id": destination_parent_id}}
    if new_name:
        payload["name"] = new_name
    return await _graph("POST", f"{dr}/items/{item_id}/copy", payload)


# --- Delete --------------------------------------------------------------

@mcp.tool()
async def onedrive_delete_item(item_id: str) -> dict:
    """Delete a file or folder by item ID. Irreversible."""
    dr = _drive_root()
    await _graph("DELETE", f"{dr}/items/{item_id}")
    return {"deleted_item_id": item_id}


# --- Search --------------------------------------------------------------

@mcp.tool()
async def onedrive_search(query: str) -> list:
    """Search for files in OneDrive by name or content keyword."""
    dr = _drive_root()
    data = await _graph("GET", f"{dr}/root/search(q='{query}')")
    return data.get("value", [])


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if TENANT_ID and CLIENT_ID and CLIENT_SECRET and USER_ID:
        print("Credentials found — listing root items...")
        items = await onedrive_list_items()
        print(f"  OK: {len(items)} item(s) at root.")
    else:
        print("Azure credentials / OUTLOOK_USER_ID not set — skipping live call.")
    print("\nTo serve:\n  python onedrive.py --serve\n  python onedrive.py --serve --transport http --port 8005")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8005)
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
