# Architecture Guide

SuperMedicine is organized around a small Python core and optional surfaces
around it. The default supported path is the standalone CLI/Kernel runtime.

## Runtime Shape

```text
CLI / TUI / Web / optional adapters
        |
        v
      Kernel
        |
        +-- configuration
        +-- event bus
        +-- plugin registry
        +-- permission engine
        +-- sessions and checkpoints
        +-- LLM provider manager
```

The Kernel coordinates shared services. Domain behavior should live in
workspaces, plugins, permission modules, installer modules, or UI-specific
surfaces rather than being embedded in the CLI facade.

## Main Directories

| Path | Responsibility |
| --- | --- |
| `cli/` | Parser and command modules. |
| `core/` | Shared runtime services, Kernel, workspace, TUI, Web, LLM, logging. |
| `permission/` | Runtime permission policy, engine, and audit logging. |
| `plugins/` | Plugin manifests and research tools. |
| `agents/` | Internal orchestration roles and state machine. |
| `adapters/` | Optional OpenCode/Claude Code metadata and adapter surfaces. |
| `installer/` | Installer and release extraction logic. |
| `tests/` | Regression and repository hygiene checks. |

## Permission Boundary

Runtime access control belongs in `permission/` and `PermissionEngine.check()`.
Prompt text and adapter metadata may explain policy, but they are not the
enforcement boundary.

Modes:

- `conservative`: default, project-local first, external operations restricted.
- `full`: explicit acknowledgement, current OS user permissions only.

## Plugin Boundary

Plugins are discovered from manifests and called through the runtime. A plugin
should return structured success/error data and should not bypass permission
checks for file, process, or network-sensitive work.

## Workspace Boundary

Workspace ids resolve to `workspaces/<id>`. CLI commands that operate on
workspace data require explicit `--workspace`.

## Adapter Boundary

OpenCode and Claude Code support is optional. Adapter files must not claim native
platform runtime behavior unless that behavior is implemented and tested.

## Release Boundary

Packaging and installer behavior is product behavior. Changes to `setup.py`,
`.github/workflows/ci.yml`, `scripts/ci/`, or `installer/` should be tested with
release-focused tests.

## References

- [Full architecture reference](../architecture/ARCHITECTURE.md)
- [Function map](../architecture/FUNCTION_MAP.md)
- [Repository map](../maintainers/repository-map.md)
- [Quality gates](../maintainers/quality-gates.md)
