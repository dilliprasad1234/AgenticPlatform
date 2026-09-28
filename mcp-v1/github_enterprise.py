"""
MCP Connector — GitHub Enterprise (self-hosted GHE instance).

Same operations as github.py (Repos, Files, Issues CRUD) but against a
GitHub Enterprise Server's own API base URL instead of api.github.com.

Env vars (shared .env):
  GITHUB_ENTERPRISE_URL    e.g. https://github.yourcompany.com
  GITHUB_ENTERPRISE_TOKEN
"""

import argparse
import asyncio
import base64
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")

mcp = FastMCP(
    name="github-enterprise-connector",
    instructions="CRUD operations against a self-hosted GitHub Enterprise instance (repos, issues, files).",
)

GHE_URL = os.environ.get("GITHUB_ENTERPRISE_URL", "").rstrip("/")
GHE_TOKEN = os.environ.get("GITHUB_ENTERPRISE_TOKEN")
# GHE's REST API is served under /api/v3 on the enterprise hostname.
GHE_API = f"{GHE_URL}/api/v3"


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GHE_TOKEN:
        headers["Authorization"] = f"Bearer {GHE_TOKEN}"
    return headers


def _require_token():
    if not (GHE_URL and GHE_TOKEN):
        raise RuntimeError("GITHUB_ENTERPRISE_URL and GITHUB_ENTERPRISE_TOKEN must be set.")


# --- Read ------------------------------------------------------------------

@mcp.tool()
async def ghe_get_user(username: str) -> dict:
    """Get a user's profile from GitHub Enterprise."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GHE_API}/users/{username}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def ghe_list_repos(org: str, limit: int = 10) -> list:
    """List repositories in a GitHub Enterprise organization."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GHE_API}/orgs/{org}/repos", params={"per_page": limit}, headers=_headers()
        )
        resp.raise_for_status()
        return [{"name": r["name"], "url": r["html_url"]} for r in resp.json()]


@mcp.tool()
async def ghe_get_file(owner: str, repo: str, path: str, ref: str | None = None) -> dict:
    """Read a file's decoded content and sha from a GHE repository."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GHE_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref} if ref else None,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return {"path": data["path"], "sha": data["sha"], "content": content}


# --- Repos -------------------------------------------------------------

@mcp.tool()
async def ghe_create_repo(org: str, name: str, description: str = "", private: bool = True) -> dict:
    """Create a repository under a GHE organization."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GHE_API}/orgs/{org}/repos",
            json={"name": name, "description": description, "private": private},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {"name": data["name"], "url": data["html_url"]}


@mcp.tool()
async def ghe_update_repo(owner: str, repo: str, description: str | None = None, private: bool | None = None) -> dict:
    """Update a GHE repository's settings."""
    _require_token()
    payload = {k: v for k, v in {"description": description, "private": private}.items() if v is not None}
    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{GHE_API}/repos/{owner}/{repo}", json=payload, headers=_headers())
        resp.raise_for_status()
        return {"updated_fields": list(payload)}


@mcp.tool()
async def ghe_delete_repo(owner: str, repo: str) -> dict:
    """Permanently delete a GHE repository. Irreversible."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{GHE_API}/repos/{owner}/{repo}", headers=_headers())
        resp.raise_for_status()
        return {"deleted": f"{owner}/{repo}"}


# --- Issues ------------------------------------------------------------

@mcp.tool()
async def ghe_create_issue(owner: str, repo: str, title: str, body: str = "") -> dict:
    """Create an issue in a GHE repository."""
    _require_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GHE_API}/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}


@mcp.tool()
async def ghe_update_issue(
    owner: str, repo: str, issue_number: int,
    title: str | None = None, body: str | None = None, state: str | None = None,
) -> dict:
    """Update a GHE issue's title, body, and/or open/closed state."""
    _require_token()
    payload = {k: v for k, v in {"title": title, "body": body, "state": state}.items() if v is not None}
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GHE_API}/repos/{owner}/{repo}/issues/{issue_number}", json=payload, headers=_headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "state": data["state"]}


@mcp.tool()
async def ghe_delete_issue(owner: str, repo: str, issue_number: int) -> dict:
    """Delete-equivalent for a GHE issue: closes it (REST API has no hard-delete for issues)."""
    return await ghe_update_issue(owner, repo, issue_number, state="closed")


# --- Files ---------------------------------------------------------------

@mcp.tool()
async def ghe_create_or_update_file(
    owner: str, repo: str, path: str, content: str, commit_message: str, branch: str | None = None
) -> dict:
    """Create or update a file in a GHE repository. Looks up the current sha automatically."""
    _require_token()
    async with httpx.AsyncClient() as client:
        sha = None
        existing = await client.get(
            f"{GHE_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch} if branch else None,
            headers=_headers(),
        )
        if existing.status_code == 200:
            sha = existing.json()["sha"]
        payload = {"message": commit_message, "content": base64.b64encode(content.encode()).decode()}
        if branch:
            payload["branch"] = branch
        if sha:
            payload["sha"] = sha
        resp = await client.put(
            f"{GHE_API}/repos/{owner}/{repo}/contents/{path}", json=payload, headers=_headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return {"action": "updated" if sha else "created", "path": data["content"]["path"]}


@mcp.tool()
async def ghe_delete_file(owner: str, repo: str, path: str, commit_message: str, branch: str | None = None) -> dict:
    """Delete a file from a GHE repository."""
    _require_token()
    async with httpx.AsyncClient() as client:
        existing = await client.get(
            f"{GHE_API}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch} if branch else None,
            headers=_headers(),
        )
        existing.raise_for_status()
        payload = {"message": commit_message, "sha": existing.json()["sha"]}
        if branch:
            payload["branch"] = branch
        resp = await client.request(
            "DELETE", f"{GHE_API}/repos/{owner}/{repo}/contents/{path}", json=payload, headers=_headers()
        )
        resp.raise_for_status()
        return {"deleted": path}


# --- Smoke test / entry point --------------------------------------------

async def _smoke_test():
    print(f"Registered {len(mcp._tool_manager._tools)} operations:")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print()
    if GHE_URL and GHE_TOKEN:
        print(f"Credentials found for {GHE_URL} — not making a live call (org unknown). Ready.")
    else:
        print("GITHUB_ENTERPRISE_URL / GITHUB_ENTERPRISE_TOKEN not set — skipping live call.")
    print("\nTo serve:\n  python github_enterprise.py --serve\n  python github_enterprise.py --serve --transport http --port 8007")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8007)
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
