"""
MCP Server — TestRail connectivity.

Exposes create/read/update/delete operations against TestRail's REST API
(Projects, Test Cases, Test Runs, Milestones) for any MCP-compatible
client/agent to call.

Environment variables required:
  TESTRAIL_URL       e.g. https://yourcompany.testrail.io
  TESTRAIL_USER      the account email
  TESTRAIL_API_KEY   API key from TestRail > My Settings > API Keys

Modes:
  python testrail.py
      Standalone smoke test. No client/network needed. Prints registered
      operations and, if credentials are set, makes one live read-only
      call. Runs and exits.

  python testrail.py --serve
      Starts the MCP server over stdio, for a client that launches this
      script as a subprocess.

  python testrail.py --serve --transport http --port 8001
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
    name="testrail-connector",
    instructions="Create/read/update/delete operations against TestRail (projects, cases, runs, milestones).",
)

TESTRAIL_URL = os.environ.get("TESTRAIL_URL", "").rstrip("/")
TESTRAIL_USER = os.environ.get("TESTRAIL_USER")
TESTRAIL_API_KEY = os.environ.get("TESTRAIL_API_KEY")


def _require_config():
    if not (TESTRAIL_URL and TESTRAIL_USER and TESTRAIL_API_KEY):
        raise RuntimeError(
            "TESTRAIL_URL, TESTRAIL_USER and TESTRAIL_API_KEY must all be set."
        )


async def _tr_request(method: str, path: str, json_body: dict | None = None):
    """Call TestRail's API (index.php?/api/v2/<path>) with basic auth."""
    _require_config()
    url = f"{TESTRAIL_URL}/index.php?/api/v2/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method,
            url,
            json=json_body,
            auth=(TESTRAIL_USER, TESTRAIL_API_KEY),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


# --- Projects ----------------------------------------------------------

@mcp.tool()
async def testrail_list_projects() -> list:
    """List all TestRail projects."""
    data = await _tr_request("GET", "get_projects")
    return data.get("projects", data)


@mcp.tool()
async def testrail_get_project(project_id: int) -> dict:
    """Get a single TestRail project by id."""
    return await _tr_request("GET", f"get_project/{project_id}")


@mcp.tool()
async def testrail_create_project(
    name: str, announcement: str = "", show_announcement: bool = False, suite_mode: int = 1
) -> dict:
    """Create a new TestRail project. suite_mode: 1=single suite, 2=single+baselines, 3=multiple suites."""
    return await _tr_request(
        "POST",
        "add_project",
        {
            "name": name,
            "announcement": announcement,
            "show_announcement": show_announcement,
            "suite_mode": suite_mode,
        },
    )


@mcp.tool()
async def testrail_update_project(project_id: int, fields: dict) -> dict:
    """Update a TestRail project. fields e.g. {"name": "...", "is_completed": true}."""
    return await _tr_request("POST", f"update_project/{project_id}", fields)


@mcp.tool()
async def testrail_delete_project(project_id: int) -> dict:
    """Permanently delete a TestRail project and all its data. Irreversible."""
    await _tr_request("POST", f"delete_project/{project_id}")
    return {"deleted_project_id": project_id}


# --- Test cases ----------------------------------------------------------

@mcp.tool()
async def testrail_list_cases(project_id: int, suite_id: int | None = None) -> list:
    """List test cases in a project (optionally scoped to a suite)."""
    path = f"get_cases/{project_id}"
    if suite_id is not None:
        path += f"&suite_id={suite_id}"
    data = await _tr_request("GET", path)
    return data.get("cases", data)


@mcp.tool()
async def testrail_get_case(case_id: int) -> dict:
    """Get a single test case by id."""
    return await _tr_request("GET", f"get_case/{case_id}")


@mcp.tool()
async def testrail_create_case(section_id: int, title: str, fields: dict | None = None) -> dict:
    """Create a test case in a section. fields e.g. {"priority_id": 3, "type_id": 1}."""
    payload = {"title": title, **(fields or {})}
    return await _tr_request("POST", f"add_case/{section_id}", payload)


@mcp.tool()
async def testrail_update_case(case_id: int, fields: dict) -> dict:
    """Update a test case. fields e.g. {"title": "...", "priority_id": 2}."""
    return await _tr_request("POST", f"update_case/{case_id}", fields)


@mcp.tool()
async def testrail_delete_case(case_id: int) -> dict:
    """Permanently delete a test case. Irreversible."""
    await _tr_request("POST", f"delete_case/{case_id}")
    return {"deleted_case_id": case_id}


# --- Test runs ----------------------------------------------------------

@mcp.tool()
async def testrail_list_runs(project_id: int) -> list:
    """List test runs in a project."""
    data = await _tr_request("GET", f"get_runs/{project_id}")
    return data.get("runs", data)


@mcp.tool()
async def testrail_get_run(run_id: int) -> dict:
    """Get a single test run by id."""
    return await _tr_request("GET", f"get_run/{run_id}")


@mcp.tool()
async def testrail_create_run(
    project_id: int, name: str, suite_id: int | None = None, fields: dict | None = None
) -> dict:
    """Create a test run in a project. fields e.g. {"include_all": true, "milestone_id": 5}."""
    payload = {"name": name, **(fields or {})}
    if suite_id is not None:
        payload["suite_id"] = suite_id
    return await _tr_request("POST", f"add_run/{project_id}", payload)


@mcp.tool()
async def testrail_update_run(run_id: int, fields: dict) -> dict:
    """Update a test run. fields e.g. {"name": "...", "include_all": false}."""
    return await _tr_request("POST", f"update_run/{run_id}", fields)


@mcp.tool()
async def testrail_close_run(run_id: int) -> dict:
    """Close a test run (locks it from further result submissions)."""
    return await _tr_request("POST", f"close_run/{run_id}")


@mcp.tool()
async def testrail_delete_run(run_id: int) -> dict:
    """Permanently delete a test run and its results. Irreversible."""
    await _tr_request("POST", f"delete_run/{run_id}")
    return {"deleted_run_id": run_id}


# --- Milestones ----------------------------------------------------------

@mcp.tool()
async def testrail_list_milestones(project_id: int) -> list:
    """List milestones in a project."""
    data = await _tr_request("GET", f"get_milestones/{project_id}")
    return data.get("milestones", data)


@mcp.tool()
async def testrail_get_milestone(milestone_id: int) -> dict:
    """Get a single milestone by id."""
    return await _tr_request("GET", f"get_milestone/{milestone_id}")


@mcp.tool()
async def testrail_create_milestone(project_id: int, name: str, fields: dict | None = None) -> dict:
    """Create a milestone in a project. fields e.g. {"description": "...", "due_on": 1735689600}."""
    payload = {"name": name, **(fields or {})}
    return await _tr_request("POST", f"add_milestone/{project_id}", payload)


@mcp.tool()
async def testrail_update_milestone(milestone_id: int, fields: dict) -> dict:
    """Update a milestone. fields e.g. {"is_completed": true}."""
    return await _tr_request("POST", f"update_milestone/{milestone_id}", fields)


@mcp.tool()
async def testrail_delete_milestone(milestone_id: int) -> dict:
    """Permanently delete a milestone. Irreversible."""
    await _tr_request("POST", f"delete_milestone/{milestone_id}")
    return {"deleted_milestone_id": milestone_id}


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
async def _smoke_test():
    tool_names = list(mcp._tool_manager._tools.keys())
    print(f"Registered {len(tool_names)} MCP operations:")
    for name in tool_names:
        print(f"  - {name}")
    print()
    if TESTRAIL_URL and TESTRAIL_USER and TESTRAIL_API_KEY:
        print("Credentials found — listing projects to confirm connectivity...")
        result = await testrail_list_projects()
        print(f"  OK: {len(result)} project(s) found.")
    else:
        print("TESTRAIL_URL / TESTRAIL_USER / TESTRAIL_API_KEY not fully set — skipping live call.")
    print()
    print("To actually serve requests:")
    print("  python testrail.py --serve")
    print("  python testrail.py --serve --transport http --port 8001")


def main():
    parser = argparse.ArgumentParser(description="TestRail MCP connector")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
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
