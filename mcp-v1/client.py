"""
MCP Client — connects to any one of the servers in this folder
(github.py, testrail.py, postgresql.py, jira.py) and calls its operations
directly. This is the "agent uses MCP connectivity" side: no LLM
tool-selection loop required — your own code decides which operation to
call and with what arguments.

List what a server can do:
    python client.py --script server.py list

Call an operation by name with JSON arguments (server.py is the unified
gateway — it exposes every connector's operations under one endpoint):
    python client.py --script server.py call jira_get_issue '{"issue_key": "PROJ-1"}'
    python client.py --script server.py call pg_select_rows '{"table": "users", "limit": 5}'
    python client.py --script server.py call testrail_list_projects '{}'
    python client.py --script server.py call github_get_user '{"username": "anthropics"}'

Connect to a server already running independently over HTTP instead of
spawning it as a subprocess (server started with
`python <script> --serve --transport http --port <port>`):
    python client.py --http http://127.0.0.1:8003/mcp list
    python client.py --http http://127.0.0.1:8003/mcp call jira_get_issue '{"issue_key": "PROJ-1"}'
"""

import argparse
import asyncio
import json
import sys
import traceback

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


async def call_operation(session: ClientSession, name: str, arguments: dict) -> str:
    """Call one MCP tool/operation by name and return its text result."""
    result = await session.call_tool(name, arguments=arguments)
    parts = []
    for block in result.content:
        if block.type == "text":
            parts.append(block.text)
        else:
            parts.append(f"[{block.type} content]")
    return "\n".join(parts)


async def run(session: ClientSession, args):
    await session.initialize()

    if args.command == "list":
        tools = await session.list_tools()
        print(f"{len(tools.tools)} available operations:")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description}")
        return

    # args.command == "call"
    try:
        arguments = json.loads(args.args_json)
    except json.JSONDecodeError as e:
        print(f"--args must be valid JSON: {e}")
        sys.exit(1)

    print(f"-> {args.tool_name}({args.args_json})")
    print(await call_operation(session, args.tool_name, arguments))


async def main():
    parser = argparse.ArgumentParser(description="Generic MCP client for this folder's servers")
    conn = parser.add_mutually_exclusive_group()
    conn.add_argument(
        "--script",
        default="server.py",
        help="server script to launch over stdio (default: server.py, the unified gateway). "
        "Or point at an individual connector: github.py / testrail.py / postgresql.py / jira.py.",
    )
    conn.add_argument(
        "--http",
        metavar="URL",
        help="connect to a standalone HTTP server instead, e.g. http://127.0.0.1:8003/mcp",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list the server's available operations")
    call_p = sub.add_parser("call", help="call one operation")
    call_p.add_argument("tool_name", help="operation name, e.g. jira_get_issue")
    call_p.add_argument("args_json", help="JSON object of arguments, e.g. '{\"issue_key\": \"PROJ-1\"}'")

    args = parser.parse_args()
    # argparse positional collision: map "call" args back onto our namespace
    if args.command == "call":
        args.tool_name = args.tool_name
        args.args_json = args.args_json

    print(
        f"Connecting via {'HTTP -> ' + args.http if args.http else f'stdio (spawning {args.script})'} ...",
        flush=True,
    )
    try:
        if args.http:
            async with streamablehttp_client(args.http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await run(session, args)
        else:
            server_params = StdioServerParameters(
                command=sys.executable, args=[args.script, "--serve"], env=None
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await run(session, args)
    except Exception:
        print("Client failed with an exception:", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
