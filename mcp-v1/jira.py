"""
MCP Server — Jira connectivity.

Exposes create/read/update/delete operations against Jira Cloud's REST API
(Issues, Comments, Projects) for any MCP-compatible client/agent to call.

Environment variables required:
  JIRA_BASE_URL     e.g. https://yourcompany.atlassian.net
  JIRA_EMAIL        the account email
  JIRA_API_TOKEN    API token from id.atlassian.com/manage-profile/security/api-tokens

Modes:
  python jira.py
      Standalone smoke test. No client/network needed. Prints registered
      operations and, if credentials are set, makes one live read-only
      call. Runs and exits.

  python jira.py --serve
      Starts the MCP server over stdio, for a client that launches this
      script as a subprocess.

  python jira.py --serve --transport http --port 8003
      Runs independently as its own long-lived process on the network.
      Any number of clients connect to http://<host>:<port>/mcp.
"""

import argparse
import asyncio
import os

import httpx
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")  # single shared .env for all connectors

mcp = FastMCP(
    name="jira-connector",
    instructions="Create/read/update/delete operations against Jira (issues, comments, projects).",
)

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")


def _require_config():
    if not (JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN):
        raise RuntimeError("JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN must all be set.")


def _adf(text: str) -> dict:
    """Wrap plain text in Jira's Atlassian Document Format, required for description/comment bodies."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def _jira_request(method: str, path: str, json_body: dict | None = None):
    _require_config()
    url = f"{JIRA_BASE_URL}/rest/api/3/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method,
            url,
            json=json_body,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


# --- Issues ----------------------------------------------------------------

@mcp.tool()
async def jira_get_issue(issue_key: str) -> dict:
    """Get a Jira issue by key, e.g. 'PROJ-123'."""
    return await _jira_request("GET", f"issue/{issue_key}")


@mcp.tool()
async def jira_search_issues(jql: str, max_results: int = 20) -> list:
    """Search issues with JQL, e.g. 'project = PROJ AND status = "In Progress"'."""
    data = await _jira_request(
        "GET", f"search?jql={httpx.QueryParams({'jql': jql})['jql']}&maxResults={max_results}"
    )
    return data.get("issues", [])


@mcp.tool()
async def jira_create_issue(
    project_key: str, summary: str, issue_type: str = "Task", description: str = "",
    fields: dict | None = None,
) -> dict:
    """Create a Jira issue. `fields` can add extras, e.g. {"priority": {"name": "High"}}."""
    payload_fields = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
        **(fields or {}),
    }
    if description:
        payload_fields["description"] = _adf(description)
    data = await _jira_request("POST", "issue", {"fields": payload_fields})
    return {"key": data["key"], "id": data["id"], "url": f"{JIRA_BASE_URL}/browse/{data['key']}"}


@mcp.tool()
async def jira_update_issue(issue_key: str, fields: dict) -> dict:
    """
    Update a Jira issue's fields, e.g. {"summary": "..."} or
    {"description": "plain text"} (auto-converted to ADF).
    """
    fields = dict(fields)
    if "description" in fields and isinstance(fields["description"], str):
        fields["description"] = _adf(fields["description"])
    await _jira_request("PUT", f"issue/{issue_key}", {"fields": fields})
    return {"updated_issue": issue_key, "updated_fields": list(fields)}


@mcp.tool()
async def jira_delete_issue(issue_key: str) -> dict:
    """Permanently delete a Jira issue. Irreversible."""
    await _jira_request("DELETE", f"issue/{issue_key}")
    return {"deleted_issue": issue_key}


# --- Comments ----------------------------------------------------------------

@mcp.tool()
async def jira_get_comments(issue_key: str) -> list:
    """List comments on an issue."""
    data = await _jira_request("GET", f"issue/{issue_key}/comment")
    return data.get("comments", [])


@mcp.tool()
async def jira_add_comment(issue_key: str, body: str) -> dict:
    """Add a plain-text comment to an issue (auto-converted to ADF)."""
    data = await _jira_request("POST", f"issue/{issue_key}/comment", {"body": _adf(body)})
    return {"comment_id": data["id"]}


@mcp.tool()
async def jira_update_comment(issue_key: str, comment_id: str, body: str) -> dict:
    """Update an existing comment's text."""
    await _jira_request("PUT", f"issue/{issue_key}/comment/{comment_id}", {"body": _adf(body)})
    return {"updated_comment_id": comment_id}


@mcp.tool()
async def jira_delete_comment(issue_key: str, comment_id: str) -> dict:
    """Delete a comment from an issue. Irreversible."""
    await _jira_request("DELETE", f"issue/{issue_key}/comment/{comment_id}")
    return {"deleted_comment_id": comment_id}


# --- Projects ----------------------------------------------------------------

@mcp.tool()
async def jira_list_projects() -> list:
    """List all Jira projects visible to the authenticated account."""
    data = await _jira_request("GET", "project/search")
    return data.get("values", data)


@mcp.tool()
async def jira_get_project(project_key: str) -> dict:
    """Get a single Jira project by key."""
    return await _jira_request("GET", f"project/{project_key}")


@mcp.tool()
async def jira_create_project(
    key: str, name: str, project_type_key: str = "software", lead_account_id: str | None = None
) -> dict:
    """Create a Jira project. `lead_account_id` is required by most Jira sites — pass the lead's accountId."""
    payload = {"key": key, "name": name, "projectTypeKey": project_type_key}
    if lead_account_id:
        payload["leadAccountId"] = lead_account_id
    return await _jira_request("POST", "project", payload)


@mcp.tool()
async def jira_delete_project(project_key: str) -> dict:
    """Permanently delete a Jira project and its issues. Irreversible."""
    await _jira_request("DELETE", f"project/{project_key}")
    return {"deleted_project": project_key}


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
async def _smoke_test():
    tool_names = list(mcp._tool_manager._tools.keys())
    print(f"Registered {len(tool_names)} MCP operations:")
    for name in tool_names:
        print(f"  - {name}")
    print()
    if JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN:
        print("Credentials found — listing projects to confirm connectivity...")
        result = await jira_list_projects()
        print(f"  OK: {len(result)} project(s) found.")
    else:
        print("JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN not fully set — skipping live call.")
    print()
    print("To actually serve requests:")
    print("  python jira.py --serve")
    print("  python jira.py --serve --transport http --port 8003")


def main():
    parser = argparse.ArgumentParser(description="Jira MCP connector")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()

    if not args.serve:
        asyncio.run(_smoke_test())
        return

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"Serving MCP over HTTP at http://{args.host}:{args.port}/mcp (Ctrl+C to stop)")
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
