# Workspace, TUI, Paper Import, And Experience Guide

This guide documents the user-facing workspace/TUI/RAG-adjacent workflows added
for the current phase. It is documentation only: no tag, release, publish,
package upload, paper upload, or external artifact upload is part of this work.

For installation and command setup, see [../INSTALL.md](../INSTALL.md). For the
broader architecture model, see [../ARCHITECTURE.md](../ARCHITECTURE.md). This
guide focuses on workspace-local operation and avoids repeating global setup
details.

## Workspaces

SuperMedicine stores project workspaces under `workspaces/<id>`. The workspace
id is a slug: lowercase letters, digits, and hyphens only. It cannot contain path
separators, traversal segments, leading/trailing hyphens, or arbitrary Unicode.

```bash
supermedicine workspace init --workspace hypertension-review
supermedicine workspace list
supermedicine workspace show --workspace hypertension-review
```

Workspace initialization creates workspace-local directories for configuration,
sessions, checkpoints, local RAG data, papers, notes, and outputs. CLI commands
do not silently infer a workspace from the TUI. Use `--workspace <id>` whenever a
command operates on workspace-local state.

## CLI And Chinese TUI

`supermedicine tui` launches the Chinese terminal UI workbench. TUI recent
selection is saved as workspace/session state for the TUI experience only; it is
not a CLI default. CLI paths such as `run`, `paper`, and `experience` require or
accept an explicit `--workspace` argument so automation is reproducible.

```bash
supermedicine run "query local context" --workspace hypertension-review
supermedicine tui
```

### Current TUI Structure Audit And Execution Boundary

This audit records the current Textual TUI structure before follow-up UI work. It
is documentation-only: no TUI source, style, controller, test, CLI, permission, or
runtime behavior is changed by this section.

Current implementation map:

- `core/tui/app.py` is the main TUI entrypoint. `SuperMedicineTUI` builds a
  persistent `Header`, left `ListView` sidebar, `#main-area`, bottom input bar,
  three-column status bar, and `Footer`. `launch_tui()` supports a non-interactive
  `--dry-run` status path for tests and CLI smoke checks.
- Sidebar navigation uses `NavItem` entries and numeric bindings `1` through `8`
  for `chat`, `dashboard`, `workspace`, `paper`, `experience`, `tool`, `dialog`,
  and `llm`. `action_switch_view()` swaps pre-mounted views by toggling
  `display`, updates `#view-title`, and synchronizes the sidebar index.
- The status bar is updated from workspace count, plugin count, LLM readiness,
  UTC time, and package version. LLM readiness uses `ConfigCenter` and
  `LLMConfigManager`; exit state is saved from `on_unmount()`.
- The input bar is global, not screen-local. `on_input_submitted()` clears
  `#prompt-input`, appends the user message to `ChatView`, and starts
  `_run_kernel_task()` with `run_worker(..., exclusive=True)` so Kernel execution
  does not block the UI thread.
- `core/tui/app.tcss` defines the high-level layout, fixed-width sidebar, title
  row, scrollable content pane, input bar, status bar, table sizing, LLM hints,
  button classes, section titles, and maximized-view height. Styling is currently
  selector/id based and intentionally compact.
- `core/tui/i18n.py` centralizes Chinese labels for app title, navigation,
  dashboard, workspace, paper, experience, tool, dialog, LLM, common actions,
  status labels, and help text through `LABELS` plus `t(key)` fallback.
- `core/tui/screens/chat_view.py` is the chat view: a `RichLog` backed message
  display with system, user, assistant, error, and clear helpers.
- `core/tui/screens/dashboard.py` is a read-only status table for initialization,
  workspace count, plugin count, module count, and version.
- `core/tui/screens/workspace_screen.py` is the interactive workspace view. It
  delegates create/select/delete/list work to `WorkspaceScreenController` in
  `core/tui/screens/workspaces.py`, including recent TUI state and permission-
  guarded hard delete.
- `core/tui/screens/paper_screen.py` is the paper view. It delegates import,
  list, show/edit controller behavior, and explicit enrichment to
  `PaperScreenController` in `core/tui/screens/papers.py`.
- `core/tui/screens/experience_screen.py` is the experience-learning view. It
  delegates suggest, confirm, list, edit, delete, and export operations to
  `ExperienceScreenController` in `core/tui/screens/experience.py`.
- `core/tui/screens/tool_screen.py` is the workspace-local tool view. It currently
  manages the workspace tool folder UI directly, including local tool directory
  initialization, simple `tool.json` creation, listing, and path display for run.
- `core/tui/screens/dialog_screen.py` is a read-only dialog-history view backed by
  `DialogHistoryStore`; history remains summary/event oriented and not raw
  conversation storage.
- `core/tui/screens/llm_screen.py` contains both `LLMScreenController` and
  `LLMView` for redacted provider listing, provider add/update, switching,
  readiness display, password-style key entry, and exit-state persistence.
- Backward-compatible aliases are present for several views/controllers, and
  `core/tui/screens/__init__.py` exports the test-friendly controller surface.

Existing TUI test boundary:

- `tests/test_tui_entrypoint.py` covers CLI help registration, Chinese labels,
  dry-run readiness, `CLI().tui(dry_run=True)`, and secret-safe LLM startup
  restore.
- `tests/test_tui_state.py` covers workspace/session-only recent TUI selection
  and separation from CLI workspace defaults and LLM startup restore.
- `tests/test_tui_workspace_screens.py` covers workspace controller create,
  select, recent state, exact delete confirmation, policy use, hard delete, and
  audit-log creation.
- `tests/test_tui_paper_screens.py` covers copy-only paper import, metadata list
  output, metadata edit, and explicit enrichment confirmation.
- `tests/test_tui_experience_screens.py` covers suggestion without persistence,
  confirmation requirement, list/edit/export, and exact delete confirmation.
- `tests/test_tui_dialog_history.py` covers summary-event dialog history storage
  and rejection of raw conversation fields.
- `tests/test_tui_permissions.py` covers permission/confirmation preparation for
  high-risk TUI tool actions.
- `tests/test_tui_llm_screen.py` covers redacted provider add/switch/list,
  startup restore of the last provider, and secret-safe controller errors.

### OpenCode-aligned TUI Experience Principles For This Round

This round uses `anomalyco/opencode` only as an experience reference for modern
TUI/CLI interaction patterns. The transferable target is not code reuse and not a
runtime integration: SuperMedicine must remain a standalone Python/Textual core,
with OpenCode kept as an optional adapter surface only.

Migrated principles for the SuperMedicine Textual workbench:

- **Command-style interaction with immediate feedback** — every submitted prompt
  or screen action should visibly acknowledge receipt, queued/running/completed
  state, or a safe no-op reason instead of leaving the terminal silent.
- **Clear focus state** — the active navigation item, focused widget, maximized
  region, and input target should be visually distinct enough that keyboard users
  can predict where the next key press will land.
- **Compact, high-information layout** — preserve the current dense sidebar,
  title row, main pane, input bar, status bar, and footer structure; prefer short
  labels, tables, badges, and concise hints over verbose panels.
- **Visible session and context state** — surface current workspace, LLM readiness,
  provider, session/recent-selection status, plugin count, and task activity in
  stable places so users do not need to infer hidden context.
- **Discoverable shortcuts** — keep numeric navigation, `?`, `f`, `Esc`, and `q`
  discoverable through footer/help copy, and make screen-local actions visible in
  nearby labels or button text.
- **Actionable errors** — error messages should identify what failed, what the
  user can do next, and whether a permission, configuration, missing dependency,
  workspace, or external-resource boundary caused the failure.
- **Explicit task-running state** — long-running Kernel or controller work should
  show a running/busy/complete/failure state without blocking the Textual event
  loop or implying that multiple conflicting Kernel jobs are active.
- **Input/output hierarchy clarity** — the global input bar is for chat/run-style
  prompts; screen-local forms and buttons should remain visually below the current
  view title and above result logs/tables, so commands, forms, and output are not
  confused.

Round optimization checklist derived from those principles:

- Documentation target for this step: record the above principles and make the
  next landing pass explicit; do not add OpenCode packages, imports, subprocesses,
  configuration requirements, or runtime assumptions.
- Copy/style target: improve Chinese labels and low-risk TCSS cues only where
  they clarify focus, status, shortcuts, task state, or error recovery.
- Status target: prefer small view-level status text updates for current
  workspace, provider/readiness, pending/running operation, and last result over
  larger layout rewrites.
- Error target: normalize user-facing TUI errors toward `原因 + 下一步` phrasing
  while preserving secret redaction, permission gates, and existing controller
  behavior.
- Help target: ensure shortcut discoverability remains available from the footer
  and help path; add only compact hints that do not crowd the main pane.
- Boundary target: keep CLI/TUI workspace semantics unchanged, keep paper
  enrichment explicit, keep dialog history summary-only, keep destructive actions
  confirmation-gated, and keep the standalone Python core independent of
  OpenCode/Claude Code runtimes.
- Deferral target: postpone any router/screen-stack replacement, per-screen input
  architecture, async orchestration redesign, persisted format changes, or widget
  replacement until a dedicated implementation plan and focused tests exist.

Execution checklist for the next TUI iteration:

- In-scope for a small landing pass: documentation updates; Chinese copy cleanup
  in `i18n.py`; low-risk style refinements in `app.tcss`; small view-level status
  text improvements; controller-surface tests for any changed workspace, paper,
  experience, dialog, permissions, or LLM behavior; and minimal TUI dry-run or
  controller synchronization that preserves existing CLI/workspace boundaries.
- In-scope only with focused tests and review: adding view-local refresh behavior,
  improving empty-state messages, exposing existing controller actions that are
  already implemented but not surfaced in a view, and aligning tool-screen UI with
  the documented workspace tool manifest model.
- Out of scope for a small landing pass and better handled as a later refactor:
  replacing the global input model with per-screen command forms, introducing a
  router/screen-stack architecture, moving all views to a common base class,
  redesigning async task orchestration beyond the current single Kernel worker,
  changing CLI/TUI workspace-default semantics, changing permission/audit policy,
  changing persisted file formats, replacing Textual widgets wholesale, or
  restructuring `core/tui/screens/**` imports and aliases.
- Required preservation boundaries: do not leak LLM secrets, do not store raw
  conversations in dialog history, do not make paper enrichment implicit, do not
  infer CLI workspaces from TUI state, and keep destructive workspace/experience
  operations confirmation-gated.

## Hard Delete Semantics

Workspace deletion is destructive and irreversible from the CLI perspective:

```bash
supermedicine workspace delete --workspace hypertension-review --confirm hypertension-review
```

The confirmation value must exactly match the workspace id. The delete path must
stay inside the project root, pass destructive-path validation, receive
PermissionEngine approval for `workspace.delete`, and emit audit records. A
failed confirmation, missing policy, permission denial, or successful deletion is
recorded for review.

## Workspace-local Python/R Tools

Workspaces can carry reusable analysis tool folders without changing global
plugin/API semantics. The layout is explicit and workspace-local:

- `workspaces/<id>/tools/python/<tool-id>/...`
- `workspaces/<id>/tools/r/<tool-id>/...`

Tool ids use the same safe slug style as workspace ids. Supported languages are
`python` and `r`. Each tool folder contains a `tool.yaml` manifest with `id`,
`language`, `name`, `description`, `entrypoint`, `dependencies`, `inputs`,
`outputs`, and `version` fields.

```bash
supermedicine tool init --workspace hypertension-review
supermedicine tool add --workspace hypertension-review --language python --tool heatmap
supermedicine tool add --workspace hypertension-review --language r --tool umap
supermedicine tool list --workspace hypertension-review
supermedicine tool show --workspace hypertension-review --language python --tool heatmap
supermedicine tool run --workspace hypertension-review --language python --tool heatmap --dry-run --input data/matrix.csv --output outputs/heatmap.png
```

Built-in templates are available for Python heatmap, Python UMAP, R heatmap, and
R UMAP. They are scaffolds: heavyweight visualization dependencies such as
`matplotlib`, `seaborn`, `umap-learn`, `ggplot2`, `pheatmap`, and R `umap` remain
optional and are reported by the runner scripts with friendly messages instead
of becoming global SuperMedicine dependencies.

`tool run` currently prepares a guarded command foundation rather than executing
workspace scripts directly. Preparation validates the workspace, language, tool
slug, manifest, entrypoint, and optional input/output paths; paths must remain
inside the selected workspace/tool folder as appropriate. The operation is
checked through PermissionEngine using `tool.run` and audit events are written
for allowed or denied decisions. CLI tool commands require explicit
`--workspace` and do not read TUI recent selection.

## Paper Import And Metadata

Paper import is copy-only. SuperMedicine reads the local source file and copies
it into the selected workspace; it does not move the source, publish it, upload
it, or call the network during normal import.

Supported formats are common local research-paper formats:

- PDF (`.pdf`)
- TeX (`.tex`)
- BibTeX (`.bib`)
- RIS (`.ris`)
- text (`.txt`)
- Markdown (`.md`)

Imports compute SHA-256 for the stored original. Duplicate detection uses the
SHA-256 and, when supplied, normalized DOI and PMID metadata. Editable metadata
fields include title, authors, DOI, PMID, notes, and tags.

```bash
supermedicine paper import ./trial.pdf --workspace hypertension-review --doi 10.1000/example
supermedicine paper list --workspace hypertension-review
supermedicine paper edit <paper-id> --workspace hypertension-review --title "Updated title"
```

## Online Metadata Enrichment

Online or external paper metadata enrichment is opt-in only. It requires:

1. explicit user confirmation with `--confirm-enrich`,
2. PermissionEngine approval for the enrichment action,
3. network and external API hard-limit context checks, and
4. audit logging before and after the provider decision.

No paper import performs silent network access.

```bash
supermedicine paper enrich <paper-id> --workspace hypertension-review --confirm-enrich
```

## Experience Learning

Experience learning is enabled by default, but it stores only user-confirmed
summaries/experience records. Raw conversations, transcripts, or message logs
are rejected.

Two storage scopes are used:

- **general** — reusable method-level experience in an OS tempdir method layer;
  this scope must not include workspace ids, paper paths, paper ids, or other
  project-specific details.
- **workspace** — project-local details stored under the selected workspace.

Users can suggest a scope without writing, explicitly add confirmed records,
list/view records, edit/delete records, and export visible records as JSON or
Markdown.

```bash
supermedicine experience suggest --workspace hypertension-review --summary "Use concise extraction prompts"
supermedicine experience add --workspace hypertension-review --scope general --title "Prompt style" --summary "Use concise extraction prompts" --confirm
supermedicine experience list --workspace hypertension-review --include-general
supermedicine experience export --workspace hypertension-review --format md --include-general
```

## Safety, Privacy, And Medical Boundary

SuperMedicine is for medical research assistance, not clinical decision support.
RAG results, paper metadata, writing checklist output, citation formatting, and
prototype statistics outputs require qualified expert review. Do not treat any
output as diagnosis, treatment, regulatory approval, or clinical advice.

Security-sensitive behavior remains permission-gated. Keep secrets in
environment variables or local private configuration, avoid committing sensitive
audit logs or private endpoints, and review every external-resource permission
before enabling network/API access.
