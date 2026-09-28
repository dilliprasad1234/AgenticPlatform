"""
MCP Server — PostgreSQL connectivity.

Exposes create/read/update/delete operations against a PostgreSQL database
(tables and rows) for any MCP-compatible client/agent to call.

Environment variables required:
  PG_HOST       default: localhost
  PG_PORT       default: 5432
  PG_DATABASE
  PG_USER
  PG_PASSWORD

Modes:
  python postgresql.py
      Standalone smoke test. No client/network needed. Prints registered
      operations and, if credentials are set, makes one live read-only
      call. Runs and exits.

  python postgresql.py --serve
      Starts the MCP server over stdio, for a client that launches this
      script as a subprocess.

  python postgresql.py --serve --transport http --port 8002
      Runs independently as its own long-lived process on the network.
      Any number of clients connect to http://<host>:<port>/mcp.
"""

import argparse
import asyncio
import os
import re

import asyncpg
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent / ".env")  # single shared .env for all connectors

mcp = FastMCP(
    name="postgresql-connector",
    instructions="Create/read/update/delete operations against a PostgreSQL database (tables and rows).",
)

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DATABASE = os.environ.get("PG_DATABASE")
PG_USER = os.environ.get("PG_USER")
PG_PASSWORD = os.environ.get("PG_PASSWORD")

_pool: asyncpg.Pool | None = None
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(name: str) -> str:
    """
    asyncpg can't parametrize identifiers (table/column names), so validate
    them against a strict allow-list pattern before interpolating into SQL.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(f"'{name}' is not a safe identifier (letters, digits, underscore only).")
    return name


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not (PG_DATABASE and PG_USER):
            raise RuntimeError("PG_DATABASE and PG_USER (and usually PG_PASSWORD) must be set.")
        _pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DATABASE, user=PG_USER, password=PG_PASSWORD,
            min_size=1, max_size=5,
        )
    return _pool


def _build_where(where: dict, start_idx: int = 1) -> tuple[str, list]:
    clauses, values = [], []
    for i, (col, val) in enumerate(where.items(), start=start_idx):
        clauses.append(f"{_safe_ident(col)} = ${i}")
        values.append(val)
    return " AND ".join(clauses), values


# --- Schema / DDL --------------------------------------------------------

@mcp.tool()
async def pg_list_tables(schema: str = "public") -> list:
    """List table names in a schema."""
    pool = await _get_pool()
    rows = await pool.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = $1 ORDER BY table_name",
        schema,
    )
    return [r["table_name"] for r in rows]


@mcp.tool()
async def pg_describe_table(table: str, schema: str = "public") -> list:
    """Describe a table's columns, types, and nullability."""
    pool = await _get_pool()
    rows = await pool.fetch(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = $1 AND table_name = $2 ORDER BY ordinal_position",
        schema, table,
    )
    return [dict(r) for r in rows]


@mcp.tool()
async def pg_create_table(table: str, columns: dict, schema: str = "public") -> dict:
    """
    Create a table. `columns` maps column name -> SQL type/constraint, e.g.
    {"id": "serial primary key", "name": "text not null", "created_at": "timestamptz default now()"}.
    """
    _safe_ident(table)
    col_defs = ", ".join(f"{_safe_ident(col)} {sqltype}" for col, sqltype in columns.items())
    pool = await _get_pool()
    await pool.execute(f'CREATE TABLE {_safe_ident(schema)}.{_safe_ident(table)} ({col_defs})')
    return {"created_table": f"{schema}.{table}"}


@mcp.tool()
async def pg_drop_table(table: str, schema: str = "public", cascade: bool = False) -> dict:
    """Drop a table. Irreversible. Set cascade=true to also drop dependent objects."""
    pool = await _get_pool()
    suffix = " CASCADE" if cascade else ""
    await pool.execute(f'DROP TABLE {_safe_ident(schema)}.{_safe_ident(table)}{suffix}')
    return {"dropped_table": f"{schema}.{table}"}


# --- Row CRUD --------------------------------------------------------------

@mcp.tool()
async def pg_select_rows(
    table: str, where: dict | None = None, limit: int = 100, schema: str = "public"
) -> list:
    """Select rows from a table, optionally filtered by an equality `where` dict."""
    pool = await _get_pool()
    query = f'SELECT * FROM {_safe_ident(schema)}.{_safe_ident(table)}'
    values = []
    if where:
        clause, values = _build_where(where)
        query += f" WHERE {clause}"
    query += f" LIMIT {int(limit)}"
    rows = await pool.fetch(query, *values)
    return [dict(r) for r in rows]


@mcp.tool()
async def pg_insert_row(table: str, values: dict, schema: str = "public") -> dict:
    """Insert one row into a table. `values` maps column name -> value."""
    pool = await _get_pool()
    cols = [_safe_ident(c) for c in values.keys()]
    placeholders = [f"${i}" for i in range(1, len(cols) + 1)]
    query = (
        f'INSERT INTO {_safe_ident(schema)}.{_safe_ident(table)} ({", ".join(cols)}) '
        f'VALUES ({", ".join(placeholders)}) RETURNING *'
    )
    row = await pool.fetchrow(query, *values.values())
    return dict(row)


@mcp.tool()
async def pg_update_rows(table: str, values: dict, where: dict, schema: str = "public") -> list:
    """
    Update rows matching `where` (equality dict), setting columns in `values`.
    `where` is required — pass a condition that matches all rows if you really
    mean to update the whole table.
    """
    if not where:
        raise ValueError("`where` must not be empty — pass an explicit condition.")
    pool = await _get_pool()
    set_cols = [_safe_ident(c) for c in values.keys()]
    set_clause = ", ".join(f"{c} = ${i}" for i, c in enumerate(set_cols, start=1))
    where_clause, where_values = _build_where(where, start_idx=len(set_cols) + 1)
    query = (
        f'UPDATE {_safe_ident(schema)}.{_safe_ident(table)} SET {set_clause} '
        f'WHERE {where_clause} RETURNING *'
    )
    rows = await pool.fetch(query, *values.values(), *where_values)
    return [dict(r) for r in rows]


@mcp.tool()
async def pg_delete_rows(table: str, where: dict, schema: str = "public") -> list:
    """Delete rows matching `where` (equality dict, required). Returns the deleted rows."""
    if not where:
        raise ValueError("`where` must not be empty — pass an explicit condition.")
    pool = await _get_pool()
    where_clause, where_values = _build_where(where)
    query = f'DELETE FROM {_safe_ident(schema)}.{_safe_ident(table)} WHERE {where_clause} RETURNING *'
    rows = await pool.fetch(query, *where_values)
    return [dict(r) for r in rows]


@mcp.tool()
async def pg_execute_query(query: str, params: list | None = None) -> list:
    """
    Generic passthrough for any parametrized SQL statement (use $1, $2, ... in
    `query` and pass matching `params`). Use the dedicated tools above where
    possible; use this for anything they don't cover (joins, aggregates, etc.).
    """
    pool = await _get_pool()
    rows = await pool.fetch(query, *(params or []))
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
async def _smoke_test():
    tool_names = list(mcp._tool_manager._tools.keys())
    print(f"Registered {len(tool_names)} MCP operations:")
    for name in tool_names:
        print(f"  - {name}")
    print()
    if PG_DATABASE and PG_USER:
        print("Credentials found — listing tables to confirm connectivity...")
        try:
            result = await pg_list_tables()
            print(f"  OK: {len(result)} table(s) found in schema 'public'.")
        finally:
            if _pool:
                await _pool.close()
    else:
        print("PG_DATABASE / PG_USER not set — skipping live call.")
    print()
    print("To actually serve requests:")
    print("  python postgresql.py --serve")
    print("  python postgresql.py --serve --transport http --port 8002")


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL MCP connector")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
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
