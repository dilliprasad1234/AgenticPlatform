"""
MCP Server — connects to third-party applications and exposes operations
that any MCP-compatible client/agent can call.

This example wires up GitHub's REST API as the third-party application,
with full create / read / update / delete operations across repos, issues
and file contents, plus one generic HTTP-passthrough operation you can
point at *any* REST API (Slack, Jira, Notion, your internal services, etc.)
without writing a new server for each one.

Modes:
  python server.py
      Standalone smoke test — no client/network needed. Prints the
      registered operations and, if GITHUB_TOKEN is set, does one live
      read-only call to prove connectivity. Runs and exits; that's it.

  python server.py --serve
      Starts the MCP server over stdio, for a client that launches this
      script as a subprocess (see client.py). Nothing to run by hand —
      a client process talks to this over stdin/stdout.

  python server.py --serve --transport http --port 8000
      Starts the MCP server as its own long-running process, listening
      on the network (Streamable HTTP transport). This is what "run
      independently" means: start it once, in its own terminal/service,
      and any number of clients connect to http://<host>:<port>/mcp
      without you having to launch it as a subprocess each time.
"""

import argparse
import asyncio
import base64
import os
import sys

import httpx
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")  # single shared .env for all connectors

# ---------------------------------------------------------------------------
# 1. Create the MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="third-party-connector",
    instructions=(
        "Provides create/read/update/delete operations against third-party "
        "applications (GitHub, and any generic REST API) for agents "
        "connected over MCP."
    ),
)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # required for write operations


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _require_token():
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is not set — write operations (create/update/delete) "
            "need an authenticated token with the right scopes."
        )


# ---------------------------------------------------------------------------
# 2. Operations — each @mcp.tool() becomes something an MCP client can call.
#    Add one function per operation you want to expose; the docstring and
#    type hints become the schema the connecting agent sees.
# ---------------------------------------------------------------------------

# --- Read operations --------------------------------------------------------

@mcp.tool()
async def github_get_user(username: str) -> dict:
    """Get public profile information for a GitHub user."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GITHUB_API}/users/{username}", headers=_github_headers())
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def github_list_repos(username: str, limit: int = 10) -> list:
    """List public repositories for a GitHub user, most recently updated first."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"sort": "updated", "per_page": limit},
            headers=_github_headers(),
        )
        resp.raise_for_status()
        return [
            {"name": r["name"], "url": r["html_url"], "stars": r["stargazers_count"]}
            for r in resp.json()
        ]


@mcp.tool()
async def github_get_file(owner: str, repo: str, path: str, ref: str | None = None) -> dict:
    """Read a file's decoded text content and sha from a GitHub repository."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref} if ref else None,
            headers=_github_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return {"path": data["path"], "sha": data["sha"], "content": content}


# --- Repository CRUD ---------------------------------------------------------

@mcp.tool()
async def github_create_repo(name: str, description: str = "", private: bool = False) -> dict:
    """Create a new GitHub repository under the authenticated user's account."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/user/repos",
            json={"name": name, "description": description, "private": private},
            headers=_github_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {"name": data["name"], "url": data["html_url"]}


@mcp.tool()
async def github_update_repo(
    owner: str,
    repo: str,
    description: str | None = None,
    private: bool | None = None,
    default_branch: str | None = None,
) -> dict:
    """Update a GitHub repository's settings (description, visibility, default branch)."""
    _require_token()
    payload = {
        k: v
        for k, v in {
            "description": description,
            "private": private,
            "default_branch": default_branch,
        }.items()
        if v is not None
    }
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}", json=payload, headers=_github_headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return {"name": data["name"], "url": data["html_url"], "updated_fields": list(payload)}


@mcp.tool()
async def github_delete_repo(owner: str, repo: str) -> dict:
    """Permanently delete a GitHub repository. Requires delete_repo scope. Irreversible."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_github_headers())
        resp.raise_for_status()
        return {"deleted": f"{owner}/{repo}"}


# --- Issue CRUD (GitHub has no hard-delete for issues; "close" is the
#     delete-equivalent the API supports) --------------------------------

@mcp.tool()
async def github_create_issue(owner: str, repo: str, title: str, body: str = "") -> dict:
    """Create an issue in a GitHub repository."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body},
            headers=_github_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}


@mcp.tool()
async def github_update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,  # "open" or "closed"
) -> dict:
    """Update an existing issue's title, body, and/or open/closed state."""
    _require_token()
    payload = {k: v for k, v in {"title": title, "body": body, "state": state}.items() if v is not None}
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}",
            json=payload,
            headers=_github_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "state": data["state"], "url": data["html_url"]}


@mcp.tool()
async def github_delete_issue(owner: str, repo: str, issue_number: int) -> dict:
    """
    Delete-equivalent for a GitHub issue. The REST API cannot hard-delete
    issues (only org owners can, via a separate GraphQL mutation), so this
    closes the issue and marks it "not planned".
    """
    return await github_update_issue(owner, repo, issue_number, state="closed")


# --- File CRUD (GitHub's contents API is create-and-update in one call) ----

@mcp.tool()
async def github_create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    commit_message: str,
    branch: str | None = None,
) -> dict:
    """
    Create a new file, or update an existing one, at `path` in a repository.
    Automatically looks up the current file's sha first so updates don't
    conflict; pass plain text in `content` (it's base64-encoded for you).
    """
    _require_token()
    async with httpx.AsyncClient() as client:
        sha = None
        existing = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch} if branch else None,
            headers=_github_headers(),
        )
        if existing.status_code == 200:
            sha = existing.json()["sha"]

        payload = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if branch:
            payload["branch"] = branch
        if sha:
            payload["sha"] = sha  # required by GitHub to update rather than create

        resp = await client.put(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            json=payload,
            headers=_github_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "action": "updated" if sha else "created",
            "path": data["content"]["path"],
            "sha": data["content"]["sha"],
            "commit_url": data["commit"]["html_url"],
        }


@mcp.tool()
async def github_delete_file(
    owner: str, repo: str, path: str, commit_message: str, branch: str | None = None
) -> dict:
    """Delete a file from a GitHub repository. Looks up the file's current sha automatically."""
    _require_token()
    async with httpx.AsyncClient() as client:
        existing = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch} if branch else None,
            headers=_github_headers(),
        )
        existing.raise_for_status()
        sha = existing.json()["sha"]

        payload = {"message": commit_message, "sha": sha}
        if branch:
            payload["branch"] = branch

        resp = await client.request(
            "DELETE",
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            json=payload,
            headers=_github_headers(),
        )
        resp.raise_for_status()
        return {"deleted": path, "commit_url": resp.json()["commit"]["html_url"]}


# --- Generic passthrough ----------------------------------------------------

@mcp.tool()
async def http_request(
    method: str,
    url: str,
    headers: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """
    Generic passthrough to any third-party REST API. Use this to reach
    services that don't have dedicated tools yet (Slack, Jira, Notion, an
    internal service, etc.). method is GET/POST/PUT/PATCH/DELETE.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method.upper(), url, headers=headers, json=json_body)
        content_type = resp.headers.get("content-type", "")
        return {
            "status_code": resp.status_code,
            "body": resp.json() if "application/json" in content_type else resp.text,
        }


# ---------------------------------------------------------------------------
# 3. Standalone smoke test — runs with no client, no network setup
# ---------------------------------------------------------------------------
async def _smoke_test():
    tool_names = [t for t in mcp._tool_manager._tools.keys()]
    print(f"Registered {len(tool_names)} MCP operations:")
    for name in tool_names:
        print(f"  - {name}")

    print()
    if GITHUB_TOKEN:
        print("GITHUB_TOKEN found — making one live read-only call to confirm connectivity...")
        result = await github_get_user(username="anthropics")
        print(f"  OK: fetched profile for '{result.get('login')}' ({result.get('html_url')})")
    else:
        print("GITHUB_TOKEN not set — skipping a live call. Read-only GitHub tools still work")
        print("unauthenticated at a lower rate limit; write operations need a token.")

    print()
    print("This process is done (no server was started). To actually serve requests:")
    print("  python server.py --serve                        # stdio, for client.py to launch")
    print("  python server.py --serve --transport http --port 8000   # standalone over HTTP")


# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Third-party app MCP connector")
    parser.add_argument("--serve", action="store_true", help="start the MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio: launched as a subprocess by one client (default). "
        "http: run as its own standalone process on the network.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="host to bind for --transport http")
    parser.add_argument("--port", type=int, default=8000, help="port to bind for --transport http")
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
