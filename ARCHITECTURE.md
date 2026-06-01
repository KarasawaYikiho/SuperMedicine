# SuperMedicine Architecture

This root architecture reference describes the public **Beta0.4.0** design. The
Python package fallback version is **0.4.0b0**. Engineering notes in excluded
folders are intentionally not referenced here.

## Overview

SuperMedicine uses a microkernel plus multi-agent orchestration architecture for
an independent Python medical research assistant framework. The Kernel wires
configuration, events, plugin discovery, sessions, workspace state, LLM provider
management, and runtime permission enforcement. Optional OpenCode and Claude Code
adapters wrap the core; they are not initialization requirements.

```text
CLI / TUI / Optional Adapters
        |
        v
Kernel
  - ConfigCenter
  - EventBus
  - PluginRegistry
  - SessionManager
  - PermissionEngine
        |
        +--> Agent orchestration and checkpoint state
        +--> Plugins: RAG, harness, tools, standards
        +--> Workspace layer: papers, experience, tool assets
        +--> LLM provider clients and token tracking
```

## Layer 1: Microkernel (`core/`)

- **ConfigCenter** reads YAML configuration, supports `SM_*` environment
  overrides, and exposes redacted LLM provider snapshots.
- **EventBus** provides topic-based publish/subscribe messaging.
- **PluginRegistry** discovers `plugin.yaml` manifests and records plugin
  capabilities.
- **SessionManager** creates UUID sessions and stores session-scoped state.
- **WorkspaceManager** anchors workspaces under `workspaces/<id>`, rejects path
  traversal and non-slug ids, and supports workspace-local papers, notes,
  outputs, checkpoints, sessions, and RAG assets.
- **TUI backend controllers** share the same core paths as the CLI. TUI recent
  selection is not an implicit CLI default.

## Layer 2: Permission System (`permission/`)

The permission system has a runtime enforcement path and an advisory prompt path:

```text
Action request
    |
    +--> Runtime code layer: PermissionEngine -> PermissionPolicy -> AuditLogger
    |      deny-overrides-allow, hard limits, enforced decision
    |
    +--> Prompt context layer: safety text and rejection templates
           advisory only, not a Kernel runtime veto
```

Key files:

| File | Role |
|------|------|
| `policy.py` | Permission policy data and fnmatch rule matching |
| `engine.py` | Policy loading and `check()` evaluation |
| `audit.py` | JSONL audit logging with UTC timestamps |
| `prompt_generator.py` | Advisory prompt safety text |

## Layer 3: Agent Orchestration (`agents/`)

Agent workflows use a state machine with checkpoint persistence:

```text
IDLE -> PLANNING -> DISPATCH -> RUNNING -> VERIFYING
  ^                                           |
  +--------------- RETRY (max 3) ------------+
                       |
                 COMPLETED / FAILED
```

Agent roles:

| Agent | Role | Workflow stage |
|-------|------|----------------|
| alpha | Analyst | Planning and requirements analysis |
| beta | Reviewer | Independent verification and review |
| gamma | Writer | Drafting and content execution |
| delta | Orchestrator | Routing and coordination |

## Layer 4: Plugin Ecosystem (`plugins/`)

Plugins are discovered from manifests and execute through the Kernel and
permission model where applicable.

```text
plugins/
  base_plugin.py
  rag/                 RAG provider interface, local TF-IDF, mock external semantics
  harness/             audit monitoring and quality assessment
  tools/               prototype Python statistics and R survival interfaces
  standards/           medical writing checklists and citation formatting
```

### RAG Contract

RAG providers return stable structured fields such as `status`, `provider`,
`items`, `errors`, and backward-compatible aliases. Errors distinguish missing
configuration, connection failure, query timeout, and unavailable resources.
Secrets are referenced by environment variable name rather than stored in code or
repository configuration.

### Medical Statistics Boundary

Python statistics and R survival paths are prototype research-support interfaces.
They are not production-grade, clinical-grade, regulatory-grade, or medical
decision-support statistics.

### Medical Writing and Citation Boundary

CONSORT, STROBE, PRISMA, and STARD helpers identify checklist gaps. AMA and
Vancouver helpers format citation strings. They do not validate clinical
correctness, evidence quality, or regulatory compliance.

## Layer 5: LLM Provider System

LLM routing is provider-neutral. The configured `api_format` chooses the wire
protocol:

- `openai` -> OpenAI-compatible chat completions.
- `anthropic` -> Anthropic-compatible messages.
- `openrouter` -> OpenRouter gateway using OpenAI-compatible format defaults.

Provider names are flexible. Built-in defaults exist for OpenAI, Anthropic, and
OpenRouter, while custom BaseURLs support compatible gateways such as DeepSeek,
智谱 GLM, Ollama-style local endpoints, and private services.

Missing required fields produce structured validation errors, and HTTP/request
errors are sanitized before display or logging. Runtime provider selection is
explicit and persisted through `llm.provider` and `llm.last_provider`.

## Layer 6: Workspace, Paper, Experience, TUI, Experiment, and Log Paths

- Workspace ids are lowercase slugs and map to project-local paths.
- Paper import is copy-only and deduplicates by SHA-256 plus normalized DOI/PMID
  metadata when available.
- Paper enrichment requires explicit confirmation, PermissionEngine approval, and
  network/external API hard-limit checks.
- Experience learning stores user-confirmed summaries and records, not raw
  conversations.
- The Chinese TUI exposes chat, dashboard, workspace, paper, experience, tool,
  dialog history, LLM, experiment guide, and log report screens.
- Experiment guide and Log report paths store local JSON records and use redacted
  event/log output.

## Layer 7: Optional Platform Adapters (`adapters/`)

Adapters bridge SuperMedicine to assistant platforms while preserving standalone
core independence.

| Capability | Standalone Core | OpenCode Add-on | Claude Code Add-on |
|------------|----------------|-----------------|-------------------|
| CLI `init`/`status`/`run` | Supported | Can wrap/adapt metadata | Minimal adapter path |
| PermissionEngine | Supported | Used for adapter operations | Used before tool execution |
| Plugin discovery/execution | Supported | Metadata integration | Not native |
| RAG/harness/medical standards | Supported | Skill docs available | Conceptual metadata |
| Native platform tool calls | Not required | Declared mappings | `claude.invoke` only |
| Native subagent runtime | Not applicable | Not launched by adapter alone | Not implemented |

## Safety and Resource Metadata

- High-risk execution, mutation, deletion, network, and external API paths are
  permission-gated.
- Adapter failures return structured unavailable/error states rather than hiding
  missing runtimes.
- RAG providers label local versus external resources and redact common secret
  payloads.
- Workspace deletion is exact-confirmation guarded and auditable.
- Paper enrichment is explicit, permission-checked external-resource behavior.

## Repository Hygiene

Git uploads should contain only necessary project files. Do not upload excluded
engineering documentation folders such as `Docs/`, `docs/`, or `Architecture/`,
generated build artifacts, caches, runtime checkpoint directories, or local
configuration containing secrets/private endpoints.

Before release, exclude generated `build/`, `dist/`, `*.egg-info`, `__pycache__`,
`.pytest_cache`, `.pytest-tmp`, runtime data, and private configuration files.

## Quality Gate

The root quality gate reference is [README.md](README.md#local-quality-gate).
Static type checking is not a required gate unless the project intentionally adds
a dedicated mypy or pyright configuration.

## Design Principles

1. Preserve existing functional behavior unless a change is explicitly approved.
2. Enforce permissions in the runtime code layer.
3. Keep platform adapters optional and core logic platform-agnostic.
4. Add capabilities through plugin manifests and well-defined interfaces.
5. Treat medical, statistical, citation, and RAG outputs as research support that
   requires qualified human review.
