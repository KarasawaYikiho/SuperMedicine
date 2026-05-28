# SuperMedicine Architecture

## Overview

SuperMedicine uses a **microkernel + multi-agent orchestration** architecture for
an independent Python medical research agent framework. The microkernel (Kernel)
integrates core subsystems, workspace state, plugins, and in-process agent
concepts through well-defined interfaces. Platform adapters such as OpenCode and
Claude Code are optional add-on entrypoints around the core; they are not Kernel
initialization requirements. A P0 runtime permission engine enforces code-layer
policy checks, while prompt-layer helpers provide advisory context generation.

The latest roadmap implementation is complete through Step 13/13. Current
user-facing additions include explicit workspace management, workspace-local
paper import, experience learning, and a Chinese TUI workbench. Historical and
phase details are maintained in focused architecture documents rather than
repeated here:

- [ExecutionRoadmap.md](Architecture/ExecutionRoadmap.md) — Completed roadmap state.
- [PhaseImplementationPlan.md](Architecture/PhaseImplementationPlan.md) — Baseline compatibility map.
- [WorkspaceTuiRagGuide.md](Architecture/WorkspaceTuiRagGuide.md) — Workspace, TUI, paper, and experience workflows.
- [PlatformIntegrationAudit.md](Architecture/PlatformIntegrationAudit.md) — Standalone-core and optional-adapter audit evidence.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (Cli.py)                             │
│             init / status / test / run / LLM config              │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      Kernel (core/kernel.py)                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────┐              │
│  │ ConfigCenter │  │ EventBus │  │ PluginRegistry│              │
│  │ (YAML config)│  │(pub/sub) │  │ (YAML discover)│              │
│  └──────────────┘  └──────────┘  └───────────────┘              │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────────────────────┐     │
│  │ SessionManager   │  │ PermissionEngine (P0)            │     │
│  │ (UUID sessions)  │  │ Code-layer runtime veto          │     │
│  └──────────────────┘  │ Policy/HardLimits → JSONL Audit  │     │
│                        └──────────────────────────────────┘     │
│  ┌──────────────────┐                                          │
│  │ WorkspaceManager │ explicit workspace anchors + path safety │
│  └──────────────────┘                                          │
└──────────────────────────────┬───────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼─────────┐ ┌───────▼───────┐ ┌─────────▼─────────┐
│   Agent Layer     │ │ Plugin Layer  │ │ Optional Adapter  │
│   (agents/)       │ │ (plugins/)    │ │ Add-ons           │
└───────────────────┘ └───────────────┘ └───────────────────┘
                     ┌─────────▼─────────┐
                     │ Workspace Layer   │
                     │ papers/experience │
                     │ TUI workbench     │
                     └───────────────────┘
```

## Layer 1: Microkernel (`core/`)

The Kernel is the central coordinator. All subsystems are instantiated and wired together at Kernel initialization.

### ConfigCenter (`config_center.py`)
- YAML-based configuration file reader
- Supports `SM_*` environment variable overrides
- Default path: `.supermedicine/config.yaml`
- Exposes `get_llm_provider_config(redacted=True)` for secret-safe OpenAI /
  Anthropic provider configuration snapshots

### EventBus (`event_bus.py`)
- Publish/subscribe messaging between decoupled components
- Topic-based subscription with unsubscribe support
- Used for inter-agent communication in multi-agent workflows

### PluginRegistry (`plugin_registry.py`)
- Discovers plugins by scanning directory tree for `plugin.yaml` files
- Each plugin declares its name, version, type, and provided capabilities
- Instantiates PluginMeta objects for discovered plugins

### SessionManager (`session_manager.py`)
- UUID-based session creation and retrieval
- Key-value storage within session scope
- Supports multi-session isolation

### WorkspaceManager (`workspace.py`)
- Project-local workspace anchors use `workspaces/<id>`.
- Workspace ids are lowercase slug identifiers using letters, digits, and
  hyphens; path separators, traversal, and non-slug values are rejected.
- Workspace initialization creates workspace-local `.supermedicine/`, paper,
  notes, outputs, checkpoint/session, and local RAG directories.
- CLI workspace usage is explicit. `run`, `paper`, and `experience` paths accept
  or require `--workspace` and do not read TUI recent workspace state.
- `supermedicine tui` launches the Chinese TUI workbench; its recent selection
  is session/workspace state, not an implicit CLI default.
- Workspace-local paper and experience features share the same path-safety and
  permission model; see the workspace section below and
  [Architecture/WorkspaceTuiRagGuide.md](Architecture/WorkspaceTuiRagGuide.md).

### PermissionEngine (`permission/engine.py`)
- **P0 priority** — initialization is mandatory
- Loads YAML policy files from `.supermedicine/policies/`
- Checks agent actions against deny-override-allow rules
- Logs all decisions to JSONL audit files with UTC timestamps

## Layer 2: Permission System (`permission/`)

The permission system has a **runtime enforcement path plus an advisory prompt-context path**:

```
Action Request
     │
     ├──► Runtime Code Layer (PermissionEngine → PermissionPolicy)
     │    - fnmatch-based rule matching
     │    - deny-override-allow logic
     │    - hard_limits checks where context is supplied
     │    - hard enforcement
     │
     ├──► Prompt Context Layer (PromptGenerator)
     │    - dynamic safety prefix generation
     │    - deny template injection into agent context
     │    - context-aware soft constraints only
     │    - not currently invoked by Kernel as a runtime veto
     │
     ▼
  Runtime PermissionEngine ALLOWED → Action may proceed
  Runtime PermissionEngine DENIED → Action blocked + AuditLogger records
```

### Components
| File | Role |
|------|------|
| `policy.py` | PermissionPolicy data class, fnmatch rule matching, HardLimits |
| `engine.py` | PermissionEngine: loads policies, evaluates check() calls |
| `audit.py` | AuditLogger: JSONL file logging with UTC timestamps |
| `prompt_generator.py` | PromptGenerator: safety prefix and deny template generation |

## Layer 3: Agent Orchestration (`agents/`)

Multi-agent workflows are managed by a state machine with checkpoint persistence.

### State Machine (`state_machine.py`)
```
IDLE → PLANNING → DISPATCH → RUNNING → VERIFYING
  ↑                                    │
  └──────── RETRY (max=3) ─────────────┘
                      ↓
               COMPLETED / FAILED
```
7 states with validated transitions. Retry logic caps at 3 attempts.

### Checkpoint (`checkpoint.py`)
- Directory-based checkpoint persistence
- Each step saves state as JSON files
- `get_latest_step()` for recovery after interruption

### Orchestrator (`orchestrator.py`)
- Registers agent instances by agent_id
- Dispatches tasks to specific agents
- Returns structured execution results

### Agent Roles
| Agent | Role | State Machine Stage | Internal Workflow Role |
|-------|------|---------------------|------------------------|
| α-Analyst | Research planning | PLANNING | Strategy and requirements analysis |
| β-Reviewer | Quality verification | VERIFYING | Independent review and validation |
| γ-Writer | Manuscript writing | RUNNING | Drafting and content execution |
| δ-Orchestrator | Workflow coordination | DISPATCH | Routing and workflow coordination |

## Layer 4: Plugin Ecosystem (`plugins/`)

Plugins are language-agnostic modules discovered through `plugin.yaml` manifests.

### Plugin Structure
```
plugins/
├── base_plugin.py          # BasePlugin + PluginMeta
├── rag/                    # RAG retrieval
│   ├── interface.py        #   RAGProvider, config, stable result/errors
│   ├── local_provider.py   #   TF-IDF local search + mock external vector store
│   └── plugin.yaml
├── harness/                # Quality monitoring
│   ├── monitor.py          #   AgentMonitor (audit, anomaly detection)
│   └── plugin.yaml
├── tools/
│   ├── python_stats/       # Prototype interface/test contracts only
│   └── r_survival/         # Prototype interface/test contracts only
└── standards/
    ├── medical_writing/    # CONSORT, STROBE, PRISMA, STARD checklists
    └── medical_citation/   # AMA, Vancouver formatters
```

### Plugin Manifest (`plugin.yaml`)
```yaml
name: "plugin-name"
version: "0.1.0"
type: "tool|standard|rag|harness"
description: "..."
provides:
  - id: "capability.id"
    description: "..."
```

### RAG Provider Contract

The RAG layer supports local, PubMed, and external database/vector-index
semantics through `RAGProviderConfig` and `RAGProvider`. Query output is stable:
`status`, `provider`, `items`, `errors`, and backward-compatible
`results`/`relevance_scores`/`source_metadata` aliases. Result items expose
`id`, `title` or `source`, `score`, and `snippet` where available. Structured
errors distinguish missing configuration, connection failure, and query timeout.
Secrets are referenced by environment variable name (`api_key_env`) rather than
stored in code or repository configuration. `MockExternalVectorStoreProvider`
provides external-vector-store behavior without requiring a live service.

### LLM Provider Contract

The LLM client layer is intentionally provider-neutral and independent of
OpenCode/Claude Code:

- `core.llm_client.create_llm_client(...)` supports `openai`, `anthropic`, and
  legacy `openrouter` provider ids.
- `core.llm_providers.config.LLMProviderConfig` normalizes `api_format`,
  `base_url`/`baseURL`, `api_key`, `api_key_env`, `model`, timeout, and headers.
- OpenAI-compatible requests use bearer authorization and the chat-completions
  path by default. Anthropic-compatible requests use `x-api-key`,
  `anthropic-version`, and the messages path.
- Installer defaults are OpenAI-compatible (`https://api.openai.com/v1`,
  `OPENAI_API_KEY`, `gpt-4o-mini`) and Anthropic-compatible
  (`https://api.anthropic.com/v1`, `ANTHROPIC_API_KEY`,
  `claude-3-5-sonnet-latest`).
- Custom BaseURL values are accepted for compatible endpoints through
  `Install.py --base-url`, `SM_LLM_BASE_URL`, or local project configuration.
- Missing required provider fields produce structured validation errors;
  HTTP/request errors are sanitized with known API keys redacted.
- Runtime provider selection is stateful but explicit: `llm.provider` is the
  configured current/default provider, while `llm.last_provider` records the last
  selected provider. `LLMConfigManager` restores `last_provider` on startup when
  it still exists and otherwise falls back to the install-time default provider.
- CLI and TUI provider management share the same manager. `supermedicine llm
  switch <provider>` validates the target, persists both current and last
  provider state, and the TUI saves its current provider on exit for the same
  startup-restore path.
- Documentation, manifests, tests, and adapter files must use fake keys or
  placeholders only and must not commit real API keys.

### Workspace-Local Papers, Experience Learning, And TUI

Paper import and experience learning are workspace-aware support paths layered on
top of the same permission and path-safety model:

- Paper imports are copy-only into `workspaces/<id>/papers/originals/` and
  support `.pdf`, `.tex`, `.bib`, `.ris`, `.txt`, and `.md` source files.
- Imported paper identity is SHA-256 based; duplicate detection also uses
  normalized DOI and PMID metadata when supplied.
- Paper metadata records are stored under the workspace and keep editable fields
  for title, authors, DOI, PMID, notes, and tags.
- Online/external paper metadata enrichment requires explicit confirmation,
  PermissionEngine approval, network/external API hard-limit context, and audit
  logging before a provider fetch; ordinary import performs no silent network
  access.
- Experience learning is default-enabled but stores only user-confirmed summaries
  and experience records, never raw conversations. General method records live in
  an OS tempdir method layer and must not include project/workspace details;
  workspace records live under the selected workspace. Records can be listed,
  viewed, edited, deleted, and exported.
- The Chinese TUI workbench provides a workspace-oriented interface for recent
  workspace selection, run/paper/experience flows, and local state visibility.
  TUI recent state is not an implicit default for non-TUI CLI commands.

### Medical Statistics Boundary

`plugins/tools/python_stats` and `plugins/tools/r_survival` currently define a
minimal, deterministic interface contract for plugin execution and tests. The
implementations are prototype paths: they are not production-grade,
clinical-grade, regulatory-grade, or medical decision-support statistics. Plugin
results carry `metadata.medical_boundary`, `metadata.statistics_boundary`, and a
`metadata.contract.stage` of `prototype-interface-tests-only` to keep this
boundary explicit at runtime.

## Layer 5: Platform Adapters (`adapters/`)

Adapters bridge SuperMedicine to AI coding assistant platforms as optional
add-ons. The standalone CLI and Kernel must run without importing or requiring
OpenCode, Claude Code, `claude`, or platform configuration directories.

### BaseAdapter Interface
| Method | Return Type | Purpose |
|--------|-------------|---------|
| `platform_name` | `str` | Platform identifier |
| `tool_call(tool_id, params)` | `dict` | Execute platform-native tool |
| `skill_load(skill_name)` | `str` | Load skill definition |
| `subagent_dispatch(agent_id, task)` | `dict` | Dispatch to sub-agent |

### OpenCode Adapter — Optional Implemented Add-on Surface
- Native tool mappings for bash, read, write, edit, glob, grep, skill, and task
- Skill/agent metadata for RAG, Harness, medical writing/citation, and prototype statistics workflows
- Plugin metadata with permissions, capabilities, and tool declarations
- Execution remains subject to SuperMedicine permission checks where actions cross execution or external-resource boundaries
- `OpenCodeAdapter.subagent_dispatch(...)` does not launch a native external
  OpenCode subagent runtime by itself. When no SuperMedicine orchestrator is
  injected, it falls back to local metadata/role information.

### Claude Code Adapter — Minimal Optional Available
- Registration/discovery metadata via `ClaudeCodeAdapter.registration`
- Structured capabilities via `tool_call("claude.capabilities", ...)`
- Runtime discovery via `tool_call("claude.runtime_status", ...)`
- Contract-compatible CLI invocation path via `tool_call("claude.invoke", ...)` when a local `claude` runtime is on PATH
- All adapter actions are checked through the canonical `.supermedicine/policies/default.yaml` `PermissionEngine` path before execution
- Explicit unavailable/error states for missing runtime, timeouts, runtime errors, unsupported tools, and native sub-agent dispatch, with timeout/resource metadata and sensitive-value redaction
- Current limits: not a full Claude Code sub-agent bridge; native skill loading and native sub-agent dispatch are not claimed as supported
- OpenAI/Anthropic provider metadata follows the core LLM configuration model;
  the adapter must not embed plaintext credentials in skill docs or manifests

### Core/Add-on Capability Matrix

| Capability | Standalone Python core | OpenCode add-on | Claude Code add-on |
|------------|------------------------|-----------------|--------------------|
| Required for installation | Yes | No | No |
| Required for `Kernel` / `Cli.py run` | Yes | No | No |
| PermissionEngine checks | Core enforcement path | Used for high-risk adapter actions | Used before adapter actions |
| Plugin discovery/execution | Native through Kernel | Adapter metadata/context only | Not native plugin runtime |
| Platform tools | Not required | Declared adapter mappings | Minimal `claude.*` tools |
| Native platform subagents | Not applicable | Not implemented without injected orchestrator | Not implemented |
| Native platform skill loading | Not applicable | Skill docs available to OpenCode setup | Not implemented |
| LLM provider config | OpenAI/Anthropic via config/env/installer | Metadata only, from core config sources | Metadata only, from core config sources |

### Standalone And CLI Execution

The CLI initializes the Kernel for `init`, `status`, `test`, and `run` paths. The
`run` command uses the real component stack rather than a placeholder-only path,
including plugin discovery and permission-gated execution where applicable.

## Safety And Resource Metadata

High-risk calls use a minimal, dependency-free safety model:

- Adapter execution is permission-checked and returns structured
  `error_code`/`retryable`/`metadata.resource` values for timeout,
  unavailable, and runtime failures.
- RAG providers identify local vs external resources, expose timeout and
  connection/config/resource failures as structured errors, and redact common
  secret-like payloads while preserving environment-variable secret references.
- Kernel plugin execution is the production permission entrypoint. Results carry
  `metadata.resource` and `metadata.security` so callers can audit whether a
  plugin path was permission-gated.
- The default policy explicitly declares mock external RAG access and keeps
  general network/external API use disabled for standard alpha/gamma roles.
- Workspace deletion is a hard delete guarded by exact confirmation,
  destructive-path validation, PermissionEngine authorization, and audit logs.
- Paper enrichment treats network and external API use as hard-limit checked
  external-resource behavior and does not run without explicit confirmation.
- Experience learning rejects raw conversations and separates general method
  storage from workspace-local project details.

## Medical Writing And Citation Constraints

Medical writing support provides reporting-checklist and citation-formatting
constraints only. CONSORT, STROBE, PRISMA, and STARD helpers can identify missing
checklist items, and AMA/Vancouver helpers format citation strings. These modules
do not validate clinical correctness, evidence quality, or regulatory compliance;
all manuscript content and references require qualified human review.

## Repository Hygiene

Git uploads should contain only necessary project files. Do not include `Docs/`,
`Superpower`, `superpower`, external skill packages, or non-essential generated
documentation artifacts in this repository. Before release upload, also exclude
generated `build/`, `dist/`, `*.egg-info`, `__pycache__`, `.pytest_cache`,
`.pytest-tmp`, runtime checkpoint directories, and any local configuration that
contains secrets or private endpoints.

Phase documentation/help work does not create tags, releases, package publishes,
paper uploads, or external artifact uploads.

## Planning And Push Gate Rule

Plan-stage work does not need strict project-standard verification. Optimization
and standardization are required before Push/finalization, not during early
planning. This is only a planning-overhead rule: before any Push, finalization,
tag, release, publish, or upload, the project-approved final verification,
quality gate, repository hygiene review, and required optimization/standardization
must still be completed.

## Quality Gate

The minimal CI/local release gate is intentionally dependency-light and is kept
canonical in [README.md](README.md#local-quality-gate).

Static type checking is not a required gate unless the project intentionally adds
a dedicated mypy or pyright configuration.

## Data Flow

```
User Input
    │
    ▼
CLI / Optional Platform Adapter
    │
    ▼
Kernel (init)
    ├── ConfigCenter.load()        — read configuration
    ├── PluginRegistry.discover()  — find available plugins
    ├── PermissionEngine (active)  — security layer online
    └── SessionManager.create()    — new workflow session
    │
    ▼
Orchestrator.dispatch(task)
    │
    ├──► α-Analyst.execute()
    │       └── StateMachine: PLANNING → DISPATCH
    │
    ├──► γ-Writer.execute()
    │       └── StateMachine: RUNNING
    │
    └──► β-Reviewer.execute()
            └── StateMachine: VERIFYING
                    ├── PASS → Checkpoint.save() → COMPLETED
                    └── FAIL → RETRY (max 3) or FAILED
```

## Design Principles

1. **Functional Preservation** — No existing function behavior is ever changed without explicit approval
2. **Permission Safety** — Runtime permission constraints are enforced by the code-layer PermissionEngine; PromptGenerator provides advisory agent-context constraints and is not a Kernel veto layer
3. **Checkpoint Resilience** — Long-running tasks can be interrupted and resumed without data loss
4. **Plugin Extensibility** — New capabilities added through plugin.yaml manifests, not core code changes
5. **Platform Agnostic** — Core logic is independent of any specific AI coding platform
