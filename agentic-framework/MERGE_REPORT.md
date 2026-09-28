# Integration Merge Report - Exception/Search Revision

Base: previous enterprise-agent-framework-merged build (latest working framework base)
Enhancement source: Elango's code.zip

## Changes integrated
- Replaced the centralized exception infrastructure with Elango's newer implementation.
- Added normalization of unexpected exceptions to ExecutionError in the exception_handler decorator.
- Added synchronous and asynchronous exception-handler support.
- Preserved FrameworkError details/structured display and centralized logging behavior.
- Added exception-handler coverage to agent, tool, workflow, guardrail, KB, RAG and runtime layers where present in Elango's implementation.
- Integrated Elango's AgentRegistry search implementation and Agent Search CLI.
- Integrated workflow search/registry/CLI improvements from Elango.
- Preserved the previous merged logging/observability implementation and newer framework UI/system-status/main entrypoint.
- Preserved HP Smart Print Fleet agents/workflow/tool definitions from the previous merged build.

## Important behavior
Unexpected exceptions raised inside @exception_handler are now logged centrally and converted to ExecutionError, allowing CLI layers to handle them consistently instead of leaking raw exceptions.

Search supports:
- Agent: Practice Area
- Agent: Good At
- Agent: Keyword
- Workflow: Practice Area
- Workflow: Good At
- Workflow: Keyword

Generated runtime logs/cache files should not be committed.
