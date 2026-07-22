# Architecture

SuperMedicine is a local-first Python framework for medical research assistance.
The default supported product is the standalone Python runtime: CLI, Kernel,
permission engine, plugins, workspace state, installer, and TUI launcher.

Current release label: **Beta0.4.2**. Python package fallback version:
**0.4.2b0**.

## System Shape

```text
CLI / OpenTUI bridge / Web + Desktop
                 |
                 v
        ApplicationFacade
                 |
                 v
      shared services / Kernel
        |
        +-- config
        +-- event bus
        +-- plugin registry
        +-- permission engine
        +-- sessions and checkpoints
        +-- LLM provider routing
```

The Kernel is a wiring point. Domain behavior belongs in focused modules:
workspaces, paper import, experience records, plugins, permissions, installer
logic, or UI-specific controllers.

The mandatory execution order is runtime validation, Harness begin, task
classification, local-first RAG where required, permission checks, single or
multi-agent execution, and exactly one Harness finalize. `RuntimeCapabilities`
is the shared health snapshot consumed by CLI, TUI, and Web. Harness/RAG
manifests are declarations; `validate_required_plugins()` is the code-level
fail-closed enforcement. Multi-agent mode defaults to single and cannot create a
parallel top-level lifecycle.

## Core Boundaries

| Area | Owner | Rule |
| --- | --- | --- |
| CLI | `cli/`, `cli_entry.py` | Parser and facade should delegate feature logic. |
| Runtime | `core/` | Shared services used by CLI, TUI, Web, and tests. |
| Permissions | `permission/` | Runtime enforcement happens here, not in prompt text. |
| Plugins | `plugins/` | Capabilities are manifest-discovered and action-based. |
| Workspaces | `core/workspace*.py`, `core/paper_import/`, `core/experience.py` | Workspace ids are explicit and project-local. |
| TUI | `core/tui/` | Python launcher plus OpenTUI JavaScript runtime. |
| Web | `core/web/` | Optional FastAPI/browser surface. |
| Installer | `installer/`, `install*.py`, `uninstall*.py` | Release-critical behavior. |
| Adapters | `adapters/` | Optional platform metadata and bridge code. |

## Permission Model

`PermissionEngine.check()` is the enforcement boundary. Prompt generators and
adapter instructions may describe policy, but they do not replace runtime
checks.

Modes:

- `conservative`: default. Project-local first, external write/delete/execute
  restricted.
- `full`: explicit acknowledgement. Uses only current OS user/process
  permissions; it does not bypass UAC, ACLs, or administrator requirements.

Audit records are local runtime data under `.supermedicine/policies/audit.jsonl`.

## Plugin Model

Plugins live under `plugins/`, declare manifests, and expose action-oriented
execution. A plugin should return structured success or error payloads and should
not bypass permission checks for sensitive operations.

Current plugin groups include RAG, harness checks, medical writing standards,
medical citation formatting, experiment helpers, Python/R tools, and figure
utilities.

## Workspace Model

Workspace-scoped commands require explicit `--workspace`. Workspace ids resolve
under `workspaces/<id>`. Paper import is copy-only. Experience records store
confirmed summaries rather than raw conversations.

## LLM Provider Model

Provider configuration is local and provider-neutral. Records include provider
name, API format, Base URL, model, and key source. Built-in API formats are
`openai`, `anthropic`, and `openrouter`; compatible custom endpoints can be
configured with explicit Base URLs.

## TUI Model

The TUI has two implementation layers and one production renderer:

- Python launcher and authenticated NDJSON bridge in `core/tui/`
- Bun/OpenTUI renderer in `core/tui/opentui/`

The JS runtime depends on `@opentui/core@0.4.3`. Textual is not a runtime or
fallback dependency. Mouse, keyboard, focus, scrolling, responsive layout,
stream cancellation, and terminal cleanup are tested against the real renderer.

## Adapter Model

OpenCode and Claude Code adapters are optional. They must return explicit
degraded/unavailable states when platform runtime features are missing. Adapter
docs and manifests must not contain credentials or claim unimplemented native
runtime behavior.

## Release Model

Release archives keep installer entrypoints, `installer/`, runtime packages,
OpenTUI npm manifests, documentation, and executables together. Release package
tests protect `SuperMedicineInstaller.exe`, `dist/SuperMedicine.exe`,
`SuperMedicineGUI.exe`, the frozen GUI self-test, and the OpenTUI smoke path.

## Repository Hygiene

Tracked content should be source, tests, CI, package metadata, docs, policies,
and small assets. Generated output, local logs, runtime state, caches, secrets,
desktop executables, and archive notes belong outside Git.

`docs/archive/` is intentionally ignored. Local historical material may live in
ignored `Temp/`.

## Related Docs

- [Function map](FUNCTION_MAP.md)
- [Maintainer guide](../maintainers/README.md)
- [Installation guide](../guides/INSTALL.md)
- [Security policy](../../SECURITY.md)
