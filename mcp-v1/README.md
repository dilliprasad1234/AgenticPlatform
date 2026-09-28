# MCP Gateway — 11 connectors, one server, one client

`server.py` merges eleven connectors into a single MCP endpoint.
`client.py` talks to it. Same pattern as before, just more coverage.

## Connectors

| File | Covers | Auth needed |
|---|---|---|
| `github.py` | GitHub (repos, issues, files) | `GITHUB_TOKEN` |
| `github_enterprise.py` | GitHub Enterprise (self-hosted) | `GITHUB_ENTERPRISE_URL`, `GITHUB_ENTERPRISE_TOKEN` |
| `testrail.py` | TestRail (projects, cases, runs, milestones) | `TESTRAIL_URL/USER/API_KEY` |
| `postgresql.py` | PostgreSQL (any table) | `PG_HOST/PORT/DATABASE/USER/PASSWORD` |
| `jira.py` | Jira (issues, comments, projects) | `JIRA_BASE_URL/EMAIL/API_TOKEN` |
| `confluence.py` | Confluence (spaces, pages, comments) — **also covers Wiki pages** | `CONFLUENCE_URL/EMAIL/API_TOKEN` |
| `sharepoint.py` | SharePoint (sites, lists, items, files) | Azure AD app (`AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET`) + `SHAREPOINT_SITE_URL` |
| `onedrive.py` | OneDrive (files, folders) | Same Azure app + `OUTLOOK_USER_ID` |
| `teams.py` | Microsoft Teams (channels, messages, chats) | Same Azure app + `TEAMS_USER_ID` |
| `outlook.py` | Outlook (mail, folders, calendar) | Same Azure app + `OUTLOOK_USER_ID` |
| `files.py` | **PDF, Word, Excel, CSV, Markdown, PPT, Plain text, local folders, Windows filesystem** | none — works on local paths; optional `FILES_ROOT_DIR` |

An unconfigured connector (missing env vars or an uninstalled optional
dependency) is skipped at startup — the rest still load. `server.py`
prints which loaded and which didn't, with why.

### Note on "Wiki pages"
There's no separate `wiki.py` — Confluence *is* the enterprise wiki in
most stacks, so its page/space/comment operations in `confluence.py`
cover that item. If you actually meant a different wiki system
(Azure DevOps Wiki, MediaWiki, a GitHub repo wiki, etc.), tell me which
one and I'll add a dedicated connector for it.

### Note on `files.py`
This one's different from the rest — no third-party account, it just
operates on paths on the machine running the server. Give it any path:
a Windows path (`C:\Users\you\Documents\report.docx`), a network share,
or a relative path resolved against `FILES_ROOT_DIR` if you set one.
Not every format supports every CRUD verb the same way (a PDF isn't
"updatable" the way a database row is) — see **Operations exposed**
below for exactly what each format supports.

## Setup

```bash
pip install -r requirements.txt
```

Fill in `.env` for whichever connectors you're using. **Values must be
plain strings — no quotes, no brackets, no Markdown link syntax.** This
bit several people:
```
GOOD:  JIRA_BASE_URL=https://foo.atlassian.net
BAD:   JIRA_BASE_URL='https://foo.atlassian.net'
BAD:   JIRA_BASE_URL=[https://foo.atlassian.net](https://foo.atlassian.net)
```
`.env` is only read at server startup — restart the server after editing it.

### Setting up the Azure AD app (SharePoint / OneDrive / Teams / Outlook)
These four share one Azure AD app registration:
1. portal.azure.com → **App registrations** → **New registration**.
2. Note the **Application (client) ID** and **Directory (tenant) ID** → `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`.
3. **Certificates & secrets** → new client secret → `AZURE_CLIENT_SECRET`.
4. **API permissions** → add Application permissions (not Delegated) for whichever you're using: `Sites.ReadWrite.All`, `Files.ReadWrite.All`, `ChannelMessage.Send`, `Chat.ReadWrite`, `Team.ReadBasic.All`, `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite` — then **Grant admin consent**.
5. `SHAREPOINT_SITE_URL` is your site's URL as it appears in the browser. `OUTLOOK_USER_ID` / `TEAMS_USER_ID` is the mailbox/user's UPN (email) or Azure AD object ID.

## Running the gateway

```bash
python server.py
```
Standalone smoke test — prints every connector's load status and every merged operation. Exits.

```bash
python server.py --serve --transport http --port 8000
```
**Runs independently, non-blocking, parallel.** Start once, leave running; any number of clients connect to `http://127.0.0.1:8000/mcp` concurrently.

## Using the client

```bash
python client.py --http http://127.0.0.1:8000/mcp list
python client.py --http http://127.0.0.1:8000/mcp call jira_get_issue "{\"issue_key\": \"PROJ-1\"}"
python client.py --http http://127.0.0.1:8000/mcp call files_read_text --args-file args.json
```
(`--args-file` sidesteps shell-quoting headaches — see the top of `client.py` for examples. `--script server.py` still works if you'd rather have the client spawn the gateway over stdio.)

## Operations exposed

**github.py / github_enterprise.py** — Repos: `create/update/delete_repo`. Files: `get/create_or_update/delete_file`. Issues: `create/update/delete_issue`. Also `get_user`, `list_repos` (prefix `github_` / `ghe_`).

**testrail.py** — Projects, Cases, Runs, Milestones — each with `list/get/create/update/delete`, plus `testrail_close_run`.

**postgresql.py** — `pg_list_tables`, `pg_describe_table`, `pg_create_table`, `pg_drop_table`, `pg_select_rows`, `pg_insert_row`, `pg_update_rows`, `pg_delete_rows`, `pg_execute_query`.

**jira.py** — Issues, Comments, Projects — each with matching `get/list/create/update/delete`.

**confluence.py** — Spaces (`list/get`), Pages (`list/get/create/update/delete/search`), Comments (`list/add/delete`).

**sharepoint.py** — Sites (`get/list_subsites`), Lists (`list/create/delete`), List items (`list/create/update/delete`), Files (`list/read/upload/delete`).

**onedrive.py** — Browse (`list_items/get_item`), Read, Write (`create_folder/upload_file/move_item/copy_item`), Delete, Search.

**teams.py** — Teams/Channels (`list/create/delete`), Channel messages (`list/send/update/delete`), Chats (`list/send/list_messages`).

**outlook.py** — Mail (`list/get/search/send/create_draft/update/delete_message`), Folders (`list/create/delete`), Calendar (`list/create/update/delete_event`).

**files.py**:
| Format | Read | Create | Update | Delete |
|---|---|---|---|---|
| Plain text / Markdown | `text_read` | `text_write` | `text_write(mode="append")` | `fs_delete` |
| CSV | `csv_read` | `csv_write` | `csv_append_row` | `fs_delete` |
| PDF | `pdf_read_text`, `pdf_get_info` | `pdf_create` | `pdf_append_page`* | `fs_delete` |
| Word (.docx) | `docx_read` | `docx_create` | `docx_append_paragraph`, `docx_replace_text` | `fs_delete` |
| Excel (.xlsx) | `xlsx_read` | `xlsx_create` | `xlsx_update_cell`, `xlsx_append_row` | `fs_delete` |
| PowerPoint (.pptx) | `pptx_read` | `pptx_create` | `pptx_add_slide` | `fs_delete` |
| Folders / Windows filesystem | `fs_list_dir`, `fs_get_info` | `fs_create_dir` | `fs_move`, `fs_copy` | `fs_delete` |

\* PDF's underlying format doesn't support in-place edits the way the others do — `pdf_append_page` rebuilds the file with a new page appended rather than editing existing content.

### Notes on "delete" where the underlying API doesn't really delete
- `github_delete_issue` / `ghe_delete_issue` close the issue (GitHub's REST API has no hard-delete for issues).
- `confluence_delete_page` trashes rather than permanently purges (standard Confluence behavior).
- `outlook_delete_message` moves to Deleted Items, matching normal Outlook behavior.
- Everything else is a genuine, irreversible delete — take care with `*_delete_repo`, `*_delete_project`, `pg_drop_table`, `fs_delete(recursive=true)`, and `sharepoint/onedrive_delete_*`.

## How connectivity and merging work

Same as before: `server.py` imports each connector module — which
registers its own `@mcp.tool()` functions on its own `FastMCP` instance
without starting a server — then copies every tool onto its own merged
instance. A connector that fails to import (missing dependency, bad
config) is caught and skipped; the rest keep working. `client.py`
connects via stdio (subprocess) or HTTP (`streamablehttp_client`) and
calls operations by name through `ClientSession.call_tool`.

## Adding another connector

Copy the closest existing file as a template (a REST-API-with-auth app →
`jira.py`; a Graph-API app → `outlook.py`; local files → `files.py`),
keep its shape (config helper, one `@mcp.tool()` per operation,
`_smoke_test()`, `main()`), add it to `CONNECTOR_MODULES` in `server.py`,
and it's merged in automatically.
