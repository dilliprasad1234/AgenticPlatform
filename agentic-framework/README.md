# Enterprise Agent Framework

A CLI-first enterprise agent framework for creating, managing, and executing AI agents, tools, workflows, guardrails, and RAG knowledge bases.

## Final merged components

The final framework uses the **Elango branch structure as the base** and incorporates:

- Agent, workflow, and tool orchestration from `enterprise-agent-framework-initial-Elango_Branch`
- Framework/agent/tool execution logging from the main branch
- Guardrail definitions, CRUD, registry, generation, execution, and auditing from `enterprise-agent-framework-initial-PreProd_Branch_Dilli`
- Multi-provider LLM support and RAG knowledge-base functionality from `enterprise-agent-framework-initial-sairanjani-changes`
- Elango's additional workflow builder, graph/orchestration, loop, and execution logging files are retained

## Project structure

```text
enterprise-agent-framework/
├── agents/
│   ├── definitions/
│   └── *.py
├── guardrails/
│   ├── definitions/
│   ├── implementations/
│   └── *.py
├── kb/
├── tools/
│   ├── definitions/
│   ├── implementations/
│   └── *.py
├── workflows/
│   ├── definitions/
│   └── *.py
├── inputs/
│   └── rag/
├── logs/
├── data/
│   └── chromadb/
├── src/
│   ├── cli/
│   ├── llm/
│   ├── observability/
│   ├── rag/
│   ├── runtime/
│   └── utils/
├── main.py
├── pyproject.toml
└── requirements.txt
```

## Installation

Python 3.11+ is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or install the project in editable mode:

```powershell
pip install -e ".[dev,llm,rag]"
```

## Configuration

Copy `.env.example` to `.env` when present and configure the provider required by your environment.

### Specification-generation LLM

Set:

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_HOST=http://localhost:11434
```

or configure `gemini`, `openai`, or `anthropic` and its corresponding credentials.

### Agent execution LLM

The runtime accepts `EXECUTION_LLM_PROVIDER`. If it is not set, it falls back to `LLM_PROVIDER`.

Supported execution providers:

- `openai`
- `anthropic`
- `ollama`
- `groq`
- `gemini`

Set the matching model variable, for example:

```text
EXECUTION_LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_HOST=http://localhost:11434
```

## Run

Interactive CLI:

```powershell
python main.py
```

After installation:

```powershell
eaf
```

Direct agent execution:

```powershell
python -m src.app <agent_id>
```

## Guardrails

Guardrails are selected in an agent definition through the `guardrails` list.

The merged runtime applies guardrails according to the guardrail definition's `type`:

- `input` — before agent execution
- `output` — after agent execution
- `content` or `both` — both phases

The configured action controls failures:

- `block` — stop execution
- `warn` — log the failure and continue

Guardrail execution is audited and can be correlated with framework logs.

## RAG

The Knowledge Base menu supports:

1. Create Knowledge Base
2. Add documents
3. List knowledge bases
4. Remove documents
5. Delete knowledge bases

Supported indexed formats:

- `.txt`
- `.md`
- `.csv`
- `.json`
- `.yaml`
- `.yml`
- `.log`
- `.pdf`
- `.docx`

RAG uses ChromaDB for persistent collections. The `knowledge_search` framework tool can be attached to an agent and used to retrieve relevant chunks with source filenames.

## Logging

Framework observability is stored under `logs/`. It is split into two independent levels: framework logs and execution logs.

```text
logs/
├── framework/
│   └── YYYY-MM-DD/
│       ├── framework.log
│       └── framework.log.1 ...
└── executions/
    ├── agents/
    │   └── YYYY-MM-DD/
    │       ├── Agent1.log
    │       └── Agent1.log.1 ...
    ├── workflows/
    │   └── YYYY-MM-DD/
    │       ├── Workflow1.log
    │       └── Workflow1.log.1 ...
    ├── guardrails/
    │   └── YYYY-MM-DD/
    │       └── Guardrail1.log
    ├── tools/
    │   └── YYYY-MM-DD/
    │       └── Tool1.log
    └── rag/
        └── YYYY-MM-DD/
            └── KnowledgeBase1.log
```

Secrets such as API keys, tokens, passwords, authorization values, and cookies are redacted from execution logs.

## Validation performed on the merged source

The final source tree was checked for:

- Python syntax compilation across all Python files
- Module-level docstrings across all Python files
- Internal absolute-import consistency
- Agent YAML loading
- Workflow YAML loading
- Tool discovery and loading
- Guardrail implementation discovery
- Guardrail pass/fail execution
- Mock LLM agent/tool/workflow/guardrail generation smoke tests
- Generated tool/guardrail Python syntax validation

CrewAI, provider SDKs, and ChromaDB remain runtime dependencies for their respective features.


## Logging and Observability

The framework uses a two-level logging model. Both levels use the same 10 MB size rotation, date-based partitioning, secret masking, and level colour coding.

### 1. Execution-level logs

Execution logs are grouped first by **execution component**, then by **date**, then by the concrete component being executed. There is intentionally no generic per-run `execution.log`; the component/entity file is the execution log.

```text
Execution logs
│
├── Agents
│   ├── YYYY-MM-DD
│   │   ├── Agent1.log
│   │   └── Agent2.log
│   └── YYYY-MM-DD
│       ├── Agent1.log
│       └── Agent2.log
│
├── Workflows
│   ├── YYYY-MM-DD
│   │   ├── Workflow1.log
│   │   └── Workflow2.log
│   └── YYYY-MM-DD
│       ├── Workflow1.log
│       └── Workflow2.log
│
├── Guardrails
├── Tools
└── RAG (KB)
```

For example, executing `Agent1` five times on the same day writes five correlated execution records to `executions/agents/YYYY-MM-DD/Agent1.log`. When that file reaches 10 MB it rotates to `Agent1.log.1`, `Agent1.log.2`, and so on. On the next day, a new `YYYY-MM-DD` directory is used automatically.

Workflow executions preserve the same trace ID across nested agents, guardrails, tools, and RAG operations. Each nested event is therefore available in the appropriate component/entity log while retaining cross-component correlation.

Standalone agents, workflows, tools, guardrails, and RAG operations create their own execution context. Nested executions reuse the existing context so the existing runtime behaviour is not changed.

### 2. Framework-level logs

Framework lifecycle, CLI, configuration, registry, initialization, and system-level events remain date based:

```text
logs/
└── framework/
    └── YYYY-MM-DD/
        ├── framework.log
        └── framework.log.1 ...
```

### Log levels

- **INFO** — green
- **DEBUG** — blue
- **ERROR** — red
- **WARNING** — yellow

The same colour coding is used for console output and persisted logs.

### Rotation and configuration

The default maximum size of each individual log file is 10 MB. Configure it with:

```text
EAF_LOG_DIR=logs
EAF_LOG_MAX_FILE_BYTES=10485760
EAF_LOG_BACKUP_COUNT=20
EAF_LOG_MAX_VALUE_LENGTH=12000
EAF_CONSOLE_LOG_LEVEL=INFO
```

The logging layer is centralized in `src/observability/logging.py`. Existing modules continue to call `log_event`, `log_exception`, `span`, `start_run`, and `end_run`; only the persistence layout has changed.

## Merged release additions

This release uses the Framework CLI/navigation and observability design as the baseline while incorporating additional capabilities from the final implementation:

- Contextual CLI navigation: `B` returns to the immediately previous screen; `0` exits.
- Workflow search by Practice Area, Good At, and Keyword.
- Structured workflow Practice Area / Good At selection.
- Agent and workflow input-format guidance with executable samples.
- Knowledge-base retrieval during configured agent execution.
- Tool input schema/sample display before execution.
- OCR fallback for scanned PDFs.
- Centralized framework exception handling and LLM response validation.
- Additional agent, workflow, tool, guardrail, and RAG sample definitions.

### OCR note

OCR support uses PyMuPDF, Pillow, and pytesseract. For scanned-PDF OCR, the Tesseract OCR executable must also be installed on the operating system and available on `PATH`. Normal text-based PDF extraction does not require OCR.

