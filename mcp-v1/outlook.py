"""
MCP Connector — Outlook (Mail + Calendar, via Microsoft Graph API).

Operations: Mail messages, Mail folders, Calendar events.
Auth: Azure AD app — same credentials as sharepoint.py/onedrive.py/teams.py.

Env vars (shared .env):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
  OUTLOOK_USER_ID   (mailbox owner's UPN or object ID)
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
    name="outlook-connector",
    instructions="CRUD operations on Outlook mail messages, mail folders and calendar events.",
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


def _mailbox() -> str:
    if not USER_ID:
        raise RuntimeError("OUTLOOK_USER_ID must be set.")
    return f"users/{USER_ID}"


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


# --- Mail: read ------------------------------------------------------------

@mcp.tool()
async def outlook_list_messages(folder: str = "inbox", limit: int = 20) -> list:
    """List messages in a mail folder (default: inbox)."""
    mb = _mailbox()
    data = await _graph(
        "GET", f"{mb}/mailFolders/{folder}/messages",
        params={"$top": limit, "$select": "id,subject,from,receivedDateTime,isRead"},
    )
    return data.get("value", [])


@mcp.tool()
async def outlook_get_message(message_id: str) -> dict:
    """Get a full message by ID, including body."""
    mb = _mailbox()
    return await _graph("GET", f"{mb}/messages/{message_id}")


@mcp.tool()
async def outlook_search_messages(query: str, limit: int = 20) -> list:
    """Search messages across the mailbox."""
    mb = _mailbox()
    data = await _graph("GET", f"{mb}/messages", params={"$search": f'"{query}"', "$top": limit})
    return data.get("value", [])


# --- Mail: create / send ----------------------------------------------------

@mcp.tool()
async def outlook_send_message(to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict:
    """Send an email. to/cc are lists of email addresses."""
    mb = _mailbox()
    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": a}} for a in to],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": a}} for a in cc]
    await _graph("POST", f"{mb}/sendMail", {"message": message})
    return {"sent_to": to}


@mcp.tool()
async def outlook_create_draft(to: list[str], subject: str, body: str) -> dict:
    """Create a draft email (not sent)."""
    mb = _mailbox()
    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": a}} for a in to],
    }
    return await _graph("POST", f"{mb}/messages", message)


# --- Mail: update / delete ---------------------------------------------

@mcp.tool()
async def outlook_update_message(message_id: str, is_read: bool | None = None, categories: list[str] | None = None) -> dict:
    """Update a message's read status and/or categories."""
    mb = _mailbox()
    payload = {}
    if is_read is not None:
        payload["isRead"] = is_read
    if categories is not None:
        payload["categories"] = categories
    return await _graph("PATCH", f"{mb}/messages/{message_id}", payload)


@mcp.tool()
async def outlook_delete_message(message_id: str) -> dict:
    """Delete (move to Deleted Items) a message."""
    mb = _mailbox()
    await _graph("DELETE", f"{mb}/messages/{message_id}")
    return {"deleted_message_id": message_id}


# --- Mail folders ------------------------------------------------------

@mcp.tool()
async def outlook_list_folders() -> list:
    """List mail folders in the mailbox."""
    mb = _mailbox()
    data = await _graph("GET", f"{mb}/mailFolders")
    return data.get("value", [])


@mcp.tool()
async def outlook_create_folder(display_name: str) -> dict:
    """Create a new top-level mail folder."""
    mb = _mailbox()
    return await _graph("POST", f"{mb}/mailFolders", {"displayName": display_name})


@mcp.tool()
async def outlook_delete_folder(folder_id: str) -> dict:
    """Delete a mail folder. Irreversible."""
    mb = _mailbox()
    await _graph("DELETE", f"{mb}/mailFolders/{folder_id}")
    return {"deleted_folder_id": folder_id}


# --- Calendar ------------------------------------------------------------

@mcp.tool()
async def outlook_list_events(limit: int = 20) -> list:
    """List upcoming calendar events."""
    mb = _mailbox()
    data = await _graph("GET", f"{mb}/events", params={"$top": limit, "$orderby": "start/dateTime"})
    return data.get("value", [])


@mcp.tool()
async def outlook_create_event(
    subject: str, start_iso: str, end_iso: str, attendees: list[str] | None = None, body: str = "",
) -> dict:
    """Create a calendar event. start_iso/end_iso e.g. '2026-10-01T14:00:00'."""
    mb = _mailbox()
    payload = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "start": {"dateTime": start_iso, "timeZone": "UTC"},
        "end": {"dateTime": end_iso, "timeZone": "UTC"},
    }
    if attendees:
        payload["attendees"] = [{"emailAddress": {"address": a}, "type": "required"} for a in attendees]
    return await _graph("POST", f"{mb}/events", payload)


@mcp.tool()
async def outlook_update_event(event_id: str, fields: dict) -> dict:
    """Update a calendar event. fields e.g. {"subject": "...", "start": {"dateTime": "...", "timeZone": "UTC"}}."""
    mb = _mailbox()
    return await _graph("PATCH", f"{mb}/events/{event_id}", fields)


@mcp.tool()
async def outlook_delete_event(event_id: str) -> dict:
    """Delete (cancel) a calendar event."""
    mb = _mailbox()
    await _graph("DELETE", f"{mb}/events/{event_id}")
    return {"deleted_event_id": event_id}


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if TENANT_ID and CLIENT_ID and CLIENT_SECRET and USER_ID:
        print("Credentials found — listing inbox...")
        msgs = await outlook_list_messages(limit=5)
        print(f"  OK: {len(msgs)} message(s) found.")
    else:
        print("Azure credentials / OUTLOOK_USER_ID not set — skipping live call.")
    print("\nTo serve:\n  python outlook.py --serve\n  python outlook.py --serve --transport http --port 8010")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
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
