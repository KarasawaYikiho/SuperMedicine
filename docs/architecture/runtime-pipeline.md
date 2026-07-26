# Runtime Pipeline

## Stable execution order

Every task enters the Kernel through a public surface, receives canonical
permission evaluation, and is wrapped by the Harness lifecycle. Local RAG
retrieval is part of the default execution context. The Harness finalizes the
result before it returns to CLI, TUI, Web, Desktop, or an adapter.

```text
surface -> application service -> permission -> harness begin
        -> local RAG context -> single-agent or optional multi-agent work
        -> harness finalize -> result
```

## Mandatory Harness and RAG

Harness and RAG are required runtime capabilities. They are enabled by default,
have no supported disable switch, and fail closed when required storage or
runtime state is missing, damaged, or unwritable.

## Optional Multi-Agent

Multi-Agent remains an explicit option. Disabled execution uses the
single-agent path. Enabled execution preserves Alpha analysis, Beta review,
Gamma writing, Delta orchestration, checkpoint persistence, and resume.

## Surface boundary

CLI, OpenTUI, Web, Desktop, Standalone, OpenCode, and Claude Code adapters call
application services; they do not construct permission engines, plugin
registries, or internal stores directly.
