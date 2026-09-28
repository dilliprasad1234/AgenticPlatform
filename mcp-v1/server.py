"""
MCP Server (gateway) — merges github.py, testrail.py, postgresql.py and
jira.py into ONE server that client.py connects to. All four connectors'
operations are exposed under this single MCP endpoint; the individual
files are still valid standalone servers if you ever want to isolate one,
but this is the file you actually run day to day.

Non-blocking / parallel by design: every underlying operation is an
`async def` built on httpx.AsyncClient / asyncpg (non-blocking I/O), and
`--transport http` serves them over an ASGI app (uvicorn) on asyncio's
event loop — many client requests are handled concurrently in one
process, none of them blocking the others while waiting on a network
call or a database round-trip.

Modes:
  python server.py
      Standalone smoke test. Prints every merged operation from all four
      connectors and exits. No client/network needed.

  python server.py --serve
      Starts the MCP server over stdio, for a client that launches this
      script as a subprocess.

  python server.py --serve --transport http --port 8000
      Runs independently as its own long-lived process on the network.
      Any number of clients connect to http://<host>:<port>/mcp, and it
      handles them concurrently (see note above).
"""

import argparse
import asyncio
import importlib

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="all-connectors-gateway",
    instructions=(
        "Unified gateway: create/read/update/delete operations against "
        "GitHub, TestRail, PostgreSQL and Jira, all under one MCP endpoint."
    ),
)

# Each entry: (module file name without .py, human label). Import errors
# (e.g. a missing optional dependency like asyncpg) don't take the whole
# gateway down — that connector is skipped and everything else still works.
CONNECTOR_MODULES = [
    ("github", "GitHub"),
    ("github_enterprise", "GitHub Enterprise"),
    ("testrail", "TestRail"),
    ("postgresql", "PostgreSQL"),
    ("jira", "Jira"),
    ("confluence", "Confluence (also covers Wiki pages)"),
    ("sharepoint", "SharePoint"),
    ("onedrive", "OneDrive"),
    ("teams", "Microsoft Teams"),
    ("outlook", "Outlook"),
    ("files", "Local files (PDF/Word/Excel/CSV/Markdown/PPT/Plain text) & filesystem"),
]

_loaded: list[str] = []
_skipped: list[tuple[str, str]] = []


def _merge_tools(source_mcp: FastMCP, label: str) -> int:
    """Copy another FastMCP instance's registered tools onto this gateway's."""
    count = 0
    for name, tool in source_mcp._tool_manager._tools.items():
        mcp._tool_manager._tools[name] = tool
        count += 1
    return count


def _load_all_connectors():
    for module_name, label in CONNECTOR_MODULES:
        try:
            module = importlib.import_module(module_name)
            n = _merge_tools(module.mcp, label)
            _loaded.append(f"{label} ({n} operations)")
        except Exception as exc:  # missing dependency, import-time error, etc.
            _skipped.append((label, str(exc)))


_load_all_connectors()


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
async def _smoke_test():
    print("Connectors loaded:")
    for line in _loaded:
        print(f"  - {line}")
    if _skipped:
        print("\nConnectors skipped (see each module's own env vars / dependencies):")
        for label, reason in _skipped:
            print(f"  - {label}: {reason}")

    tool_names = list(mcp._tool_manager._tools.keys())
    print(f"\n{len(tool_names)} total merged operations:")
    for name in tool_names:
        print(f"  - {name}")

    print()
    print("To actually serve requests:")
    print("  python server.py --serve")
    print("  python server.py --serve --transport http --port 8000")


def main():
    parser = argparse.ArgumentParser(description="Unified MCP gateway (GitHub + TestRail + PostgreSQL + Jira)")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
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
        print(f"Connectors loaded: {', '.join(_loaded) if _loaded else '(none)'}")
        if _skipped:
            print(f"Connectors skipped: {', '.join(label for label, _ in _skipped)}")
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
