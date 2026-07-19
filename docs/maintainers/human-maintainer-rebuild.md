# Feature-Preserving Human Maintainer Rebuild

This is the authoritative maintenance record for the fixed-baseline rebuild
from `49ac6f88264fe4e06090af39154f2a089a18d8ef`. It complements the immutable
[Feature Parity Baseline](feature-parity.md); it does not replace the machine
contract in `feature_manifest.json`.

## Outcome and scope

PR-00 through PR-10 established the inventory, repaired preserved paths,
introduced shared application services, consolidated RAG/Harness/Multi-Agent,
adapters, standards, research tools and UI implementations, hardened Web and
Desktop, unified installers/builders, and converged core files and long
orchestrators. PR-11 owns final documentation, clean-install/artifact gates and
the no-overwrite release policy.

No baseline Feature ID was removed. The reviewed set grew from 158 to 185 only
because 27 existing or required preserved surfaces gained explicit contracts:
the Multi-Agent CLI switch (3 IDs), OpenTUI pages/interactions (23 IDs), and the
versioned health route (1 ID). The complete additions are stored in
`feature_manifest.json`; `baseline_feature_ids` remains the immutable 158-ID
set.

## Supported surfaces and defaults

| Surface | Maintained contract |
| --- | --- |
| CLI | 43 command IDs through the shared application services. |
| OpenTUI | 13 pages, real JSONL service bridge, keyboard, mouse, scroll, resize, focus, restore, cancellation, Unicode and error recovery. |
| Web/Desktop | 46 HTTP/WebSocket routes, consistent result/error schema, bound-socket startup, health polling, persistent user storage and executable self-test. |
| Adapters | Standalone, OpenCode and Claude Code use the adapter application service. |
| RAG/Harness | Required and default-enabled; local RAG and checkpoint paths fail closed when unavailable. |
| Multi-Agent | Optional persisted switch; disabled uses the single-agent path, enabled executes Alpha/Beta/Gamma/Delta with resumable checkpoints. |
| Plugins/tools | Every packaged manifest and `provides` ID is discovered from source and clean Wheel installs. |
| Research standards | AMA, Vancouver, CONSORT, STROBE, PRISMA and STARD remain distinct public contracts. |
| Install/release | Source installer, GUI installer, application/GUI/installer EXEs, Wheel/sdist and release ZIP share version `0.4.2b0` / `Beta0.4.2`. |

Optional capabilities remain explicit: OpenTUI requires Bun, Web/Desktop use
their extras, the formal R survival backend requires R plus `survival`, and
OpenCode/Claude Code adapters are not required for the standalone core.

## Structural result

| Metric | Fixed baseline | Final source | Delta |
| --- | ---: | ---: | ---: |
| Production Python files | 182 | 164 | -18 |
| Raw production Python LOC | 38,897 | 41,223 | +2,326 |
| Effective production Python LOC | 33,270 | 35,434 | +2,164 |
| Functions/methods | 1,608 | 1,828 | +220 |
| Public top-level symbols | 472 | 528 | +56 |
| Functions over 60 lines | 78 | 79 | +1 |
| Functions over 100 lines | 28 | 18 | -10 |
| Top-level dependency edges | 17 | 15 | -2 |
| Feature IDs | 158 | 185 | +27 classified preserved surfaces |

LOC and symbol growth comes from previously missing service, error, security,
interactive and artifact contracts; it was not used to add unrelated product
features. The main maintainability gains are fewer implementation files,
ten fewer functions over 100 lines, two fewer dependency edges, and explicit
application boundaries.

PR-10 implementation-file budgets are: Workspace 4, Log 3, Paper 3, LLM 5,
Database 3, Installer 4, Agents 3, Adapters 4, TUI 10, Figure 5, Harness 2 and
Medical standards 8. Legacy module paths use runtime aliases plus `.pyi`
facades, not duplicate implementations.

## Deleted implementation migration map

| Deleted files | Preserved destination |
| --- | --- |
| `agents/{alpha,base,beta,delta,gamma}_agent.py`, `state_machine.py` | `agents/roles.py`, `orchestrator.py`, `checkpoint.py` |
| `adapters/{opencode,standalone}/__init__.py` | Narrow package discovery and shared adapter contracts |
| `core/llm_providers/openrouter.py` | `core/llm_providers/base.py` plus typed compatibility facade |
| `core/log_severity.py` | `core/log_report_models.py` plus typed compatibility facade |
| `core/paper_import/errors.py`, `models.py` | `core/paper_import/contracts.py` plus typed facades |
| `core/workspace_tool_templates.py` | `core/workspace_tool_spec.py` plus typed facade |
| Eleven `core/tui` helper modules | `core/tui/support.py` plus runtime/typed facades |
| Sixteen `core/tui/screens` modules | `core_views.py`, `workspace_views.py`, `research_views.py`, `system_views.py` plus facades |
| `plugins/rag/interface.py`, `local_provider.py` | `plugins/rag/providers.py` |
| `plugins/harness/checkpoint_verifier.py` | `plugins/harness/main.py`, `monitor.py`, shared `agents/checkpoint.py` |
| `plugins/figure/{check,layout,qa,style}.py` | `audit.py`, `presentation.py` and package aliases |
| `plugins/standards/medical_citation/vancouver_format.py` | `ama_format.py` plus typed compatibility facade |

## Known-defect disposition (36/36)

Only the permitted statuses are used. Each row names its primary executable
evidence; the full suite provides the surrounding regression coverage.

| # | Preserved defect/path | Status | Primary evidence |
| ---: | --- | --- | --- |
| 1 | Fixed audit baseline ancestry | FIXED | `tests/feature_contract/test_manifest_contract.py` |
| 2 | Invalid HTTP client dependency | FIXED | `tests/test_web_self_evolution.py` |
| 3 | Colliding Kernel task IDs | FIXED | `tests/test_kernel_full.py` |
| 4 | Web 2xx/4xx/5xx mapping | FIXED | `test_chat_missing_message_returns_http_client_error`, `test_unexpected_api_failure_returns_http_server_error` |
| 5 | Persisted API-key/config permissions | FIXED | `tests/test_secure_config_permissions.py` |
| 6 | Provider collection schema | FIXED | `test_llm_provider_list_uses_frontend_provider_schema` |
| 7 | Placeholder experiment details | FIXED | `test_experiment_detail_endpoint_returns_persisted_session_details` |
| 8 | Wheel plugin resources/discovery | FIXED | `scripts/ci/smoke_wheel_install.py`, `tests/test_plugin_registry.py` |
| 9 | RAG required/default enabled | FIXED | `tests/feature_contract/test_runtime_contract.py` |
| 10 | Harness required/default enabled | FIXED | `tests/feature_contract/test_runtime_contract.py` |
| 11 | Multi-Agent enabled four-role path | FIXED | `test_enabled_multi_agent_pipeline_executes_all_four_roles` |
| 12 | Multi-Agent disabled fallback | FIXED | `test_cli_parser_can_enable_and_disable_multi_agent` |
| 13 | Multi-Agent checkpoint resume | FIXED | `tests/test_checkpoint_full.py` |
| 14 | Adapter duplicated permission wiring | REPLACED_EQUIVALENT | `test_platform_adapters_depend_on_application_services_not_permission_or_kernel` |
| 15 | CLI duplicated business wiring | REPLACED_EQUIVALENT | `tests/test_application_service_boundaries.py` |
| 16 | TUI direct store/runtime construction | REPLACED_EQUIVALENT | `test_ui_adapters_do_not_construct_internal_stores_or_permission_runtime` |
| 17 | Web duplicated business wiring | REPLACED_EQUIVALENT | `test_web_routes_delegate_status_and_diagnostics_to_application_services` |
| 18 | Oversized Web app factory | REPLACED_EQUIVALENT | `tests/test_core_convergence.py` |
| 19 | Oversized LLM chat path | REPLACED_EQUIVALENT | `tests/test_core_convergence.py` |
| 20 | OpenTUI static shell/demo records | FIXED | `test_opentui_catalog_uses_real_services_without_demo_records` |
| 21 | OpenTUI keyboard/focus behavior | FIXED | `test_opentui_feature_contract_covers_pages_and_interactions` |
| 22 | OpenTUI mouse behavior | FIXED | `test_interaction_matrix_helper_uses_real_runtime_mode` |
| 23 | OpenTUI scroll behavior | FIXED | `test_interaction_matrix_helper_uses_real_runtime_mode` |
| 24 | OpenTUI resize behavior | FIXED | `test_interaction_matrix_helper_uses_real_runtime_mode` |
| 25 | OpenTUI state restoration | FIXED | `test_opentui_activation_persists_workspace_and_provider_state` |
| 26 | OpenTUI Unicode/long text | FIXED | `test_opentui_feature_contract_covers_pages_and_interactions` |
| 27 | OpenTUI error/cancellation recovery | FIXED | `test_service_bridge_jsonl_handles_multiple_requests` |
| 28 | Desktop bundle-root persistence | FIXED | `test_desktop_paths_use_user_storage_not_bundle_root` |
| 29 | Desktop logging outside `_MEIPASS` | FIXED | `test_desktop_self_test_checks_backend_health_frontend_and_storage` |
| 30 | Desktop health/startup propagation | FIXED | `test_desktop_self_test_checks_backend_health_frontend_and_storage` |
| 31 | Desktop port TOCTOU | FIXED | `test_desktop_server_reserves_bound_loopback_socket` |
| 32 | Backend exit/timeout propagation | FIXED | `tests/test_desktop_runtime.py` |
| 33 | WebView2 actionable diagnosis | FIXED | `test_gui_entry_self_test_is_machine_readable_from_non_repo_directory` |
| 34 | Frozen installer manifest/root lookup | FIXED | `test_gui_installer_resolves_manifest_from_pyinstaller_bundle` |
| 35 | Installer partial-copy rollback | FIXED | `test_install_service_rolls_back_files_created_before_copy_failure` |
| 36 | Same-version overwrite and artifact-only CI | FIXED | `test_release_publish_refuses_to_overwrite_an_existing_version`, `test_packaging_ci_runs_real_artifact_self_tests_and_clean_wheel_install` |

## Release gate

Run from a clean checkout:

```powershell
python -m pytest -q
python -m mypy core permission cli plugins agents adapters installer
python -m ruff check .
python -m build
npm run opentui:smoke
```

Then clean-install the Wheel, run `scripts/ci/smoke_wheel_install.py`, run the
application dry-run and both executable `--self-test` contracts, and build the
release ZIP. The publish job fails if either the version tag or Release already
exists; it never edits, deletes or clobbers a same-version release.

Platform-specific evidence that cannot be produced on the current runner must
remain explicitly unverified: native POSIX permission modes, a machine with an
actually available R `survival` backend, live PubMed access, and interactive
Windows WebView2 rendering beyond the executable self-test contract.
