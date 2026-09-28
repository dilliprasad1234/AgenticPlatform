# External MCP Server Integration

## Architecture

The Enterprise Agent Framework contains only an MCP **client-side tool**. It does not start, host, own, or embed the MCP server.

```text
Enterprise Agent Framework
        |
        | MCP Server Connector
        | Streamable HTTP
        v
External MCP Server (independent process/service)
        |
        +-- PostgreSQL / Neon
        +-- JIRA
        +-- Azure DevOps
        +-- TestRail
```

Any future agent can select the `mcp_server_connector` framework tool when it needs an MCP-backed integration. The framework does not need connector-specific database/API code.

## Configure the endpoint

Set the external server endpoint in the framework environment:

```powershell
$env:MCP_SERVER_URL="http://127.0.0.1:8000/mcp"
```

For a remote deployment, use that server's Streamable HTTP MCP endpoint instead.

Do not put database passwords, API keys, or tokens in this repository.

## Fleet workflow

The Fleet workflow intentionally permits only read-only PostgreSQL MCP operations:

- `list_tools`
- `pg_list_tables`
- `pg_describe_table`
- `pg_select_rows`
- `pg_execute_query` with read-only SQL (`SELECT`, `WITH`, `SHOW`, `EXPLAIN`)

The external MCP server remains responsible for authenticating to Neon and other enterprise systems.
