"""
MCP Connector — Microsoft Teams (via Microsoft Graph API).

Operations: Teams, Channels, Channel messages, 1:1/group Chats.
Auth: Azure AD app — same credentials as sharepoint.py/onedrive.py.

Env vars (shared .env):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
  TEAMS_USER_ID   (UPN or object ID — used as the sender identity for chats)
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
    name="teams-connector",
    instructions="CRUD operations on Microsoft Teams teams, channels, messages and chats.",
)

TENANT_ID = os.environ.get("AZURE_TENANT_ID")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
TEAMS_USER_ID = os.environ.get("TEAMS_USER_ID")
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
            method, f"{GRAPH}/{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=json_body, params=params,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


# --- Teams / Channels ------------------------------------------------------

@mcp.tool()
async def teams_list_joined_teams() -> list:
    """List teams the configured user belongs to."""
    if not TEAMS_USER_ID:
        raise RuntimeError("TEAMS_USER_ID must be set.")
    data = await _graph("GET", f"users/{TEAMS_USER_ID}/joinedTeams")
    return data.get("value", [])


@mcp.tool()
async def teams_list_channels(team_id: str) -> list:
    """List channels in a team."""
    data = await _graph("GET", f"teams/{team_id}/channels")
    return data.get("value", [])


@mcp.tool()
async def teams_create_channel(team_id: str, display_name: str, description: str = "") -> dict:
    """Create a new channel in a team."""
    return await _graph(
        "POST", f"teams/{team_id}/channels",
        {"displayName": display_name, "description": description},
    )


@mcp.tool()
async def teams_delete_channel(team_id: str, channel_id: str) -> dict:
    """Delete a channel from a team. Irreversible."""
    await _graph("DELETE", f"teams/{team_id}/channels/{channel_id}")
    return {"deleted_channel_id": channel_id}


# --- Channel messages ------------------------------------------------------

@mcp.tool()
async def teams_list_channel_messages(team_id: str, channel_id: str, limit: int = 20) -> list:
    """List recent messages in a channel."""
    data = await _graph("GET", f"teams/{team_id}/channels/{channel_id}/messages", params={"$top": limit})
    return data.get("value", [])


@mcp.tool()
async def teams_send_channel_message(team_id: str, channel_id: str, content: str) -> dict:
    """Post a message to a channel."""
    return await _graph(
        "POST", f"teams/{team_id}/channels/{channel_id}/messages",
        {"body": {"content": content}},
    )


@mcp.tool()
async def teams_update_channel_message(team_id: str, channel_id: str, message_id: str, content: str) -> dict:
    """Update (edit) a previously sent channel message."""
    return await _graph(
        "PATCH", f"teams/{team_id}/channels/{channel_id}/messages/{message_id}",
        {"body": {"content": content}},
    )


@mcp.tool()
async def teams_delete_channel_message(team_id: str, channel_id: str, message_id: str) -> dict:
    """Soft-delete (mark deleted) a channel message."""
    await _graph("DELETE", f"teams/{team_id}/channels/{channel_id}/messages/{message_id}")
    return {"deleted_message_id": message_id}


# --- 1:1 / group chats -------------------------------------------------

@mcp.tool()
async def teams_list_chats() -> list:
    """List chats for the configured user."""
    if not TEAMS_USER_ID:
        raise RuntimeError("TEAMS_USER_ID must be set.")
    data = await _graph("GET", f"users/{TEAMS_USER_ID}/chats")
    return data.get("value", [])


@mcp.tool()
async def teams_send_chat_message(chat_id: str, content: str) -> dict:
    """Send a message in an existing 1:1 or group chat."""
    return await _graph("POST", f"chats/{chat_id}/messages", {"body": {"content": content}})


@mcp.tool()
async def teams_list_chat_messages(chat_id: str, limit: int = 20) -> list:
    """List recent messages in a chat."""
    data = await _graph("GET", f"chats/{chat_id}/messages", params={"$top": limit})
    return data.get("value", [])


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if TENANT_ID and CLIENT_ID and CLIENT_SECRET and TEAMS_USER_ID:
        print("Credentials found — listing joined teams...")
        teams = await teams_list_joined_teams()
        print(f"  OK: {len(teams)} team(s) found.")
    else:
        print("Azure credentials / TEAMS_USER_ID not set — skipping live call.")
    print("\nTo serve:\n  python teams.py --serve\n  python teams.py --serve --transport http --port 8009")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8009)
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
