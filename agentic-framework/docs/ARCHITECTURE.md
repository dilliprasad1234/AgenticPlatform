# Architecture

Current milestone: CLI control-plane/scaffolding.

```text
AgentSpec / WorkflowSpec / ToolSpec
              |
              v
        Your framework
              |
              v
        CrewAI Adapter
              |
              v
     CrewAI Agent / Crew / Flow
```

CrewAI is intentionally isolated from CLI and schema layers. The next milestone adds Tool Registry + Policy + CrewAI tool adapters, then workflow execution.
