# Debug BUG Priority and Minimal Fix Plan

**Source inputs:** `Architecture/DebugReviewTaskLedger.md` and `C:\Users\D2O\Desktop\Debug.txt` (`Beta0.4.2`).  
**Scope:** documentation-only BUG triage and minimum repair planning. This plan does **not** authorize source behavior changes, broad refactors, or test implementation by itself.  
**Fix rule:** each future implementation task must change only the proven erroneous behavior for that ledger ID, add/update only the mapped regression coverage, and avoid unrelated UI redesign, architecture restructuring, or feature expansion.

## Priority Model

- **阻断级 / Blocker:** prevents a core workflow or safety boundary from functioning, or risks executing in the wrong permission/security mode.
- **严重级 / Severe:** breaks a major advertised workflow or makes important runtime state invisible/untrustworthy, but can usually be worked around.
- **普通级 / Normal:** likely product defect or high-impact uncertainty that needs proof before code changes; not yet proven to block a core workflow.

## BUG Queue Sorted by Priority

| Priority | Ledger ID | BUG / suspected BUG summary | Minimum next action |
| --- | --- | --- | --- |
| 阻断级 / Blocker | DBG-BUG-001 | Permission `FULL`/`P` switching, chat leakage, conservative authorized-root import, and permission indicator placement. | Reproduce mode switching and path import failures, then patch only permission input routing/parsing/status placement defects. |
| 严重级 / Severe | DBG-BUG-003 | R/Python tools such as heatmap/UMAP are suspected to be missing from scan/import. | Prove whether manifests, scan roots, language handling, or TUI selection are failing; patch only the failing discovery/import boundary. |
| 严重级 / Severe | DBG-BUG-002 | Logs are not confirmed to aggregate into one per-launch/session log record. | Confirm current log container lifecycle, then patch only session identity/append semantics if fragmented. |
| 严重级 / Severe | DBG-BUG-004 | LLM Thinking/progress is invisible during dialogs. | Confirm provider/event support and user policy, then patch only safe progress/reasoning display fallback. |

## Evidence-Only Non-BUG Watch Items Sorted by Priority

These Question/Better entries are **not** BUG implementation items. They stay outside the BUG queue until evidence proves a concrete defect or misleading advertised behavior.

| Priority | Ledger ID | Current type | Evidence-only summary | Minimum next action |
| --- | --- | --- | --- | --- |
| 普通级 / Normal | DBG-Q-001 | Question | Multi-Agent authenticity is unclear: normal flows may be single-agent only. | Diagnostic only; promote to BUG only if advertised multi-agent flow is proven inactive or misleading. |
| 普通级 / Normal | DBG-BET-001 | Better | Settings/menu entry and localization confusion may include broken entry points. | Keep as Better unless `M`/menu/settings entry is proven nonfunctional rather than merely confusing. |
| 普通级 / Normal | DBG-BET-002 | Better | Shortcut policy/IME behavior may include accidental shortcut triggering. | Keep as Better unless a reproducible input-loss or wrong-command trigger is captured. |

## Per-BUG Minimal Fix Paths

### DBG-BUG-001 — Permission FULL/P switching and authorized-root import

- **Priority:** 阻断级 / Blocker.
- **Reproducible / evidence summary:** `Debug.txt` lines 3-4 report that entering `FULL` does not switch to complete/full access, `FULL` can also be sent into Chat, conservative-mode accessible-directory import fails, absolute/relative paths and quoted/unquoted paths are not all recognized, and the lower-left `P` permission indicator is visually misplaced. Ledger marks this as evidence-first before patching.
- **Candidate source files:** `permission/access_mode.py`, `permission/engine.py`, `permission/policy.py`, `core/path_safety.py`, `core/tui/permissions.py`, `core/tui/screens/permission_screen.py`, `core/tui/app.py`, `core/tui/state.py`, `core/tui/screens/chat_view.py`.
- **Candidate test files:** `tests/test_permission_modes.py`, `tests/test_permission_engine.py`, `tests/test_policy.py`, `tests/test_path_safety.py`, `tests/test_tui_permissions.py`, `tests/test_tui_chat_view.py`, `tests/test_tui_state.py`.
- **Minimum fix boundary:** only separate permission confirmation input from chat input routing; normalize accepted `FULL`/`P` mode commands to the existing access-mode model; normalize conservative authorized-root text by trimming quotes and resolving relative paths through the existing path-safety policy; reposition/integrate the permission indicator only enough to stop layout collision or disconnected placement. Do not redesign the whole TUI, rename modes, loosen policy checks, or add new permission levels.
- **Tests to add/update:** add regression cases for `FULL` changing the stored/effective mode without adding a chat message; `P`/permission UI state reflecting the selected mode; conservative authorized roots accepting absolute, relative, quoted, and unquoted paths; invalid paths still rejected; permission indicator rendered in the intended status/surface without duplicating chat text.
- **Acceptance commands:** `python -m pytest tests/test_permission_modes.py tests/test_permission_engine.py tests/test_policy.py tests/test_path_safety.py tests/test_tui_permissions.py tests/test_tui_chat_view.py tests/test_tui_state.py`
- **May change user-visible behavior?** Yes. Permission mode switching, path import feedback, and the TUI permission indicator become visibly different/corrected.
- **Needs user confirmation?** No for the functional bug fixes already requested. Yes only if the future implementation proposes a materially different visual location/style beyond the minimal integration needed to fix the misplaced `P` indicator.

### DBG-BUG-003 — R/Python tool scan/import failure

- **Priority:** 严重级 / Severe.
- **Reproducible / evidence summary:** `Debug.txt` line 8 reports that R/Python tools are suspected not to be recognized/imported, with heatmap and UMAP examples not scanned. Repository evidence shows tool manifests/templates under `plugins/tools/`, including `python_data_analysis/tool.yaml`, `r_data_analysis/tool.yaml`, `r_template/tool.yaml`, `python_stats/plugin.yaml`, `r_survival/plugin.yaml`, and the workspace tool/TUI surfaces.
- **Candidate source files:** `core/workspace_tools.py`, `core/plugin_registry.py`, `core/tui/screens/tool_screen.py`, `core/tui/screens/workspace_screen.py`, `plugins/tools/*/tool.yaml`, `plugins/tools/*/plugin.yaml`, `plugins/tools/python_data_analysis/runner.py`, `plugins/tools/r_data_analysis/runner.R`, `plugins/tools/r_template/runner.R`.
- **Candidate test files:** `tests/test_workspace_tools.py`, `tests/test_plugin_registry.py`, `tests/test_tui_workspace_screens.py`, `tests/test_workspace.py`, `tests/test_workspace_cli.py`, `tests/test_python_stats.py`, `tests/test_r_survival.py`.
- **Minimum fix boundary:** first determine whether the failure is missing manifests for heatmap/UMAP, scan-root mismatch, YAML schema mismatch, language filter mismatch, duplicate ID suppression, or TUI display/import selection. Patch only that boundary: manifest inclusion/diagnostics, scan path inclusion, schema parsing, language recognition, or UI listing/import handoff. Do not introduce a new plugin framework, add unrelated analysis tools, or rewrite plugin registry semantics.
- **Tests to add/update:** add fixture-based scan coverage for at least one valid Python tool and one valid R tool; add explicit coverage for heatmap/UMAP-style manifest names if those are intended bundled tools; verify invalid/missing manifests produce actionable diagnostics; verify TUI/workspace import receives discovered tool IDs rather than requiring manual IDs.
- **Acceptance commands:** `python -m pytest tests/test_workspace_tools.py tests/test_plugin_registry.py tests/test_tui_workspace_screens.py tests/test_workspace.py tests/test_workspace_cli.py tests/test_python_stats.py tests/test_r_survival.py`
- **May change user-visible behavior?** Yes. Tool lists, diagnostics, and import availability may change.
- **Needs user confirmation?** No if fixing recognition/import of existing intended tool manifests. Yes if heatmap/UMAP must be added as new bundled tools rather than discovered from existing user/import templates.

### DBG-BUG-002 — Session-level log lifecycle aggregation

- **Priority:** 严重级 / Severe.
- **Reproducible / evidence summary:** `Debug.txt` line 6 requests that logs be merged so each application opening/use creates one log record and all logs before exit are recorded there. Ledger notes current log semantics need comparison with requested session-level aggregation.
- **Candidate source files:** `core/log_report.py`, `core/tui/app.py`, `core/tui/screens/log_screen.py`, `core/session_manager.py`, `core/event_bus.py`, `core/redaction.py`, CLI entry surfaces if log commands are present.
- **Candidate test files:** `tests/test_log_report.py`, `tests/test_tui_log_screen.py`, `tests/test_session_manager.py`, `tests/test_event_bus.py`, `tests/test_redaction.py`, `tests/test_experiment_log_integration.py`.
- **Minimum fix boundary:** if fragmentation is proven, introduce or reuse one stable per-launch/per-session log container identifier and append all redacted events to it through normal exit. Keep existing redaction and retention rules. Do not change log payload schema beyond necessary session ID/container linkage, do not remove existing readable history, and do not log sensitive content.
- **Tests to add/update:** add lifecycle coverage proving one launch/session keeps one stable container across multiple events/screens; append order is preserved; normal exit/finalization writes to the same container; redaction still applies; log screen/CLI can display the session container.
- **Acceptance commands:** `python -m pytest tests/test_log_report.py tests/test_tui_log_screen.py tests/test_session_manager.py tests/test_event_bus.py tests/test_redaction.py tests/test_experiment_log_integration.py`
- **May change user-visible behavior?** Yes. Log grouping/display and file/report naming may change.
- **Needs user confirmation?** Yes if implementers must choose between “one JSONL/file per launch” and “one JSON object/report record per launch.” No if repository evidence already exposes a single intended container format and only append routing is broken.

### DBG-BUG-004 — LLM Thinking/progress visibility

- **Priority:** 严重级 / Severe.
- **Reproducible / evidence summary:** `Debug.txt` line 10 reports that the LLM thinking process is invisible and asks for dynamic real-time Thinking updates in the dialog. Ledger notes provider capabilities and privacy/policy constraints vary.
- **Candidate source files:** `core/llm_client.py`, `core/llm_manager.py`, `core/llm_providers/base.py`, `core/llm_providers/openrouter.py`, `core/kernel.py`, `core/tui/screens/chat_view.py`, `core/tui/screens/dialog_screen.py`, `core/tui/app.py`, `core/tui/state.py`.
- **Candidate test files:** `tests/test_llm_client.py`, `tests/test_llm_manager.py`, `tests/test_kernel.py`, `tests/test_tui_chat_view.py`, `tests/test_tui_dialog_history.py`, `tests/test_tui_llm_screen.py`, `tests/test_tui_state.py`.
- **Minimum fix boundary:** only expose a safe, labeled live progress/thinking surface using provider events that are already available or a non-sensitive progress fallback when reasoning tokens are unavailable. Do not expose hidden chain-of-thought, internal prompts, provider secrets, or raw reasoning unless the user has explicitly approved that policy and the provider returns it as user-displayable content.
- **Tests to add/update:** add streaming/progress event tests for providers with thinking/progress events; fallback display tests for providers without reasoning stream; TUI rendering tests that label the area and update it dynamically without storing sensitive internal prompt content in dialog history unless allowed.
- **Acceptance commands:** `python -m pytest tests/test_llm_client.py tests/test_llm_manager.py tests/test_kernel.py tests/test_tui_chat_view.py tests/test_tui_dialog_history.py tests/test_tui_llm_screen.py tests/test_tui_state.py`
- **May change user-visible behavior?** Yes. Dialogs will show a new live Thinking/progress area or fallback status.
- **Needs user confirmation?** Yes. User/product policy must confirm whether the display should be raw provider reasoning, summarized thinking, or progress-only status.

### DBG-Q-001 — Multi-Agent authenticity investigation, not yet a BUG

- **Priority:** 普通级 / Normal until evidence proves a defect.
- **Reproducible / evidence summary:** `Debug.txt` lines 25-26 state uncertainty about whether multi-Agent is working normally or whether the system always runs a single-Agent dialog. The ledger correctly classifies this as Question because no broken expected flow is yet proven.
- **Candidate source files:** `agents/orchestrator.py`, `agents/base_agent.py`, `agents/state_machine.py`, `agents/checkpoint.py`, `adapters/opencode/adapter.py`, `core/kernel.py`, `core/tui/app.py`, `core/tui/screens/chat_view.py`.
- **Candidate test files:** `tests/test_orchestrator.py`, `tests/test_state_machine.py`, `tests/test_checkpoint.py`, `tests/test_opencode_adapter.py`, `tests/test_standalone_adapter.py`, `tests/test_integration.py`, `tests/test_kernel.py`.
- **Minimum fix boundary:** do not patch yet. First produce evidence mapping each user-facing flow to either `Orchestrator.dispatch`, adapter subagent dispatch, or direct `Kernel`/LLM execution. If a documented multi-agent flow is proven inactive or falsely advertised, open a BUG follow-up that patches only that dispatch entry point or documentation mismatch.
- **Tests to add/update:** investigation may identify missing tests; future BUG coverage should assert the exact flow dispatches through orchestrator when multi-agent is selected and uses direct kernel path only when single-agent mode is intended.
- **Acceptance commands:** `python -m pytest tests/test_orchestrator.py tests/test_state_machine.py tests/test_checkpoint.py tests/test_opencode_adapter.py tests/test_standalone_adapter.py tests/test_integration.py tests/test_kernel.py`
- **May change user-visible behavior?** Investigation alone: no. A future BUG fix could change routing, labels, or mode selection.
- **Needs user confirmation?** Possibly. Required if the choice is to make multi-Agent default rather than optional, or to change how modes are exposed.

## Non-BUG Items Kept Out of Immediate Fix Implementation

| Ledger ID | Current type | Reason not promoted to BUG now | Later path |
| --- | --- | --- | --- |
| DBG-Q-001 | Question | Multi-Agent authenticity lacks proof of a broken expected flow; it requires evidence mapping before any code change. | Evidence-only diagnostic first; promote only if an advertised multi-agent flow is proven inactive or misleading. |
| DBG-BET-001 | Better | Settings/menu unification and localization are product/UI improvements unless a specific settings entry is proven broken. | UX/menu design task after user confirms final `M`/upper-left menu structure and localized labels. |
| DBG-BET-002 | Better | Shortcut policy and IME compatibility are important but currently described as confusing policy, not a reproduced incorrect command/input-loss defect. | Evidence-first keybinding audit; promote only reproducible shortcut/input bugs. |
| DBG-BET-003 | Better | Whole repository function placement/optimization is an architecture audit, not one wrong behavior. | Repository audit/refactor planning with behavior-preserving boundaries. |
| DBG-BET-004 | Better | TUI beautification requires preview and explicit user confirmation, not a bug fix. | Design preview in `C:\Users\D2O\Downloads`, then approved implementation. |
| DBG-BET-005 | Better | Logo design is branding/documentation work. | User-approved minimal text logo before Markdown embedding. |
| DBG-BET-006 | Better | Markdown release quality/language split is documentation quality work. | Staged docs rewrite/split preserving command accuracy. |
| DBG-REB-001 | Rebuild | Opencode alignment is an external-reference rebuild/audit and legal/product decision set, not a minimal bug fix. | Safe comparison matrix and separately approved alignment tasks. |
| DBG-REB-002 | Rebuild | Whole-repository refactor is explicitly constrained by duplicate/dead-code evidence and cannot be bundled into BUG fixes. | Evidence-based refactor queue with tests and user approval for risky changes. |

## Global Guardrails for Future Implementers

- Start each BUG with a failing automated or documented manual reproduction tied to the ledger ID.
- Change only the smallest source boundary necessary for that BUG; no opportunistic refactor, style sweep, unrelated TUI redesign, or plugin framework rewrite.
- Add/update the mapped tests before claiming the BUG is fixed; keep acceptance commands limited to the impacted area plus necessary adjacent regression files.
- Preserve security/privacy rules: permission fixes must not loosen path safety, log fixes must preserve redaction, and LLM Thinking fixes must not reveal hidden chain-of-thought or secrets without explicit policy approval.
- If evidence shows a ledger entry is not a BUG, keep it in Better/Question/Rebuild with rationale rather than promoting it to implementation.
