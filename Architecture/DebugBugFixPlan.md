# Debug BUG Priority and Minimal Fix Plan

**Source inputs:** `Architecture/DebugReviewTaskLedger.md` and `C:\Users\D2O\Desktop\Debug.txt` (`Beta0.4.2`).  
**Scope:** documentation-only BUG triage and minimum repair planning. This plan does **not** authorize source behavior changes, broad refactors, or test implementation by itself.  
**Fix rule:** each future implementation task must change only the proven erroneous behavior for that ledger ID, add/update only the mapped regression coverage, and avoid unrelated UI redesign, architecture restructuring, or feature expansion.

**Step 1 evidence matrix:** the current traceable 18-item baseline is recorded in `Architecture/DebugReviewTaskLedger.md#step-1-evidence-matrix-baseline`. Items without concrete code/test/docs/remote/artifact evidence are intentionally marked as gaps for later scoped work rather than treated as complete.

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
| 普通级 / Normal | DBG-BUG-005 | BUG | Real-time refresh is requested for all dynamically changing data/files, but impacted surfaces need inventory first. | Audit dynamic TUI/data/file surfaces and promote targeted refresh defects only after stale-display evidence is captured. |
| 普通级 / Normal | DBG-BET-001 | Better | Settings/menu entry and localization confusion may include broken entry points. | Keep as Better unless `M`/menu/settings entry is proven nonfunctional rather than merely confusing. |
| 普通级 / Normal | DBG-BET-002 | Better | Shortcut policy/IME behavior may include accidental shortcut triggering. | Keep as Better unless a reproducible input-loss or wrong-command trigger is captured. |
| 普通级 / Normal | DBG-BET-007 | Better | TUI title/key-label capitalization/style consistency is requested. | Keep as Better/style audit unless inconsistent titles are tied to a functional navigation or accessibility defect. |
| 普通级 / Normal | DBG-BET-008 | Better | Chat Processing status and temporary input lock are requested to prevent duplicate submissions. | Audit current in-flight chat handling; promote only if duplicate submission or missing task-state feedback is reproduced as a defect. |
| 普通级 / Normal | DBG-BET-009 | Better | Shortcut reduction into the `M` menu is requested. | Keep coupled to the menu/shortcut design task unless specific shortcuts are proven harmful. |
| 普通级 / Normal | DBG-BET-010 | Better | Professional GitHub Wiki content is requested; user has confirmed GitHub Wiki publishing authorization. | Documentation/publishing task requiring wiki structure/final content and use of the authorized publishing workflow, not a source BUG fix. |

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
- **Reproducible / evidence summary:** `Debug.txt` lines 35-36 state uncertainty about whether multi-Agent is working normally or whether the system always runs a single-Agent dialog. The ledger correctly classifies this as Question because no broken expected flow is yet proven.
- **Candidate source files:** `agents/orchestrator.py`, `agents/base_agent.py`, `agents/state_machine.py`, `agents/checkpoint.py`, `adapters/opencode/adapter.py`, `core/kernel.py`, `core/tui/app.py`, `core/tui/screens/chat_view.py`.
- **Candidate test files:** `tests/test_orchestrator.py`, `tests/test_state_machine.py`, `tests/test_checkpoint.py`, `tests/test_opencode_adapter.py`, `tests/test_standalone_adapter.py`, `tests/test_integration.py`, `tests/test_kernel.py`.
- **Minimum fix boundary:** do not patch yet. First produce evidence mapping each user-facing flow to either `Orchestrator.dispatch`, adapter subagent dispatch, or direct `Kernel`/LLM execution. If a documented multi-agent flow is proven inactive or falsely advertised, open a BUG follow-up that patches only that dispatch entry point or documentation mismatch.
- **Tests to add/update:** investigation may identify missing tests; future BUG coverage should assert the exact flow dispatches through orchestrator when multi-agent is selected and uses direct kernel path only when single-agent mode is intended.
- **Acceptance commands:** `python -m pytest tests/test_orchestrator.py tests/test_state_machine.py tests/test_checkpoint.py tests/test_opencode_adapter.py tests/test_standalone_adapter.py tests/test_integration.py tests/test_kernel.py`
- **May change user-visible behavior?** Investigation alone: no. A future BUG fix could change routing, labels, or mode selection.
- **Needs user confirmation?** Possibly. Required if the choice is to make multi-Agent default rather than optional, or to change how modes are exposed.

### DBG-BUG-005 — Dynamic data/file real-time refresh, evidence-first

- **Priority:** 普通级 / Normal until a concrete stale-display defect is proven for a specific surface.
- **Reproducible / evidence summary:** `Debug.txt` line 12 requires all dynamically changing data or files to refresh in real time. The ledger classifies this as BUG because stale dynamic state can be user-visible incorrect behavior, but it must be split by affected surface before implementation.
- **Candidate source files:** `core/tui/app.py`, `core/tui/screens/workspace_screen.py`, `core/tui/screens/tool_screen.py`, `core/tui/screens/log_screen.py`, `core/tui/screens/dialog_screen.py`, dashboard and other TUI screen modules with reloadable data, workspace/tool/log/dialog managers as discovered by surface inventory.
- **Candidate test files:** `tests/test_tui_workspace_screens.py`, `tests/test_tui_log_screen.py`, `tests/test_workspace_tools.py`, `tests/test_log_report.py`, TUI screen tests matching each proven stale surface.
- **Minimum fix boundary:** first inventory dynamic surfaces and reproduce stale data/file behavior per surface. Patch only the surface-specific refresh hook, activation refresh, manual refresh, polling, or watcher boundary that is proven stale. Do not introduce broad background polling or rewrite all TUI screens without evidence.
- **Tests to add/update:** add or update targeted stale-display regression coverage for each proven surface, including external file/data changes becoming visible under the confirmed real-time policy without breaking focus/input state.
- **Acceptance commands:** target only the affected TUI/data tests identified by evidence, then adjacent regression files for shared refresh hooks.
- **May change user-visible behavior?** Yes. Screen data may update more often and statuses may change.
- **Needs user confirmation?** Yes if implementation requires choosing between filesystem watching, periodic polling, activation refresh, or manual refresh semantics.

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
| DBG-BET-007 | Better | TUI title capitalization/style is a copy/design consistency request unless tied to navigation or accessibility breakage. | TUI string inventory and approved style pass. |
| DBG-BET-008 | Better | Chat Processing/lock request is UX/runtime-state improvement unless duplicate send or missing in-flight status is reproduced as a concrete defect. | Evidence-first chat lifecycle audit; promote targeted duplicate-submit/status defects only if proven. |
| DBG-BET-009 | Better | Shortcut reduction depends on the confirmed `M` menu structure and final retained shortcut policy. | Combined menu/shortcut design task after confirmation. |
| DBG-BET-010 | Better | GitHub Wiki writing is documentation publishing work outside immediate repository source fixes; publishing authorization is now user-confirmed and must not be treated as blocked. | Prepare the Wiki publishing set from existing release docs (`Home`, `Installation`, `TUI`, `Permissions`, `Tools`, `Logs`, `Architecture`, `OpenCode-Alignment`, `Contributing-or-Quality-Gates`) and execute publication only in Step 4 through the authorized workflow. |
| DBG-REB-001 | Rebuild | Opencode alignment is an external-reference rebuild/audit and legal/product decision set, not a minimal bug fix. | Safe comparison matrix and separately approved alignment tasks. |
| DBG-REB-002 | Rebuild | Whole-repository refactor is explicitly constrained by duplicate/dead-code evidence and cannot be bundled into BUG fixes. | Evidence-based refactor queue with tests and user approval for risky changes. |

## Global Guardrails for Future Implementers

- Start each BUG with a failing automated or documented manual reproduction tied to the ledger ID.
- Change only the smallest source boundary necessary for that BUG; no opportunistic refactor, style sweep, unrelated TUI redesign, or plugin framework rewrite.
- Add/update the mapped tests before claiming the BUG is fixed; keep acceptance commands limited to the impacted area plus necessary adjacent regression files.
- Preserve security/privacy rules: permission fixes must not loosen path safety, log fixes must preserve redaction, and LLM Thinking fixes must not reveal hidden chain-of-thought or secrets without explicit policy approval.
- If evidence shows a ledger entry is not a BUG, keep it in Better/Question/Rebuild with rationale rather than promoting it to implementation.

## Step 2 Cross-Check Closure Notes

**Review date:** 2026-06-08. Current implementation evidence is recorded item-by-item in `Architecture/DebugReviewTaskLedger.md#step-2-implementation-evidence-pass`.

**Deep code-audit update:** `Architecture/DebugReviewTaskLedger.md#step-2-deep-source-code-audit` now records source-level status for all 18 `Debug.txt` items, including concrete paths/functions/classes/modules and explicit code gaps where implementation is partial, confirmation-gated, external-only, or documentation-only.

- **DBG-BUG-001:** minimum functional gap closed for quoted/unquoted authorized-directory input by normalizing user-entered directory text in `core/config_center.py` before authorize/revoke. Existing evidence already covered dedicated TUI FULL confirmation and no chat routing leakage.
- **DBG-BUG-002:** session-level append semantics are already implemented in `core/log_report.py` and covered by existing log-report tests; no schema change required.
- **DBG-BUG-003:** Python/R scan/import and heatmap/UMAP templates are already implemented in `core/workspace_tools.py` and covered by existing workspace-tool tests; no new plugin framework or bundled-tool expansion required.
- **DBG-BUG-004:** visible provider-safe Thinking/progress is already implemented via `progress_callback`, `reasoning` events, and TUI chat rendering; raw hidden chain-of-thought remains intentionally undisclosed.
- **DBG-BUG-005:** targeted dynamic refresh hooks are already implemented for mounted/visible TUI views and documented as non-watcher/non-polling behavior. CI root-cause repair remains out of this Step 2 scope.
- **Shortcut/menu Better items:** global alphabetic bindings and docs have been aligned to uppercase `M`/`P`/`Q`; secondary actions remain under the menu.
- **Explicit code gaps carried forward from Step 2:** universal watcher/polling refresh, OS-level IME proof, preview-image approval workflow, GitHub Wiki publication evidence, full external Opencode comparison/alignment, and whole-repo refactor/optimization remained outside Step 2 implementation. Step 4 later closed the local clickable menu affordance and TUI string-inventory enforcement gaps, and recorded Wiki publication evidence at commit `d6a1e11`.

No further BUG implementation is authorized by this plan without new evidence or user confirmation for the confirmation-gated Better/Rebuild items.

## Step 4 Regression Coverage Closure Notes

**Review date:** 2026-06-08.

- **DBG-BUG-001 permission root normalization:** coverage gap closed in `tests/test_config_center.py` with quoted absolute and quoted relative authorized-root normalization, duplicate avoidance, policy allow decision, and revoke behavior.
- **Shortcut policy:** existing `tests/test_tui_entrypoint.py` coverage already verifies uppercase `M`/`P`/`Q` bindings and lowercase ordinary input handling; no additional test required.
- **DBG-BUG-005 / CI workspace refresh race:** existing `tests/test_tui_workspace_screens.py` coverage already uses condition-based waiting for external workspace creation plus manual refresh, matching the CI root-cause regression path; no additional test required.

## Step 4 Code Gap Closure Notes

**Review date:** 2026-06-08. Step 4 implemented minimal feasible local code/docs changes for the Step 2/3 confirmed gaps without claiming external approvals.

- **DBG-BET-010 Wiki publication evidence:** remote GitHub Wiki publication is now recorded as commit `d6a1e11` in this plan/ledger. This is evidence tracking only; local tests cannot prove remote availability.
- **DBG-BET-004 TUI preview artifact workflow:** `scripts/tui_preview_artifact.py` can generate a text preview artifact in the user's Downloads directory by default (`Path.home() / "Downloads"`) and explicitly states that user approval is not recorded. `tests/test_tui_entrypoint.py::test_tui_preview_artifact_workflow_writes_text_without_approval_claim` covers the artifact workflow using a temp output dir.
- **DBG-BET-001 clickable upper-left menu affordance:** `core/tui/app.py::MenuButton` and the `#menu-button` widget provide a visible/clickable `≡ 菜单 (M)` affordance at the top-left sidebar position; `tests/test_tui_entrypoint.py::test_tui_upper_left_menu_button_opens_menu` covers click-to-menu behavior.
- **DBG-BUG-005 targeted refresh boundary:** `core/tui/app.py::DynamicRefreshSurface` and `SuperMedicineTUI.dynamic_refresh_surfaces()` expose a code-backed inventory for workspace/log/dashboard/tool/dialog targeted refresh surfaces. No broad watcher/polling was added.
- **DBG-BET-007 TUI string inventory:** `core/tui/i18n.py::tui_title_style_inventory()` enforces retained English chat emphasis labels as single capitalized words while preserving Chinese-first navigation and screen titles. `tests/test_tui_entrypoint.py::test_tui_title_style_inventory_enforces_english_emphasis_without_replacing_chinese` covers that boundary.

## Step 3 Deep Test Coverage Audit Notes

**Review date:** 2026-06-08. Detailed item-by-item test audit is recorded in `Architecture/DebugReviewTaskLedger.md#step-3-deep-test-coverage-audit`.

- The audit inspected actual executable tests for all 18 `Debug.txt` ledger IDs and did not add superficial documentation-only assertions.
- Existing behavior-level tests cover the implemented/local behaviors: permission confirmation and authorized-root normalization, session log aggregation, Python/R heatmap/UMAP tool templates and scan/import flow, safe LLM progress/Thinking display, targeted workspace/log/dashboard refresh, `M` menu behavior, uppercase-only shortcut classification, Chat Processing lock/unlock/reject behavior, reduced shortcut/menu relocation, multi-agent/orchestrator diagnostic boundaries, and optional OpenCode adapter capability boundaries.
- No tests were changed in Step 3 because no uncovered local behavior gap was found that could be usefully tested without implementing a new approved feature.
- Manual/external/approval-gated items remain explicitly outside automated proof after Step 4: GitHub Wiki remote availability/content after commit `d6a1e11`, preview image generation and user approval, OS-level IME proof, full English-only TUI title sweep under Chinese localization constraints, full external Opencode comparison/alignment, and broad whole-repo refactor/optimization.
- Tester should use the ledger Step 3 matrix as the authoritative mapping from each ID to either executable test evidence or substitute manual/external verification rationale.

## Step 6 Final Closure Notes

**Review date:** 2026-06-08. Final item-by-item closure, CI repair summary, verification evidence policy, and artifact-cleanup status are recorded in `Architecture/DebugReviewTaskLedger.md#step-6-final-implementation-and-ci-closure-summary`.

- **Debug.txt 18-item closure:** every ledger ID has a final status and an evidence location. Items that still require confirmation are explicitly marked partial/confirmation-gated instead of being claimed complete; the GitHub Wiki item is authorization-cleared and queued for Step 4 publishing rather than blocked by authorization.
- **CI failure root cause:** Windows/Textual asynchronous refresh timing around `tests/test_tui_workspace_screens.py::test_workspace_view_refresh_button_reads_external_workspace_created_after_enter`, where the table assertion ran before the UI reflected the externally created workspace.
- **CI repair:** `tests/test_tui_workspace_screens.py::_wait_for_tui_condition` and the updated workspace refresh test wait for `DataTable.row_count == 1` before asserting the `external-a` row, aligning the regression with `core/tui/screens/workspace_screen.py` refresh behavior.
- **Verification handling:** Step 6 cites prior Tester-passed verification and existing planned acceptance/coverage references; it intentionally does not run `pytest`, wheel/build, coverage, or any command that can create artifacts.
- **Artifact handling:** no new validation artifacts are generated by Step 6; generated/cache/build/runtime cleanup boundaries remain governed by `Architecture/MaintainerRepositoryReading.md`, and this closure does not claim any destructive cleanup outside the two tracking documents.

## Step 5 Documentation Alignment Notes

**Review date:** 2026-06-08. Documentation alignment details are recorded in `Architecture/DebugReviewTaskLedger.md#step-5-documentation-alignment-pass`.

- README and README.zh-CN now describe the Step 4 upper-left `≡ 菜单 (M)` affordance, uppercase `M`/`P`/`Q` policy, targeted refresh inventory, TUI preview artifact workflow, Wiki publication evidence, TUI title/string inventory boundary, and remaining external/approval-gated items.
- The targeted refresh wording remains limited to workspace/log/dashboard/tool/dialog surfaces and explicitly excludes a broad watcher or polling implementation.
- The TUI preview wording states that `scripts/tui_preview_artifact.py` produces a text artifact by default and does not record user approval or create an image artifact by itself.
- The Wiki wording records commit `d6a1e11` as publication evidence while preserving the boundary that local tests cannot verify remote availability or future remote edits.
- No unsupported completion claim was added for OS-level IME proof, full English-only title replacement, full external OpenCode comparison/alignment, broad whole-repo refactor, or user-approved visual redesign.

## Step 7 Artifact Generation and Cleanup Notes

**Review date:** 2026-06-08. Artifact evidence is recorded in `Architecture/DebugReviewTaskLedger.md#step-7-artifact-generation-and-content-relevance-check`.

- **TUI preview artifact workflow:** `scripts/tui_preview_artifact.py` was used to generate `C:\Users\D2O\Downloads\SuperMedicine_TUI_preview.txt` with `--project-root D:\GIT\SuperMedicine`. The artifact is a bounded text preview deliverable outside the repository.
- **Artifact content boundary:** the generated preview records dry-run shell/status/menu/targeted-refresh metadata and explicitly says user approval has **NOT** been recorded. It does not claim image generation or user-approved redesign.
- **Package/build relevance:** `pyproject.toml` only installs the `supermedicine` CLI entry point and runtime package data; `setup.py` handles installer wrapper distribution post-processing. The preview generator remains a repository utility script under `scripts/`, so no package script/build configuration change is needed for the current requirement.
- **Cleanup:** repository build/cache/runtime artifact scan found no `build/`, `dist/`, `*.egg-info`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, or `*.pyc` cleanup targets. Local runtime `.supermedicine/` artifacts were cleaned from the repository working tree; the Downloads preview artifact was intentionally preserved as the required deliverable.

## Step 10 Final Report Closure Notes

**Review date:** 2026-06-08. Final 18-item closure is recorded in `Architecture/DebugReviewTaskLedger.md#step-10-final-18-item-implementation-report`.

- The Step 10 ledger section is the authoritative final report for all 18 `Debug.txt` items and cross-references original requirements, actual code evidence, executable/manual evidence, docs evidence, Wiki/remote evidence, artifact evidence where relevant, local validation result, remote validation result, and remaining risks/boundaries.
- Latest local validation evidence is recorded as: `ruff` PASS, `mypy` PASS, build PASS, and `pytest` `859 passed, 4 skipped`.
- Latest GitHub Wiki evidence is commit `e5172dc1cdd7dc328a61f117f6d309a000d32771`, with remote Wiki pages accessible. Earlier `d6a1e11` notes remain historical Step 4 publication evidence only.
- GitHub Actions CI status was not queried because `gh` is unavailable; local validation is substitute evidence and must not be described as remote CI success.
- The TUI preview deliverable remains `C:\Users\D2O\Downloads\SuperMedicine_TUI_preview.txt`; it is text-only and records no user approval or image/screenshot claim.
- Main repository changes remain local/uncommitted unless separately requested. No commit/push is authorized by this plan closure.
