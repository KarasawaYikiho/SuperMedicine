# Function Map / Repository Callable Inventory

> Authoritative maintainer location: this root-level `FUNCTION_MAP.md` is the
> single trackable FunctionMap artifact for the repository. Do not create
> case-conflicting `FunctionMap.md` or duplicate `docs/function-map.md` copies.
> This document is
> generated from Python AST static analysis and must not include configuration
> values, environment values, API keys, tokens, passwords, private endpoints,
> raw logs, or other secret material.

## Security and Review Notes

- This inventory is for navigation, impact review, and verification support only;
  it does not grant permission to execute listed callables.
- External side-effect hints are static heuristics. Review the implementation and
  permission checks before running commands, network calls, mutations, or adapter
  tools.
- Regenerate or update this file only from repository source, never from runtime
  logs or local configuration snapshots.

## Static/Dynamic Analysis Limitations

- Callers and callees are static-analysis-visible relationships inferred from `ast.Call` names and attribute calls; same-name functions, alias imports, closures, monkeypatching, and runtime rebinding can create ambiguity.
- CLI dispatch, Textual callbacks, decorators, pytest fixtures, plugins, reflection, string-based command maps, registries, and runtime dynamic imports may introduce additional runtime relationships that static AST analysis cannot fully reconstruct.
- Textual `compose`, `on_*`, `action_*`, `watch_*`, pytest fixtures, decorated callables, plugin registration hooks, and adapter callbacks are marked as potentially framework/runtime invoked where visible.

## Maintainer Curated Function Map

This section is the maintainer-facing project map. It integrates the current
`Architecture/MaintainerRepositoryReading.md` reading pass and keeps the older
AST callable inventory below as a static appendix rather than a raw execution
log. It intentionally omits local runtime state, private scratch notes, raw logs,
environment values, tokens, API keys, generated build outputs, and ignored
runtime directories.

### Repository scope and release hygiene

- Tracked reading coverage used as source: 242 tracked files from the roadmap
  inventory, including self-evolution source and regression-test files:
  `core/self_evolution.py`, `tests/test_self_evolution.py`, and
  `tests/test_self_evolution_cli.py`.
- Excluded inputs: caches, `build/`, `dist/`, egg-info, runtime
  `.supermedicine/`, binary/release artifacts, ignored scratch docs, raw audit
  notes, and private/transient local artifacts.
- Commit/upload-eligible output: this curated function map and the maintained
  architecture reports. Do not promote raw logs or private local analysis into
  this file.

### Top-level execution and installation surfaces

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `Cli.py` | `_configure_stdio_errors`, `_log_json`, `_configure_cli_logging`, workspace/experience/paper/self-evolution helper converters, `CLI`, `main` | Compatibility CLI entry point and user command router for init/status/test/run/workspace/paper/experience/log/permission/tool flows. | Receives argparse-style command parameters and user paths; emits console text, JSON responses, workspace records, plugin/task results, and structured errors. | Console I/O, filesystem writes, subprocess/release-helper calls; depends on `core`, `permission`, `plugins`, installer helpers, and redaction/logging utilities. |
| `Install.py`, `install.py`, `installer/entrypoint.py` | `ExistingInstallEvidence`, `ExistingInstallDetection`, `detect_existing_install`, `write_install_record`, `write_llm_config`, `detect_platform`, `init_config`, `main` plus config merge/provider normalization helpers | Installation/bootstrap entry points, existing-install handling, install-record refresh, and default runtime configuration creation. | Install flags, existing-install policy choices, provider/environment choices, filesystem locations; outputs config files, secret-free install records, installer messages, and safe exits for scripted ambiguity. | Filesystem mutation for confirmed install/update/uninstall paths, possible PATH/platform probing; existing-install detection itself is read-only; depends on `core`, `permission`, `Uninstall`, `urllib`, and host filesystem permissions. |
| `Uninstall.py` | `RemovalCandidate`, `Residual`, `_redact_text`, `_redact_data`, `_safe_display`, `_is_within`, `_load_install_record`, `_iter_recorded_paths`, `collect_removal_candidates`, `uninstall`, `main` | Safe uninstall and residual cleanup discovery. | Install records/manifests and user confirmation flags; outputs removal plans, console status, and structured residuals. | Filesystem deletion when confirmed, subprocess/registry probing on supported hosts, path containment/redaction. |
| `installer/exe_release.py` | `ExeReleaseError`, `resolve_desktop_dir`, `resolve_exe_path`, `validate_release_payload_root`, `iter_release_payload_files`, `release_exe_to_desktop` | Local executable release payload validation/copy support. | Release payload roots and target filename; outputs copied payload/exe paths or validation errors. | Filesystem traversal/copy; excludes generated/cache/private payloads by rule. |

Call/data flow: console command -> `Cli.py`/installer compatibility wrapper -> existing-install detection/policy branch when installing -> core service/plugin/permission layer -> structured result/log/audit/console output. Install/uninstall/release helpers are host-facing and must keep path safety/redaction aligned with `permission` and `core.path_safety`; install records must not contain API keys or other secrets.

### Core kernel, configuration, events, sessions, and logging

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/kernel.py` | `Kernel`, `execute_task`, `emit`, properties for config/LLM/event/plugin/session/permission/checkpoint managers | Microkernel composition point and task execution coordinator. | User/task dictionaries and plugin/action names; outputs plugin results, emitted events, and structured kernel responses. | Event/plugin dispatch, permission checks, optional network via providers; depends on `ConfigCenter`, `LLMConfigManager`, `EventBus`, `PluginRegistry`, `SessionManager`, `PermissionEngine`, `CheckpointManager`. |
| `core/config_center.py` | `ConfigCenter`, `_redact_llm_providers`, `_safe_runtime_slug`, `get`, `set`, `save`, `safe_all`, `diagnostics`, `get_llm_config`, `get_experiment_guide_config` | YAML configuration management with safe LLM/provider diagnostics. | YAML files plus `SM_*` overrides; outputs config values, redacted snapshots, diagnostics. | Filesystem read/write; must not leak secrets. Depends on `yaml`, `permission`, `logging`. |
| `core/event_bus.py` | `Subscription`, `EventBus.subscribe`, `unsubscribe`, `publish` | In-process pub/sub for runtime events. | Event names/payloads and callbacks; outputs callback invocations. | Callback execution side effects are delegated to subscribers; uses logging/UUIDs. |
| `core/session_manager.py` | `Session`, `SessionManager.create`, `get`, `cleanup_expired`, `list_active` | Short-lived runtime session storage. | Session payloads and TTL windows; outputs session IDs/records. | In-memory state only; no persistent storage. |
| `core/log_report.py` | `LogReport`, `LogStorageLocations`, `LogReportStore`, `LogReportLoggingHandler`, `normalize_log_severity`, `detect_log_severity`, `format_log_message`, `resolve_log_storage_locations`, `configure_tui_log_storage`, `append_tui_stream_output` | Safe JSONL-backed log/report storage and TUI log streaming. | Log messages, severities, session IDs; outputs sanitized log records, summaries, and files. | Filesystem writes, thread/logging handler effects; depends on redaction, timestamps, path handling. |
| `core/redaction.py` | `redact_sensitive`, `redact_path_for_display` and helper detectors | Central sensitive-value/path redaction. | Nested data/text/URLs/paths; outputs sanitized equivalents. | No external side effects; cross-cutting dependency for adapters, config, logs, uninstall, LLM errors. |
| `core/serialization.py`, `core/time_utils.py`, `core/token_tracker.py` | `json_ready`, `utc_now`, `utc_now_datetime`, `TokenRecord`, `TokenTracker.record/summary` | Shared serialization/time/token accounting support. | Arbitrary dataclass/path/time data and token usage records; outputs JSON-safe values/timestamps/usage summaries. | `TokenTracker` persists JSONL; serialization/time helpers are pure. |

Call/data flow: `Kernel.__init__` wires service singletons; CLI/TUI/plugins call kernel properties and `execute_task`; plugin results and log/audit events flow back through event/log/session helpers. Redaction and JSON serialization are cross-module safety dependencies for anything leaving the process.

### Governance, permissions, and path safety

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `permission/access_mode.py` | `AccessMode`, `FileAccessOperation`, `AccessDecisionStatus`, `AccessDecision`, `AccessModePolicy`, `normalize_access_mode`, `normalize_file_operation`, `insufficient_permission_helper` | Conservative/sandbox/full access-mode model for file operations. | Mode strings, file operation names, roots, and confirmation context; outputs allow/deny/prompt decisions. | Pure policy calculation; informs CLI, TUI, self-evolution, workspace tools. |
| `permission/policy.py` | `PermissionResult`, `PermissionRule`, `HardLimits`, `PermissionPolicy`, `default_policy_path`, `ensure_default_policy`, `matches`, `check` | YAML-backed agent/action/resource permission policy. | Agent/action/resource triples and policy dictionaries; outputs allowed/denied results with reasons. | May bootstrap default policy file; depends on package resources, path normalization, fnmatch. |
| `permission/engine.py` | `PermissionEngine.default_policy_path`, `_load_policies`, `check` | Runtime permission engine over loaded policy. | Agent/action/resource checks; outputs `PermissionResult`. | Reads YAML policies, may audit through configured logger. |
| `permission/audit.py` | `AuditLogger.for_project`, `storage_path`, `log`, `restrict_file_permissions` | Permission/audit JSONL persistence. | Permission decisions/events; outputs audit lines. | Filesystem writes with restricted file permissions when possible. |
| `permission/prompt_generator.py` | `PromptGenerator.generate_prefix`, `generate_rejection_templates`, `SELF_EVOLUTION_GUIDANCE` | Governance prompt text for agents/tools, including self-evolution constraints. | Role/task context; outputs prompt prefixes/templates. | Pure text generation. |
| `core/path_safety.py` | `validate_path_value`, `resolve_project_root`, `validate_path_in_project_root`, `is_protected_path`, path safety errors | Project-root containment and protected-path checks. | User/tool candidate paths and project roots; outputs resolved safe paths or typed errors. | Pure path validation; called before adapter, workspace, and self-evolution writes. |
| `core/operation_guard.py` | `DangerousOperationDenied`, `OperationAuditRecord`, `OperationAuthorization`, `authorize_dangerous_operation` | Guardrail for high-risk operations needing explicit authorization. | Permission engine, agent/action/resource, risk context; outputs authorization or denial. | Produces audit context; no direct mutation beyond delegated audit/logging. |

Call/data flow: action request -> path/resource normalization -> access-mode/policy engine check -> optional prompt/authorization -> audit/log record -> allowed handler. New tool or plugin side effects should enter through this chain rather than bypassing it.

### Agents and orchestration

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `agents/base_agent.py` | `BaseAgent.agent_id`, `role`, `describe_state`, `execute` | Abstract agent contract. | Task dictionaries; outputs agent results. | Abstract/no direct side effects. |
| `agents/state_machine.py` | `TaskState`, `StateMachine.transition`, `can_resume`, `snapshot` | Task lifecycle states: planning, dispatch, running, verifying, retry, completed. | Task IDs and transition events; outputs state snapshots and resume decisions. | In-memory history; depends on time utilities. |
| `agents/checkpoint.py` | `sanitize_for_checkpoint`, `CheckpointManager.save`, `load`, `load_latest`, `get_latest_step`, `recovery_report` | Redacted checkpoint persistence and recovery support. | Task/stage payloads; outputs sanitized checkpoint files and recovery reports. | Filesystem JSON writes; strips sensitive keys before persistence. |
| `agents/orchestrator.py` | `Orchestrator.register_agent`, `get_agent`, `list_agents`, `describe`, `dispatch`, `recovery_report` | Agent registry and dispatch coordinator. | Agent IDs and task dictionaries; outputs agent execution results and checkpointed stages. | Checkpoint writes and state transitions; depends on `BaseAgent`, `CheckpointManager`, `StateMachine`. |

Call/data flow: adapter/TUI/CLI task request -> `Orchestrator.dispatch` -> state transition/checkpoint -> concrete agent `execute` -> checkpoint/recovery output. Sensitive payloads must pass through `sanitize_for_checkpoint` before disk.

### Platform adapters, OpenCode/Claude anchors, skills, and tools

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `adapters/__init__.py` | `AdapterRegistration.as_dict`, `list_adapter_registrations`, `get_adapter_registration`, `default_adapter_registration`, `__getattr__` | Static adapter registry and lazy optional adapter imports. | Platform names and optional-inclusion flag; outputs adapter metadata or lazily imported modules. | Lazy imports may reveal optional runtime availability; keeps core import lightweight. |
| `adapters/base_adapter.py` | `BaseAdapter`, `platform_name`, `tool_call`, `skill_load`, `subagent_dispatch`, `_execute_permissioned_tool_call`, `_tool_bash/read/write/edit/glob/grep`, `_normalize_command`, `_resolve_sandbox_path`, `_resource_error` | Shared permissioned/sandboxed tool-call implementation. | Tool IDs and params; outputs tool strings or structured dict errors/results. | Subprocess execution for bash; filesystem read/write/edit/glob/grep; enforces permission engine, project-root sandbox, timeout, and redaction. |
| `adapters/standalone/adapter.py` | `StandaloneAdapter.registration`, `tool_call`, `_tool_skill`, `_tool_task`, `skill_load`, `subagent_dispatch` | Self-contained adapter with inherited local tools and explicit skill/task contract metadata. | Tool/skill/task params; outputs local tool results or unavailable/metadata responses. | Uses inherited filesystem/subprocess handlers through policy checks; no external platform runtime required. |
| `adapters/opencode/adapter.py` | `OpenCodeAdapter.registration`, `capabilities`, `tool_call`, `_tool_skill`, `_tool_task`, `skill_load`, `subagent_dispatch` | Optional OpenCode adapter metadata, skill file loading, and orchestrator-backed task dispatch when injected. | OpenCode-like tool IDs, skill names, agent IDs, task dictionaries; outputs capability maps, Markdown skill content/metadata, or orchestrator dispatch result. | Filesystem reads for tracked skill/agent docs; tool side effects delegated through `BaseAdapter`; no native OpenCode runtime bridge claimed without injected orchestrator. |
| `adapters/claude_code/adapter.py` | `ClaudeCodeAdapter.registration`, `capabilities`, `tool_call`, `skill_load`, `subagent_dispatch`, `_invoke`, `_runtime_status`, `_permission_denied` | Minimal optional Claude Code CLI adapter and capability reporter. | `invoke` prompts/timeouts, skill/task requests, permission context; outputs runtime status or `claude --print` result/error. | Permission-checked subprocess call to local `claude`; redacts prompt/error material; native Claude skill loading and subagent dispatch are explicitly unavailable. |
| `adapters/claude_code/SKILL.md`, `adapters/opencode/plugin.json`, `adapters/opencode/skills/*.md`, `adapters/opencode/agents/*.md` | Declarative platform skill/agent metadata documents | Human/platform-facing optional adapter anchors for SuperMedicine workflows. | Skill/agent metadata and instructions; outputs loaded documentation/metadata when adapter reads them. | No runtime side effects when read; must stay aligned with adapter capabilities and not overclaim external platform features. |

Call/data flow: platform/tool request -> adapter registry/lazy import -> adapter capability/permission check -> local handler, subprocess, filesystem handler, skill doc read, or orchestrator dispatch -> redacted structured result. Adapter security boundaries are cross-module dependencies on `permission`, `core.path_safety`, and `core.redaction`.

### Plugin registry and plugin contracts

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/plugin_registry.py` | `PluginRegistry.discover`, `diagnostics`, `get_meta`, `get`, `list_plugins` | Discovers `plugin.yaml` metadata and executable plugin modules. | Plugin root paths and metadata YAML; outputs registry maps, plugin metadata, and plugin instances. | Filesystem scans/imports; depends on `plugins.base_plugin` and `yaml`. |
| `plugins/base_plugin.py` | `PluginMeta`, `BasePlugin.meta/name/execute/health_check`, `plugin_result`, `_direct_execution_denied` | Common plugin metadata and execution contract. | Plugin metadata dictionaries and action params; outputs normalized plugin result dictionaries. | Dynamic entry loading/inspection; direct execution protection. |
| `plugins/*/plugin.yaml`, `plugins/tools/*/tool.yaml` | Declarative plugin/tool manifests | Registry and tool metadata. | YAML fields such as name/version/type/language/entry; outputs metadata for registry/UI. | No side effects when read; drift risk if entry points move. |

Call/data flow: `Kernel`/CLI requests plugin action -> `PluginRegistry` discovers metadata and loads plugin -> plugin `execute(action, params)` returns `plugin_result` dictionaries -> caller logs/displays result. Plugin side effects must remain permissioned by kernel/permission contexts.

### Medical writing, citation, and Nature/Citation-skill equivalents

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `plugins/standards/medical_writing/checklist_base.py` | `ChecklistItemBase`, `MedicalClaim`, `ChecklistBase`, `annotate_medical_claims`, `enforce_medical_accuracy` | Shared medical-writing checklist and claim/citation audit primitives. | Manuscript text and optional claim/citation metadata; outputs checklist items, claim annotations, human-review issues. | Pure checks; relies on caller to handle clinical review boundaries. |
| `plugins/standards/medical_writing/checklists.py` | `ChecklistItem`, `Checklist`, `get_consort_checklist`, `get_strobe_checklist`, `check` | CONSORT/STROBE checklist construction and validation. | Manuscript text; outputs compliance items/reports. | Pure validation. |
| `plugins/standards/medical_writing/prisma.py`, `stard.py` | `PRISMAChecklist`, `STARDChecklist`, `_init_items` | PRISMA/STARD checklist definitions. | Manuscript text via inherited `ChecklistBase.check`; outputs compliance report/items. | Pure validation; references tracked Markdown checklist docs. |
| `plugins/standards/medical_writing/main.py` | `execute`, `_checklist_for_action`, `_base_metadata`, `_required_text`, `_claims_from_params` | Plugin entry for medical writing standards. | Actions such as checklist runs and manuscript/claim params; outputs plugin result with metadata/issues. | No direct network/filesystem mutation expected; depends on plugin contract and checklist modules. |
| `plugins/standards/medical_citation/utils.py` | `JournalArticle`, `Book`, `CitationSource`, `CitationValidationResult`, `validate_source_id`, `citation_state_from_validation`, `citation_provenance_from_source`, `format_authors`, `format_journal_base`, `format_book_base` | Citation data model, source validation, provenance, and shared formatting. | Reference/source dictionaries and article/book fields; outputs validation states, provenance, formatted author/base strings. | Pure formatting/validation. |
| `plugins/standards/medical_citation/ama_format.py`, `vancouver_format.py` | `AMAFormatter.format_journal/format_book`, `VancouverFormatter.format_journal/format_book` | AMA and Vancouver reference formatting. | `JournalArticle`/`Book`; outputs formatted citation strings. | Pure formatting. |
| `plugins/standards/medical_citation/main.py` | `execute`, `_execute_citation`, `_sources_from_params`, `_source_from_dict`, `_reference_from_source_dict`, `_journal_from_dict`, `_book_from_dict` | Citation plugin entry for formatting/validation. | Citation action, style, sources/reference params; outputs structured formatted references, validation/provenance/issues. | No direct mutation; depends on plugin contract and citation utilities. |

Current status for requested skill names:

- **Nature-Skill**: absent by exact implementation/package/file name. Existing
  SuperMedicine-native anchors are medical-writing checklist modules, tracked
  guideline references, `adapters/opencode/skills/medical-writing.md`, and
  medical writer/agent role docs. Gap versus a conventional installed
  Nature-style skill: no installable skill package with manuscript-spine section
  generation, journal-specific style transformations, cover-letter workflow, or
  end-to-end Nature submission checks is present.
- **Citation-Check-Skill**: absent by exact implementation/package/file name.
  Existing anchors are `plugins/standards/medical_citation/*`, medical-writing
  claim/citation audit helpers, and `adapters/opencode/skills/medical-citation.md`.
  Gap versus a conventional installed citation-check skill: no external-library
  crossref/PMID verification loop, no full bibliography reconciliation against
  manuscript in-text citations, and no installed skill runtime with persistent
  citation-check state is present.

### Paper import, PaperSpine status, RAG, workspace, and knowledge flows

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/paper_import/models.py` | `PaperMetadata`, `PaperImportResult` | Paper metadata/result data structures. | File/identifier metadata; outputs dataclass records. | Pure data model. |
| `core/paper_import/errors.py` | `PaperImportError`, `UnsupportedPaperFormatError`, `MissingPaperSourceError`, `PaperMetadataError` | Typed paper import errors. | Error context; outputs exception types. | No side effects. |
| `core/paper_import/enrichment.py` | `PaperMetadataProvider`, `LocalMockMetadataProvider`, `PaperEnrichmentResult`, `PaperEnricher.enrich`, `_apply_provider_fields` | Optional metadata enrichment with permission-aware provider boundary. | DOI/PMID/title metadata and provider responses; outputs enriched `PaperMetadata`/issues. | Provider calls may be networked depending on implementation; permission constants define action/agent. |
| `core/paper_import/importer.py` | `PaperImporter.import_file`, `list_papers`, `get_paper`, `update_paper_metadata`, `save_paper_metadata`, normalization helpers | Workspace paper file import and metadata persistence. | Source file paths and metadata dictionaries; outputs `PaperImportResult`, copied records, JSON metadata. | Filesystem copy/write/read; path safety and schema drift are maintenance concerns. |
| `plugins/rag/interface.py` | `RAGProviderConfig`, `RAGProviderError` variants, `make_rag_result`, `RAGProvider`, `EmptyRAGProvider` | Provider contract and normalized RAG result shape. | Query/config/provider metadata; outputs result dictionaries or typed errors. | Provider-specific side effects only. |
| `plugins/rag/local_provider.py` | `LocalRAGProvider.add_document/query/store_context/retrieve_context`, `MockExternalVectorStoreProvider` | Local text index and context persistence. | Documents, query strings, context keys/values; outputs ranked local results/context values. | Filesystem JSON/index/context writes; key/path sanitization required. |
| `plugins/rag/pubmed_provider.py` | `PubmedRAGProvider.connect/query/store_context/retrieve_context`, `_search`, `_fetch`, `_parse_articles`, `_get_json` | Permissioned PubMed-backed retrieval. | Query/scope/API config; outputs normalized article/result dictionaries. | Network calls to PubMed endpoints when permissioned; parses JSON/XML. |
| `plugins/rag/main.py` | `execute`, `_execute_query`, `_execute_context_store`, `_execute_context_retrieve`, `_provider_config`, `_seed_local_documents` | RAG plugin entry point. | Query/context actions and provider params; outputs plugin results. | May create temp/local storage and query provider. |
| `core/workspace.py` | `WorkspaceMetadata`, `WorkspaceInfo`, `WorkspaceManager`, `validate_workspace_id`, `initialize_workspace`, `list_workspaces`, `save_recent_selection` | Workspace identity and storage layout. | Workspace IDs/labels/root paths; outputs metadata/info and recent selection. | Filesystem directory/YAML writes. |
| `core/workspace_tools.py` | `ToolManifest`, `ToolInvocationPlan`, `ToolImportCandidate`, validation/import/invocation helpers, `build_tool_authoring_llm_context` | Workspace-local Python/R tool authoring/import/invocation support. | Tool IDs/languages/manifests/candidate source; outputs validated manifests, import candidates, invocation plans. | Filesystem reads/writes/copies; depends on path safety and permission checks. |

**PaperSpine status**: absent by exact implementation/package/workflow name.
Existing SuperMedicine-native anchors are `core/paper_import/*`, workspace paper
controllers/screens, RAG providers, medical-writing/citation plugins, and
OpenCode skill/agent docs. Gap versus a conventional installed PaperSpine effect:
no named paper-spine package, no canonical manuscript spine data model, no
one-command paper-to-outline-to-citation pipeline, and no persistent installed
skill state for paper planning are present.

Call/data flow: workspace path/metadata -> paper import/copy/metadata JSON -> optional enrichment/RAG evidence -> TUI/CLI paper screens and medical-writing/citation plugins. External metadata and PubMed calls are optional and must remain permissioned/degradable.

### Experiment guide, scientific tools, and local analysis plugins

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/experiment_protocols.py` | `ExperimentProtocolConfigError`, `ExperimentProtocolAuthoringError`, `ExperimentInputField`, `CalculationRequest`, `ExperimentStep`, `ExperimentProtocol`, `load_protocols`, `validate_experiment_config`, `summarize_experiment_protocol`, `build_experiment_llm_context`, `draft_experiment_config_from_instruction` | Loads/validates YAML experiment protocols and builds LLM-authoring context. | Protocol config files/instructions; outputs protocol objects, summaries, authoring drafts/errors. | Filesystem config reads/writes for config dir setup; YAML/JSON parsing. |
| `core/experiment_guide.py` | `ExperimentStatus`, `KernelExecutor`, `CalculationResult`, `StepRecord`, `ExperimentSession`, `ExperimentGuide`, `build_experiment_log_event`, `append_experiment_log_event` | Guided experiment-session state machine and calculation execution boundary. | Protocol steps, sample/calculation inputs, kernel executor; outputs step records, session state, calculation results/log events. | Event/log append and kernel/plugin execution side effects. |
| `plugins/tools/experiment_wb/main.py` | `normalize_loading`, `antibody_dilution`, `execute` | Deterministic wet-bench calculation plugin. | Sample intensities, dilution params, action names; outputs normalized loading/dilution results. | Pure calculation. |
| `plugins/tools/python_stats/main.py`, `_common.py` | `execute`, descriptive/t-test/ANOVA/regression helpers, `as_float_list`, `as_float_groups`, `normal_cdf`, `required_str` | Python statistical analysis plugin. | Numeric arrays/groups/action params; outputs structured statistical summaries. | Pure calculation. |
| `plugins/tools/r_survival/*.py` | Kaplan-Meier, log-rank, Cox model action handlers and plugin `execute` | Survival-analysis plugin with optional R/rpy2-style semantics represented in Python adapter modules. | Time/event/covariate arrays; outputs survival tables/test/model summaries. | Pure/local computation; formal R support depends on optional local R extra/tooling. |
| `plugins/tools/python_data_analysis/runner.py`, `plugins/tools/r_data_analysis/runner.R`, `plugins/tools/r_template/runner.R` | External runner/template files | Workspace/local analysis runner templates. | Tool manifests and user data files; outputs analysis artifacts when invoked by tool workflow. | Subprocess or R execution may occur through caller/tool layer, not by reading these files. |

Call/data flow: protocol config -> `ExperimentGuide` session -> kernel/plugin calculation action -> deterministic tool plugin result -> session/log update. Tool imports/invocations should be guarded by `workspace_tools`, permission policy, and path safety.

### LLM management and provider clients

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/llm_providers/config.py` | `LLMProviderConfig`, `redact_secret`, `sanitize_error_message`, `sanitized_headers`, `_infer_api_format`, default provider helpers | Provider configuration normalization and secret-safe serialization. | Provider dictionaries/env vars; outputs config objects, missing-field reports, sanitized headers/errors. | Reads environment variables; redacts secrets. |
| `core/llm_providers/base.py` | `ConfiguredLLMClient`, `OpenAIClient`, `AnthropicClient`, `_openai_request`, `_parse_*_response` | HTTP provider client implementations and bounded response parsing. | Chat/completion messages/model/config; outputs provider response text/metadata or sanitized errors. | Network calls; URL/response-size safety. |
| `core/llm_providers/openrouter.py` | `OpenRouterClient` | OpenRouter-specialized configured client. | Provider config/messages; outputs LLM responses. | Network delegated to base client. |
| `core/llm_client.py` | `LLMClient`, `TrackedLLMClient`, `create_llm_client`, `create_configured_llm_client` | Abstract and configured LLM client factories with token tracking wrapper. | Provider configs and messages/prompts; outputs chat/completion results. | Network via concrete client; token accounting. |
| `core/llm_manager.py` | `LLMConfigManager.list_providers/diagnostics/add_provider/switch_provider/get_current_provider/create_client` | Runtime provider registry/selection over `ConfigCenter`. | Provider config mutations and selection commands; outputs readiness diagnostics/current provider/client. | Config writes and provider creation; must preserve redacted diagnostics. |

Call/data flow: installer/config -> `LLMProviderConfig` -> `LLMConfigManager` -> `create_configured_llm_client` -> provider HTTP client -> `TrackedLLMClient` token record -> sanitized response/error to CLI/TUI/kernel.

### TUI and workspace screens

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/tui/app.py`, `app.tcss`, `i18n.py`, `state.py`, `permissions.py` | `SuperMedicineTUI`, `launch_tui`, `build_parser`, `TUIStatus`, navigation/menu widgets, `TUIState`, `prepare_tool_action`, translations/redaction helpers | Chinese Textual workbench shell, navigation, styling, local TUI state, and permission prompts. | User key/button/input events and workspace/application state; outputs Textual widgets/status updates and core service calls. | Console/TUI I/O, stream routing, filesystem state writes; optional Textual dependency. |
| `core/tui/dialog_history.py`, `screens/chat_view.py`, `screens/dialog_screen.py` | `DialogHistoryStore`, `DialogHistoryEvent`, `ChatView`, `DialogView`, safe display helpers | Safe dialog history and chat display surfaces. | User/assistant/status text and workspace selection; outputs redacted display/history events. | Filesystem history writes; rejects raw conversation/private fields. |
| `screens/dashboard.py` | `collect_dashboard_context`, `DashboardOverviewController`, `DashboardView` | Runtime dashboard context and overview UI. | Kernel/workspace/plugin/LLM state; outputs dashboard rows/advice. | May query config/plugin/LLM state. |
| `screens/workspaces.py`, `workspace_screen.py` | `WorkspaceScreenController`, `WorkspaceView` | Workspace list/create/select/delete UI. | Workspace IDs and user actions; outputs workspace records/status. | Filesystem workspace mutation, permissioned deletes. |
| `screens/papers.py`, `paper_screen.py` | `PaperScreenController`, `PaperView` | Paper import/list/show/edit/enrich UI. | Paper paths/metadata and workspace selection; outputs import/enrichment display records. | Filesystem paper writes and optional metadata enrichment. |
| `screens/experience.py`, `experience_screen.py` | `ExperienceScreenController`, `ExperienceView` | Experience suggestion/confirmation/list/edit/delete/export UI. | Experience records and workspace scope; outputs stored/exported experience records/status. | Filesystem persistence/export. |
| `screens/experiment_screen.py` | `ExperimentGuideView` | Experiment protocol/session UI. | Protocol table selections and step/calculation actions; outputs session refresh/status. | Kernel/plugin calls and log/session updates. |
| `screens/llm_screen.py`, `permission_screen.py`, `tool_screen.py`, `log_screen.py` | `LLMScreenController`, `LLMView`, `PermissionScreenController`, `PermissionView`, `ToolView`, `LogReportView` | Provider config, permission mode/directory UI, workspace tool UI, and log report UI. | User selections/inputs; outputs provider mutations, permission decisions, tool actions, log tables/details. | Config/log/filesystem writes and guarded tool operations. |

Call/data flow: Textual event/callback -> screen controller -> core workspace/paper/experience/LLM/permission/tool/log service -> redacted TUI status/table/chat display. Static maps undercount Textual callback relationships; treat `compose`, `on_*`, `action_*`, and timers as framework-invoked.

### Experience learning and self-evolution files

| File/module | Main functions/classes/components | Responsibility | Inputs / outputs | Side effects and dependencies |
| --- | --- | --- | --- | --- |
| `core/experience.py` | `ExperienceRecord`, `ExperienceClassificationSuggestion`, `ExperienceStore`, `validate_confirmed_record`, `validate_general_experience_privacy`, raw-conversation rejection helpers | Privacy-preserving experience learning storage. | Candidate experience fields, project/general scope, workspace roots; outputs validated/stored records, classification suggestions, export payloads. | Filesystem JSON persistence; rejects raw conversation/project-private markers. |
| `core/self_evolution.py` | `SelfEvolutionError`, `SelfEvolutionValidationError`, `SelfEvolutionPermissionError`, `GeneratedArtifact`, `SelfEvolutionRequest`, `SelfEvolutionResult`, `SelfEvolutionService.generate/preview/confirm`, `_normalize_request`, `_build_artifacts`, `_finalize_artifacts`, `_resolve_output_file`, `_validate_candidate_path`, `_validate_extension_and_overwrite`, `_authorize_artifacts`, `_write_artifacts`, `_resolve_experience_records`, `_build_plan`, `_render_markdown`, `_render_tool_readme`, `_render_python_tool`, `_render_r_tool`, `_record_event`, `_write_audit_event`, `_write_log_event`, `build_self_evolution_preview` | Safe deterministic self-evolution artifact generation for whitelisted Markdown/Python/R outputs. | User intent, artifact type/output request, optional confirmed experience source, access mode/confirmation context; outputs preview plan/artifacts or confirmed write result/errors. | Preview may write audit/log events; confirm can bootstrap default policy, append audit/log records, create directories, and write generated artifacts under approved roots; failures are redacted and logged when possible. Depends on `core.experience`, `core.log_report`, `core.operation_guard`, `core.path_safety`, `core.redaction`, `permission.*`. |
| `tests/test_self_evolution.py`, `tests/test_self_evolution_cli.py` | Self-evolution service/CLI regression tests | Coverage anchors for preview/confirmation, permission modes, path rejection, generated artifact safety, and help/CLI behavior. | Test inputs and temporary project roots; expected structured results. | Test-only filesystem/temp effects when run by verifier; not production code. |

Call/data flow: user intent -> optional confirmed experience lookup -> normalized `SelfEvolutionRequest` -> deterministic preview artifacts/plan -> explicit confirmation and permission/audit authorization -> whitelisted artifact writes. Self-evolution must not mutate arbitrary source paths unless conservative/full access rules and explicit acknowledgement allow it.

### Cross-module dependency hotspots

- `core.kernel` depends on configuration, events, sessions, plugin registry,
  permissions, LLM manager, and checkpoint manager; most user-facing flows pass
  through it or mirror its service composition in CLI/TUI controllers.
- `permission.*`, `core.path_safety`, `core.operation_guard`, and
  `core.redaction` are safety dependencies for adapters, workspace tools,
  paper import, self-evolution, uninstall, and any side-effecting plugin/tool.
- `core.plugin_registry` and `plugins.base_plugin` define the plugin ABI used by
  RAG, harness, standards, experiment, Python stats, and R survival modules.
- `adapters.base_adapter` is the shared local tool-call implementation for
  standalone/OpenCode adapters and informs optional Claude/OpenCode safety
  boundaries.
- `core.workspace`, `core.paper_import`, `core.experience`, `core.workspace_tools`,
  and `core.tui.screens.*` form the workspace UX/data plane.
- LLM providers depend on config redaction and token tracking; diagnostics must
  stay secret-free.
- Medical-writing/citation modules are the current SuperMedicine-native anchors
  for Nature-style and citation-checking work, but they do not constitute
  installed external skills by those exact names.

### Side-effect inventory summary

- Filesystem writes: config center, workspace manager, paper importer, experience
  store, self-evolution, audit/log/token stores, checkpoints, adapters' write/edit
  tools, installer/uninstaller/release helpers, workspace tools, local RAG context.
- Subprocess execution: `BaseAdapter._tool_bash`, `ClaudeCodeAdapter._invoke`,
  installer/uninstaller/release helper paths, and external analysis runners when
  invoked through guarded tool workflows.
- Network calls: LLM provider clients and PubMed/RAG providers when configured and
  permissioned; optional platform/runtime status checks can probe local runtime
  availability.
- Event/callback side effects: `EventBus.publish`, Textual `on_*` callbacks,
  plugin execution, orchestrator dispatch, logging handlers.
- Persistent audit/log effects: permission audit, log report store, self-evolution
  audit/log events, token JSONL records, agent checkpoints.

### Maintainer update checklist for this map

- Update curated sections when adding/removing modules, plugin actions,
  side-effecting call paths, or optional platform capabilities.
- Keep exact-name status for Nature-Skill, PaperSpine, and Citation-Check-Skill
  separate from SuperMedicine-native anchors to avoid overclaiming installed-skill
  behavior.
- Keep self-evolution status synchronized with local intended files if they are
  promoted to tracked source or removed from the roadmap inventory.
- Do not commit generated build artifacts, raw private notes, runtime logs, or
  ignored scratch docs as evidence for this map.

## Summary

- Python source files analyzed: 179
- Callable units inventoried: 2082
- Parse errors: 0
