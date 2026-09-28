# Local validation: Fleet + external MCP + Neon

## 1. Start the independent MCP server

Use the separately maintained MCP server project. It must not be copied into the Enterprise Agent Framework.

The Neon-ready MCP server accepts `DATABASE_URL` directly:

```powershell
$env:DATABASE_URL = "<your Neon PostgreSQL URL>"
python server.py --serve --transport http --port 8000
```

Keep this terminal running.

## 2. Verify MCP discovery from the MCP project

In another terminal:

```powershell
python client.py --http http://127.0.0.1:8000/mcp list
```

Confirm the PostgreSQL operations are visible, including:

- `pg_list_tables`
- `pg_describe_table`
- `pg_select_rows`
- `pg_execute_query`

Then verify database access:

```powershell
python client.py --http http://127.0.0.1:8000/mcp call pg_list_tables '{"schema":"public"}'
```

## 3. Configure the framework as an MCP client

In the Enterprise Agent Framework terminal:

```powershell
$env:MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
```

Install the framework dependencies in its virtual environment:

```powershell
python -m pip install -r requirements.txt
```

The `mcp` Python package is required by the client-side connector. The framework does not start the MCP server.

## 4. Start the framework

```powershell
python main.py
```

The Tool Management / Agent Management screens should show:

- `mcp_server_connector`
- `knowledge_search`
- `Fleet Data Collector Agent`
- `Fleet Analyzer Agent`
- `Fleet Recommendation Agent`
- `HP Smart Print Fleet Optimization`

## 5. Run the Fleet workflow

Select the Fleet workflow and enter JSON similar to:

```json
{
  "objective": "Retrieve the printer fleet records from the external MCP server and analyze them for maintenance, warranty, supply, connectivity, utilization, and fleet balancing opportunities.",
  "schema": "public"
}
```

The Collector agent should first discover MCP tools, inspect PostgreSQL tables, describe the relevant table, and retrieve rows. It must not connect directly to Neon.

## 6. Expected architecture

```text
Framework CLI
    |
    v
Fleet Workflow
    |
    +--> Fleet Data Collector
    |       |
    |       +--> mcp_server_connector
    |               |
    |               v
    |        External MCP Server
    |               |
    |               v
    |             Neon
    |
    +--> Fleet Analyzer
    |       +--> Fleet RAG policies
    |
    +--> Fleet Recommendation
            +--> Fleet RAG policies/rules
```

## 7. Security rules

- Do not place the Neon connection string in the framework ZIP.
- Do not commit `.env` files containing credentials.
- The framework only knows the MCP endpoint.
- The external MCP server owns database/API credentials and connectivity.
- Fleet MCP access is intended for read-oriented retrieval. Destructive MCP operation names are blocked by the framework connector's default safety policy.
