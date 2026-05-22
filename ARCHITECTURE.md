# SuperMedicine Architecture

## Overview

SuperMedicine uses a **microkernel + multi-agent orchestration** architecture. The microkernel (Kernel) integrates all core subsystems, while plugins and agents extend functionality through well-defined interfaces. A P0 dual-layer permission engine enforces security constraints at both code and prompt levels.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                             │
│                   init / status / test / run                     │
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
│  │ (UUID sessions)  │  │ Code-layer + Prompt-layer        │     │
│  └──────────────────┘  │ One-vote Veto → JSONL Audit      │     │
│                        └──────────────────────────────────┘     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼─────────┐ ┌───────▼───────┐ ┌─────────▼─────────┐
│   Agent Layer     │ │ Plugin Layer  │ │  Adapter Layer    │
│   (agents/)       │ │ (plugins/)    │ │  (adapters/)      │
└───────────────────┘ └───────────────┘ └───────────────────┘
```

## Layer 1: Microkernel (`core/`)

The Kernel is the central coordinator. All subsystems are instantiated and wired together at Kernel initialization.

### ConfigCenter (`config_center.py`)
- YAML-based configuration file reader
- Supports `SM_*` environment variable overrides
- Default path: `.supermedicine/config.yaml`

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

### PermissionEngine (`permission/engine.py`)
- **P0 priority** — initialization is mandatory
- Loads YAML policy files from `.supermedicine/policies/`
- Checks agent actions against deny-override-allow rules
- Logs all decisions to JSONL audit files with UTC timestamps

## Layer 2: Permission System (`permission/`)

The permission system enforces a **dual-layer constraint model**:

```
Action Request
     │
     ├──► Code Layer (PermissionPolicy)
     │    - fnmatch-based rule matching
     │    - deny-override-allow logic
     │    - hard enforcement
     │
     ├──► Prompt Layer (PromptGenerator)
     │    - dynamic safety prefix generation
     │    - deny template injection into agent context
     │    - context-aware soft constraints
     │
     ▼
  Both must PASS → Action allowed
  Any DENY → Action blocked + AuditLogger records
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
| Agent | Role | State Machine Stage | OpenCode Mapping |
|-------|------|---------------------|-----------------|
| α-Analyst | Research planning | PLANNING | Brain/Planner |
| β-Reviewer | Quality verification | VERIFYING | Coder/Tester |
| γ-Writer | Manuscript writing | RUNNING | Coder |
| δ-Orchestrator | Workflow coordination | DISPATCH | Brain |

## Layer 4: Plugin Ecosystem (`plugins/`)

Plugins are language-agnostic modules discovered through `plugin.yaml` manifests.

### Plugin Structure
```
plugins/
├── base_plugin.py          # BasePlugin + PluginMeta
├── rag/                    # RAG retrieval
│   ├── interface.py        #   RAGProvider, EmptyRAGProvider
│   ├── local_provider.py   #   TF-IDF based local search
│   └── plugin.yaml
├── harness/                # Quality monitoring
│   ├── monitor.py          #   AgentMonitor (audit, anomaly detection)
│   └── plugin.yaml
├── tools/
│   ├── python_stats/       # Descriptive stats, t-test, ANOVA, regression
│   └── r_survival/         # Kaplan-Meier, log-rank, Cox PH
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

## Layer 5: Platform Adapters (`adapters/`)

Adapters bridge SuperMedicine to AI coding assistant platforms.

### BaseAdapter Interface
| Method | Return Type | Purpose |
|--------|-------------|---------|
| `platform_name` | `str` | Platform identifier |
| `tool_call(tool_id, params)` | `dict` | Execute platform-native tool |
| `skill_load(skill_name)` | `str` | Load skill definition |
| `subagent_dispatch(agent_id, task)` | `dict` | Dispatch to sub-agent |

### OpenCode Adapter — Production Ready
- 8 native tool mappings: bash, read, write, edit, glob, grep, skill, task
- 6 skill files: rag-query, harness-monitor, medical-writing, medical-citation, python-stats, r-survival
- 4 agent definitions: alpha-analyst, beta-reviewer, gamma-writer, delta-orchestrator
- Full plugin.json metadata with permissions, capabilities, and tool declarations

### Claude Code Adapter — Coming Soon
- Safe degradation: all methods return "coming_soon" structured responses
- SKILL.md with complete capability reference
- Ready for full implementation when Claude Code sub-agent API matures

## Data Flow

```
User Input
    │
    ▼
CLI / Platform Adapter
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
2. **Dual-Layer Security** — Permission constraints enforced at both code and prompt levels simultaneously
3. **Checkpoint Resilience** — Long-running tasks can be interrupted and resumed without data loss
4. **Plugin Extensibility** — New capabilities added through plugin.yaml manifests, not core code changes
5. **Platform Agnostic** — Core logic is independent of any specific AI coding platform
