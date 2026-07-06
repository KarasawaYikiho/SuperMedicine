# SuperMedicine Refactoring Plan (Rebuild-2)

> **Purpose**: Decompose oversized files into focused, single-responsibility modules while preserving all existing functionality and public APIs.

---

## 1. File Analysis

### 1.1 `Cli.py` — 2662 lines, ~40 methods

**Current responsibilities** (all in one file):
| Group | Lines | Methods/Functions | Responsibility |
|-------|-------|-------------------|----------------|
| Logging infrastructure | 25–78 | `_configure_stdio_errors`, `_RedactingFormatter`, `_configure_cli_logging`, `_log_json` | CLI logging setup & redaction |
| CLI class: core lifecycle | 109–274 | `init`, `status`, `test`, `run` | Project init, status display, test runner, task execution |
| CLI class: workspace ops | 276–376 | `workspace_init`, `workspace_list`, `workspace_show`, `workspace_delete` | Workspace CRUD |
| CLI class: tool ops | 378–485 | `tool_init`, `tool_list`, `tool_scan`, `tool_add`, `tool_show`, `tool_run` | Workspace tool management |
| CLI class: LLM ops | 487–567 | `llm_add`, `llm_list`, `llm_show`, `llm_switch` | LLM provider management |
| CLI class: permission ops | 569–637 | `permission_status`, `permission_set_mode`, `permission_authorize`, `permission_revoke` | File access permission |
| CLI class: self-evolution | 639–688 | `self_evolve` | Self-evolution artifact generation |
| CLI class: diagnostics | 690–725 | `diagnose` | System diagnostics |
| CLI class: paper ops | 727–829 | `paper_import`, `paper_list`, `paper_show`, `paper_edit`, `paper_enrich` | Paper metadata management |
| CLI class: experience ops | 831–974 | `experience_suggest`, `experience_add`, `experience_list`, `experience_view`, `experience_edit`, `experience_delete`, `experience_export` | Experience record management |
| CLI class: experiment ops | 976–1220 | `experiment_start`, `experiment_list`, `experiment_context`, `experiment_add_config`, `experiment_show`, `experiment_submit` | Experiment guide sessions |
| CLI class: log ops | 1222–1331 | `log_write`, `log_list`, `log_show`, `log_location`, `log_follow` | Log report operations |
| CLI class: TUI | 1333–1338 | `tui` | TUI launcher |
| Module-level helpers | 1340–1694 | 20+ free functions | Conversions, parsing, JSON loading, permission formatting, LLM header parsing |
| Argument parser | 1696–2658 | `main()` | argparse setup + command dispatch |

**Key observations**:
- The `CLI` class is a god object — every domain registers a method here.
- Each method follows the same pattern: lazy-import service → call service → `_log_json(result)` → return result.
- The `main()` function is 960 lines of pure argparse setup.
- Module-level helper functions are domain-specific but live at module level.

---

### 1.2 `core/kernel.py` — 857 lines

**Current responsibilities**:
| Group | Lines | Methods | Responsibility |
|-------|-------|---------|----------------|
| System prompt & constants | 27–61 | — | `MEDICAL_BOUNDARY`, `SUPERMEDICINE_SYSTEM_PROMPT` |
| Kernel.__init__ | 67–120 | `__init__`, `_ensure_canonical_default_policy` | Wiring all core services |
| Properties | 121–153 | 7 `@property` | Read-only accessors |
| Checkpoint | 155–186 | `_checkpoint_task` | Save task checkpoint |
| `execute_task` | 188–446 | `execute_task` | **260 lines** — permission check, plugin dispatch, result shaping |
| LLM runtime context | 448–481 | `_llm_runtime_context` | Secret-safe LLM state |
| `_execute_llm_chat` | 483–744 | `_execute_llm_chat` | **260 lines** — streaming LLM chat with error handling |
| LLM messages | 746–793 | `_llm_chat_messages` | Build message array |
| Workspace tool context | 795–808 | `_workspace_tool_runtime_context` | Tool context for LLM |
| Plugin selection | 810–857 | `_select_plugin_action` | Keyword → plugin/action mapping |

**Key observations**:
- `execute_task` and `_execute_llm_chat` are each ~260 lines — should be decomposed.
- `_select_plugin_action` is a pure mapping function that doesn't need kernel state.
- System prompt is a large constant that inflates the file.

---

### 1.3 `core/log_report.py` — 857 lines

**Current responsibilities**:
| Group | Lines | Items | Responsibility |
|-------|-------|-------|----------------|
| Severity helpers | 20–110 | 4 functions + constants | Severity normalization & detection |
| LogReport dataclass | 117–143 | `LogReport` | Single log record |
| LogStorageLocations | 146–181 | `LogStorageLocations`, `resolve_log_storage_locations` | Storage path resolution |
| LogReportStore | 184–766 | 1 class, ~30 methods | **580 lines** — JSON file-backed log store |
| LogReportLoggingHandler | 768–787 | 1 class | Python logging integration |
| TUI log helpers | 790–857 | 3 functions | TUI log routing |

**Key observations**:
- `LogReportStore` is 580 lines — the internal query/statistics logic could be extracted.
- Severity helpers are pure functions, already well-scoped.
- TUI-specific log routing is mixed into the log report module.

---

### 1.4 `core/workspace_tools.py` — 1043 lines

**Current responsibilities**:
| Group | Lines | Items | Responsibility |
|-------|-------|-------|----------------|
| Constants & exceptions | 30–67 | 5 exception classes, constants | Type definitions |
| Manifest helpers | 68–153 | `_read_limited_text`, `_safe_load_manifest`, `TOOL_AUTHORING_SPEC`, `build_tool_authoring_llm_context` | YAML loading & LLM context |
| `ToolManifest` | 174–275 | 1 dataclass | Manifest schema + validation |
| `ToolInvocationPlan` | 278–311 | 1 dataclass | Invocation plan |
| `ToolImportCandidate` | 313–369 | 1 dataclass | Scan result |
| Templates | 371–525 | `_manifest_text`, `PYTHON_RUNNER`, `R_RUNNER`, `BUILTIN_TEMPLATES` | Built-in tool templates |
| `WorkspaceToolService` | 534–1043 | 1 class, ~20 methods | **510 lines** — CRUD + scan + import |

**Key observations**:
- Three dataclasses + exceptions + templates + service all in one file.
- Templates are large string constants (~150 lines).
- The service's `_candidate_from_source` method is ~110 lines of complex parsing logic.

---

### 1.5 `core/tui/app.py` — 1464 lines

**Current responsibilities**:
| Group | Lines | Items | Responsibility |
|-------|-------|-------|----------------|
| Stream capture | 36–116 | 3 classes + context manager | stdout/stderr routing to log storage |
| Kernel output filtering | 118–222 | 2 functions + constants | Strip internal telemetry |
| Status styling | 224–248 | `apply_status_style` | CSS class application |
| Data classes | 251–299 | 4 dataclasses | Status/nav/shell types |
| Nav widgets | 301–324 | `NavItem`, `MenuOption`, `MenuButton` | Sidebar navigation |
| Menu screens | 335–419 | `ViewSelectMenuScreen`, `MainMenuScreen` | Modal menus |
| PromptInput | 422–553 | `PromptInput` | **130 lines** — terminal control filtering input |
| SuperMedicineTUI | 555–1293 | 1 class, ~40 methods | **740 lines** — main app |
| launch_tui + helpers | 1295–1464 | 4 functions | Entry point + diagnostics |

**Key observations**:
- Stream capture and kernel output filtering are reusable utilities mixed into app.
- `PromptInput` is a self-contained 130-line widget that should be its own module.
- `SuperMedicineTUI` has clear sub-responsibilities: navigation, status bar, chat processing, view management.

---

## 2. Extraction Plan

### 2.1 `Cli.py` → `cli/` package

**Target structure**:
```
cli/
├── __init__.py          # Re-exports CLI class and main()
├── logging_setup.py     # _configure_stdio_errors, _RedactingFormatter, _configure_cli_logging, _log_json
├── helpers.py           # Module-level helper functions (parsing, conversion, formatting)
├── commands/
│   ├── __init__.py
│   ├── workspace.py     # workspace_init, workspace_list, workspace_show, workspace_delete
│   ├── tool.py          # tool_init, tool_list, tool_scan, tool_add, tool_show, tool_run
│   ├── llm.py           # llm_add, llm_list, llm_show, llm_switch
│   ├── permission.py    # permission_status, permission_set_mode, permission_authorize, permission_revoke
│   ├── paper.py         # paper_import, paper_list, paper_show, paper_edit, paper_enrich
│   ├── experience.py    # experience_suggest, experience_add, experience_list, experience_view, experience_edit, experience_delete, experience_export
│   ├── experiment.py    # experiment_start, experiment_list, experiment_context, experiment_add_config, experiment_show, experiment_submit
│   ├── log.py           # log_write, log_list, log_show, log_location, log_follow
│   └── self_evolve.py   # self_evolve, _self_evolution_cli_result
├── cli_core.py          # CLI class (thin orchestrator delegating to commands/*)
└── parser.py            # main() argparse setup + dispatch
```

**What moves where**:
| Current location | Target file | Notes |
|------------------|-------------|-------|
| Lines 25–78 (logging) | `cli/logging_setup.py` | Pure utility, no dependencies |
| Lines 109–274 (init/status/test/run) | `cli/cli_core.py` | Core lifecycle stays in CLI class |
| Lines 276–376 (workspace) | `cli/commands/workspace.py` | Extract as functions taking CLI context |
| Lines 378–485 (tool) | `cli/commands/tool.py` | Same pattern |
| Lines 487–567 (LLM) | `cli/commands/llm.py` | Same pattern |
| Lines 569–637 (permission) | `cli/commands/permission.py` | Same pattern |
| Lines 639–688 (self-evolve) | `cli/commands/self_evolve.py` | Same pattern |
| Lines 727–829 (paper) | `cli/commands/paper.py` | Same pattern |
| Lines 831–974 (experience) | `cli/commands/experience.py` | Same pattern |
| Lines 976–1220 (experiment) | `cli/commands/experiment.py` | Same pattern |
| Lines 1222–1331 (log) | `cli/commands/log.py` | Same pattern |
| Lines 1340–1694 (helpers) | `cli/helpers.py` | Pure functions, move as-is |
| Lines 1696–2658 (parser) | `cli/parser.py` | `main()` function + all argparse |

**Migration strategy**: 
1. Create `cli/` package with `__init__.py` re-exporting `CLI` and `main` from `Cli.py`.
2. Extract one command group at a time into `cli/commands/*.py`.
3. Each command module exports functions that the `CLI` class delegates to.
4. Move `main()` to `cli/parser.py` last.
5. Keep `Cli.py` as a thin shim that imports from `cli/` for backward compatibility.

---

### 2.2 `core/kernel.py` → decompose in-place

**Target structure**:
```
core/
├── kernel.py              # Slim Kernel class (init, properties, execute_task orchestration)
├── kernel_constants.py    # MEDICAL_BOUNDARY, SUPERMEDICINE_SYSTEM_PROMPT
├── kernel_llm_chat.py     # _execute_llm_chat extracted as standalone function/module
├── kernel_plugin_select.py # _select_plugin_action extracted as pure function
```

**What moves where**:
| Current location | Target file | Notes |
|------------------|-------------|-------|
| Lines 27–61 (constants) | `core/kernel_constants.py` | Import back into kernel.py |
| Lines 483–744 (`_execute_llm_chat`) | `core/kernel_llm_chat.py` | Extract as `execute_llm_chat(kernel, task, ...)` function |
| Lines 810–857 (`_select_plugin_action`) | `core/kernel_plugin_select.py` | Pure function, no class state needed |
| Lines 746–793 (`_llm_chat_messages`) | `core/kernel_llm_chat.py` | Goes with chat logic |
| Lines 795–808 (`_workspace_tool_runtime_context`) | `core/kernel_llm_chat.py` | Used only by `_llm_chat_messages` |

**Key decisions**:
- `execute_task` stays in `kernel.py` but should be decomposed internally into smaller private methods:
  - `_dispatch_plugin_task()` — lines 239–446
  - `_build_permission_context()` — lines 253–269
  - `_handle_permission_denied()` — lines 289–318
  - `_handle_missing_plugin()` — lines 321–343
  - `_execute_plugin()` — lines 345–446
- Keep `Kernel` class in `core/kernel.py` for import compatibility.

---

### 2.3 `core/log_report.py` → decompose in-place

**Target structure**:
```
core/
├── log_report.py              # Slim: imports, LogReportStore, re-exports
├── log_severity.py            # Severity constants + normalize/detect/format functions
├── log_report_models.py       # LogReport, LogStorageLocations dataclasses
├── log_report_handler.py      # LogReportLoggingHandler + TUI log helpers
```

**What moves where**:
| Current location | Target file | Notes |
|------------------|-------------|-------|
| Lines 20–110 (severity) | `core/log_severity.py` | Pure functions + constants |
| Lines 117–181 (dataclasses) | `core/log_report_models.py` | LogReport, LogStorageLocations |
| Lines 768–857 (handler + TUI) | `core/log_report_handler.py` | LogReportLoggingHandler, configure_tui_log_storage, append_tui_stream_output |
| Lines 184–766 (LogReportStore) | `core/log_report.py` | Stays, but imports from above |

**Internal decomposition of LogReportStore**:
- Extract `_statistics_from_entries` and `_tail_display_lines` into a `log_statistics.py` if needed.
- Extract `_entry_from_record`, `_records_from_payload`, `_coerce_record` into a `log_record_processing.py` if LogReportStore still exceeds 400 lines.

---

### 2.4 `core/workspace_tools.py` → decompose in-place

**Target structure**:
```
core/
├── workspace_tools.py          # Slim: WorkspaceToolService, re-exports
├── workspace_tool_models.py    # ToolManifest, ToolInvocationPlan, ToolImportCandidate, exceptions
├── workspace_tool_templates.py # PYTHON_RUNNER, R_RUNNER, BUILTIN_TEMPLATES, _manifest_text
├── workspace_tool_spec.py      # TOOL_AUTHORING_SPEC, build_tool_authoring_llm_context
```

**What moves where**:
| Current location | Target file | Notes |
|------------------|-------------|-------|
| Lines 30–67 (exceptions + constants) | `core/workspace_tool_models.py` | Alongside dataclasses |
| Lines 90–153 (TOOL_AUTHORING_SPEC) | `core/workspace_tool_spec.py` | Large dict constant |
| Lines 174–369 (3 dataclasses) | `core/workspace_tool_models.py` | ToolManifest, ToolInvocationPlan, ToolImportCandidate |
| Lines 371–525 (templates) | `core/workspace_tool_templates.py` | Large string constants |
| Lines 534–1043 (WorkspaceToolService) | `core/workspace_tools.py` | Stays, imports from above |

---

### 2.5 `core/tui/app.py` → `core/tui/` package decomposition

**Target structure**:
```
core/tui/
├── app.py                  # Slim: SuperMedicineTUI, launch_tui, re-exports
├── stream_capture.py       # _TUILogTextSink, _TUIThreadRoutedStream, _capture_current_thread_tui_streams
├── kernel_output.py        # _redact_display_secrets, _strip_internal_kernel_output, constants
├── prompt_input.py         # PromptInput widget
├── menu_screens.py         # MainMenuScreen, ViewSelectMenuScreen
├── nav_widgets.py          # NavItem, MenuOption, MenuButton
├── status_helpers.py       # apply_status_style, _console_safe_text, _describe_llm_status
├── types.py                # TUIStatus, NavMetadata, ShellStatusText, DynamicRefreshSurface
```

**What moves where**:
| Current location | Target file | Notes |
|------------------|-------------|-------|
| Lines 36–116 (stream capture) | `core/tui/stream_capture.py` | Reusable utility |
| Lines 118–222 (kernel output) | `core/tui/kernel_output.py` | Kernel output filtering |
| Lines 224–248 (status styling) | `core/tui/status_helpers.py` | Pure function |
| Lines 251–299 (dataclasses) | `core/tui/types.py` | Type definitions |
| Lines 301–324 (nav widgets) | `core/tui/nav_widgets.py` | UI components |
| Lines 335–419 (menu screens) | `core/tui/menu_screens.py` | Modal screens |
| Lines 422–553 (PromptInput) | `core/tui/prompt_input.py` | Self-contained widget |
| Lines 1406–1464 (helpers) | `core/tui/status_helpers.py` | Entry-point helpers |

---

## 3. Module Boundaries

### 3.1 Proposed New Module Structure

```
cli/
├── __init__.py
├── logging_setup.py
├── helpers.py
├── commands/
│   ├── __init__.py
│   ├── workspace.py
│   ├── tool.py
│   ├── llm.py
│   ├── permission.py
│   ├── paper.py
│   ├── experience.py
│   ├── experiment.py
│   ├── log.py
│   └── self_evolve.py
├── cli_core.py
└── parser.py

core/
├── kernel.py                   (slimmed)
├── kernel_constants.py         (new)
├── kernel_llm_chat.py          (new)
├── kernel_plugin_select.py     (new)
├── log_report.py               (slimmed)
├── log_severity.py             (new)
├── log_report_models.py        (new)
├── log_report_handler.py       (new)
├── workspace_tools.py          (slimmed)
├── workspace_tool_models.py    (new)
├── workspace_tool_templates.py (new)
├── workspace_tool_spec.py      (new)
└── tui/
    ├── app.py                  (slimmed)
    ├── stream_capture.py       (new)
    ├── kernel_output.py        (new)
    ├── prompt_input.py         (new)
    ├── menu_screens.py         (new)
    ├── nav_widgets.py          (new)
    ├── status_helpers.py       (new)
    └── types.py                (new)
```

### 3.2 Import Dependency Rules

**No circular imports allowed.** The dependency graph flows:

```
cli/commands/*  →  core/kernel, core/workspace_tools, core/log_report, ...
cli/cli_core    →  cli/commands/*
cli/parser      →  cli/cli_core
core/kernel     →  core/kernel_constants, core/kernel_llm_chat, core/kernel_plugin_select
core/log_report →  core/log_severity, core/log_report_models, core/log_report_handler
core/workspace_tools → core/workspace_tool_models, core/workspace_tool_templates, core/workspace_tool_spec
core/tui/app    →  core/tui/stream_capture, core/tui/kernel_output, core/tui/prompt_input, ...
```

### 3.3 Backward Compatibility

- **`Cli.py`**: Keep as a shim that re-exports `CLI` and `main` from `cli/`. All existing `from Cli import ...` statements continue to work.
- **`core/kernel.py`**: Keep `Kernel` class in same file. New modules are internal.
- **`core/log_report.py`**: Keep `LogReportStore` in same file. Re-export from sub-modules.
- **`core/workspace_tools.py`**: Keep `WorkspaceToolService` in same file. Re-export.
- **`core/tui/app.py`**: Keep `SuperMedicineTUI` and `launch_tui` in same file. Re-export.

---

## 4. Test Coverage

### 4.1 Existing Tests That Must Continue Passing

| Test file | Covers | Risk level |
|-----------|--------|------------|
| `tests/test_kernel_full.py` | Kernel.execute_task, plugin dispatch, plus coverage historically split across focused kernel tests | **HIGH** — most affected |
| `test_log_report.py` | LogReportStore CRUD | **HIGH** — module decomposition |
| `tests/test_workspace_full.py` | WorkspaceToolService, including coverage historically split across focused workspace-tool tests | **HIGH** — module decomposition |
| `test_tui_entrypoint.py` | launch_tui, dry-run | **MEDIUM** — import paths change |
| `tests/test_tui.py` | Chat processing and other consolidated TUI chat-view coverage | **MEDIUM** — kernel output filtering |
| `test_workspace_cli.py` | CLI workspace commands | **MEDIUM** — CLI class refactoring |
| `test_paper_cli.py` | CLI paper commands | **MEDIUM** |
| `test_experience_cli.py` | CLI experience commands | **MEDIUM** |
| `test_experiment_cli.py` | CLI experiment commands | **MEDIUM** |
| `test_self_evolution_cli.py` | CLI self-evolve | **MEDIUM** |
| `test_permission_modes.py` | CLI permission commands | **MEDIUM** |
| `test_integration.py` | End-to-end flows | **HIGH** |
| All other test files | Various | LOW |

### 4.2 New Tests Needed

| Test target | What to verify |
|-------------|---------------|
| `cli/logging_setup.py` | `_RedactingFormatter` redacts secrets, `_configure_cli_logging` sets up handler |
| `cli/commands/*.py` | Each command function produces expected output (migrate from CLI class tests) |
| `cli/parser.py` | `main()` dispatches to correct CLI methods for each subcommand |
| `core/kernel_constants.py` | Constants are importable and unchanged |
| `core/kernel_llm_chat.py` | `execute_llm_chat` handles streaming, errors, empty responses |
| `core/kernel_plugin_select.py` | `select_plugin_action` returns correct (plugin, action) for each keyword |
| `core/log_severity.py` | `normalize_log_severity`, `detect_log_severity`, `format_log_message` |
| `core/log_report_models.py` | `LogReport.from_dict/to_dict`, `LogStorageLocations.to_dict` |
| `core/workspace_tool_models.py` | `ToolManifest.from_dict` validation, `ToolImportCandidate.to_dict` |
| `core/workspace_tool_templates.py` | Templates are valid YAML, runner scripts are syntactically correct |
| `core/tui/stream_capture.py` | `_TUILogTextSink` captures lines, `_TUIThreadRoutedStream` routes correctly |
| `core/tui/kernel_output.py` | `_strip_internal_kernel_output` removes telemetry keys |
| `core/tui/prompt_input.py` | `PromptInput` filters terminal controls, preserves normal text |
| `core/tui/types.py` | Dataclass construction and serialization |

---

## 5. Risk Assessment

### 5.1 High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Import cycle creation** | Runtime ImportError | Strict dependency graph; no command module imports another command module |
| **CLI class method signatures change** | Breaking CLI tests | Keep `CLI` class as thin delegation layer; method signatures unchanged |
| **LogReportStore internal method visibility** | Tests calling private methods fail | Keep private methods in same class; only extract pure helper functions |
| **`from core.log_report import X` breaks** | 50+ test files | Re-export all public names from `core/log_report.py` |

### 5.2 Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **argparse parser names change** | CLI dispatch breaks | Move entire `main()` as-is; don't refactor parser structure |
| **TUI widget import paths change** | TUI screens break | Re-export from `core/tui/app.py` |
| **Lazy imports in CLI methods** | Import timing changes | Preserve lazy imports in extracted command functions |
| **Thread safety of log storage** | Data corruption | Keep `_LOG_STORAGE_LOCK` in `core/log_report.py` where it's used |

### 5.3 Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Test file import paths** | Minor test fixes | Update imports in affected test files |
| **Type annotation forward references** | mypy errors | Use `TYPE_CHECKING` guards consistently |
| **Docstring drift** | Documentation inconsistency | Preserve docstrings exactly during extraction |

---

## 6. Execution Order

### Phase 1: Low-Risk Extractions (no behavioral change, pure moves)

**Step 1.1**: Extract `core/log_severity.py`
- Move severity constants and functions (lines 20–110) to new file
- Update `core/log_report.py` to import from `core/log_severity.py`
- Run `python -m pytest tests/test_log_report.py -x -q`

**Step 1.2**: Extract `core/log_report_models.py`
- Move `LogReport`, `LogStorageLocations`, `resolve_log_storage_locations` (lines 117–181)
- Update imports in `core/log_report.py`
- Run `python -m pytest tests/test_log_report.py -x -q`

**Step 1.3**: Extract `core/log_report_handler.py`
- Move `LogReportLoggingHandler`, `configure_tui_log_storage`, `append_tui_stream_output` (lines 768–857)
- Run `python -m pytest tests/test_log_report.py tests/test_tui_entrypoint.py -x -q`

**Step 1.4**: Extract `core/workspace_tool_models.py`
- Move exceptions + constants + dataclasses (lines 30–369)
- Run `python -m pytest tests/test_workspace_full.py -x -q`

**Step 1.5**: Extract `core/workspace_tool_templates.py`
- Move `PYTHON_RUNNER`, `R_RUNNER`, `BUILTIN_TEMPLATES`, `_manifest_text` (lines 371–525)
- Run `python -m pytest tests/test_workspace_full.py -x -q`

**Step 1.6**: Extract `core/workspace_tool_spec.py`
- Move `TOOL_AUTHORING_SPEC`, `build_tool_authoring_llm_context` (lines 90–153)
- Run `python -m pytest tests/test_workspace_full.py -x -q`

**Step 1.7**: Extract `core/kernel_constants.py`
- Move `MEDICAL_BOUNDARY`, `SUPERMEDICINE_SYSTEM_PROMPT` (lines 27–61)
- Run `python -m pytest tests/test_kernel_full.py -x -q`

**Step 1.8**: Extract `core/kernel_plugin_select.py`
- Move `_select_plugin_action` as `select_plugin_action(task: str) -> tuple[str | None, str | None]` (lines 810–857)
- Run `python -m pytest tests/test_kernel_full.py -x -q`

### Phase 2: TUI Decomposition

**Step 2.1**: Extract `core/tui/types.py`
- Move `TUIStatus`, `NavMetadata`, `ShellStatusText`, `DynamicRefreshSurface` (lines 251–299)
- Run `python -m pytest tests/test_tui_entrypoint.py tests/test_tui_state.py -x -q`

**Step 2.2**: Extract `core/tui/stream_capture.py`
- Move `_TUILogTextSink`, `_TUIThreadRoutedStream`, `_capture_current_thread_tui_streams` (lines 36–116)
- Run `python -m pytest tests/test_tui_entrypoint.py -x -q`

**Step 2.3**: Extract `core/tui/kernel_output.py`
- Move `_redact_display_secrets`, `_strip_internal_kernel_output`, related constants (lines 118–222)
- Run `python -m pytest tests/test_tui.py -x -q`

**Step 2.4**: Extract `core/tui/prompt_input.py`
- Move `PromptInput` class (lines 422–553)
- Run `python -m pytest tests/test_tui_entrypoint.py tests/test_tui.py -x -q`

**Step 2.5**: Extract `core/tui/nav_widgets.py`
- Move `NavItem`, `MenuOption`, `MenuButton` (lines 301–324)
- Run `python -m pytest tests/test_tui_entrypoint.py -x -q`

**Step 2.6**: Extract `core/tui/menu_screens.py`
- Move `ViewSelectMenuScreen`, `MainMenuScreen` (lines 335–419)
- Run `python -m pytest tests/test_tui_entrypoint.py -x -q`

**Step 2.7**: Extract `core/tui/status_helpers.py`
- Move `apply_status_style`, `_console_safe_text`, `_describe_llm_status` (lines 224–248, 1406–1464)
- Run `python -m pytest tests/test_tui_entrypoint.py -x -q`

### Phase 3: Kernel LLM Chat Extraction

**Step 3.1**: Extract `core/kernel_llm_chat.py`
- Move `_execute_llm_chat`, `_llm_chat_messages`, `_workspace_tool_runtime_context`, `_llm_runtime_context` (lines 448–808)
- Convert to standalone functions taking kernel state as parameters
- Run `python -m pytest tests/test_kernel_full.py tests/test_tui.py -x -q`

**Step 3.2**: Decompose `execute_task` internally
- Break into `_dispatch_plugin_task`, `_build_permission_context`, etc. within `Kernel` class
- No file extraction — just method decomposition
- Run `python -m pytest tests/test_kernel_full.py tests/test_integration.py -x -q`

### Phase 4: CLI Decomposition

**Step 4.1**: Create `cli/` package structure
- Create `cli/__init__.py` re-exporting from `Cli.py`
- Create `cli/logging_setup.py` with logging infrastructure
- Create `cli/helpers.py` with module-level helper functions
- Run `python -m pytest tests/ -x -q` (full suite)

**Step 4.2**: Extract CLI command modules one by one
- Order: `permission.py` → `llm.py` → `log.py` → `workspace.py` → `tool.py` → `paper.py` → `experience.py` → `experiment.py` → `self_evolve.py`
- Each step: extract functions → update `CLI` class to delegate → run full test suite
- Run `python -m pytest tests/ -x -q` after each extraction

**Step 4.3**: Extract `cli/parser.py`
- Move `main()` function
- Update `Cli.py` shim to import from `cli.parser`
- Run `python -m pytest tests/ -x -q`

### Phase 5: Validation

**Step 5.1**: Run full test suite
```
python -m pytest tests/ -x -q
```

**Step 5.2**: Verify all public import paths still work
- `from Cli import CLI, main`
- `from core.kernel import Kernel`
- `from core.log_report import LogReportStore`
- `from core.workspace_tools import WorkspaceToolService`
- `from core.tui.app import SuperMedicineTUI, launch_tui`

**Step 5.3**: Verify no circular imports
```
python -c "from cli import CLI; from core.kernel import Kernel; from core.log_report import LogReportStore; from core.workspace_tools import WorkspaceToolService; from core.tui.app import SuperMedicineTUI; print('All imports OK')"
```

---

## Appendix: Line Count Estimates (After Refactoring)

| File | Before | After (est.) | Reduction |
|------|--------|-------------|-----------|
| `Cli.py` (shim) | 2662 | ~10 | -99% |
| `cli/cli_core.py` | — | ~200 | New |
| `cli/parser.py` | — | ~400 | New |
| `cli/helpers.py` | — | ~350 | New |
| `cli/commands/*.py` (9 files) | — | ~100–200 each | New |
| `cli/logging_setup.py` | — | ~80 | New |
| `core/kernel.py` | 857 | ~300 | -65% |
| `core/kernel_constants.py` | — | ~40 | New |
| `core/kernel_llm_chat.py` | — | ~350 | New |
| `core/kernel_plugin_select.py` | — | ~50 | New |
| `core/log_report.py` | 857 | ~400 | -53% |
| `core/log_severity.py` | — | ~100 | New |
| `core/log_report_models.py` | — | ~70 | New |
| `core/log_report_handler.py` | — | ~100 | New |
| `core/workspace_tools.py` | 1043 | ~520 | -50% |
| `core/workspace_tool_models.py` | — | ~250 | New |
| `core/workspace_tool_templates.py` | — | ~160 | New |
| `core/workspace_tool_spec.py` | — | ~70 | New |
| `core/tui/app.py` | 1464 | ~500 | -66% |
| `core/tui/stream_capture.py` | — | ~90 | New |
| `core/tui/kernel_output.py` | — | ~110 | New |
| `core/tui/prompt_input.py` | — | ~140 | New |
| `core/tui/menu_screens.py` | — | ~90 | New |
| `core/tui/nav_widgets.py` | — | ~30 | New |
| `core/tui/status_helpers.py` | — | ~80 | New |
| `core/tui/types.py` | — | ~50 | New |

**Total**: ~6,016 → ~6,016 (same total lines, but each file ≤ 520 lines).
