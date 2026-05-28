# Platform Integration Audit

Step 1 audit artifact for separating SuperMedicine standalone core capability
from optional OpenCode / Claude Code platform integrations. Step 6 documentation
updates preserve this model as **core independent + platform add-ons**. Current
user-facing summaries live in [../README.md](../README.md), [../INSTALL.md](../INSTALL.md),
and [../ARCHITECTURE.md](../ARCHITECTURE.md); this file preserves audit evidence
and final support-status reasoning.

## 1. Core Standalone Boundary

The standalone core should be runnable without OpenCode, Claude Code, or any assistant-platform runtime on the host. Based on the inspected files, the core boundary currently consists of:

- `Cli.py` — user-facing CLI entry point for `init`, `status`, `run`, workspace, paper, experience, and TUI commands. Core execution enters `core.kernel.Kernel` directly and does not need platform adapters.
- `Install.py` — core project initialization via `init_config(...)`, including `.supermedicine/config.yaml`, local agent/plugin directories, and canonical default policy creation.
- `core/**` — microkernel, workspace, config, event bus, session, operation/path guards, paper import, experience storage, LLM provider abstractions, and TUI foundation.
- `permission/**` — canonical policy parsing, default policy resource, runtime `PermissionEngine`, audit logger, and prompt-context generator.
- `agents/**` — in-process agent base class, orchestrator, state machine, and checkpoint persistence. These are SuperMedicine workflow concepts, not OpenCode agents by themselves.
- `plugins/**` — RAG, harness, medical writing/citation, Python statistics, and R survival plugin contracts and implementations. Production plugin execution is intended to flow through `core.kernel.Kernel.execute_task(...)` and `PermissionEngine.check(...)`.
- `pyproject.toml` runtime dependencies — `pyyaml`, `rich`, and `textual`; optional `r` extra for `rpy2`; `dev` extra for test/lint tooling.
- Core tests — tests for CLI, kernel, permissions, plugins, workspaces, paper import, experience, TUI, state machine, checkpoints, and backward compatibility.

Standalone success criterion for later steps: a fresh install using only package/core dependencies can run `supermedicine init`, `supermedicine status`, and `supermedicine run ...` through `Kernel` and plugins without importing `adapters.opencode`, requiring `claude`, or requiring OpenCode configuration directories.

## 2. Optional Platform Add-on Boundary

Platform-specific support should be treated as optional integration layers around the core:

- `adapters/base_adapter.py` — shared adapter abstraction and local tool helpers. It imports `permission.engine` / `permission.policy` and is an adapter-support layer, not required by core CLI/kernel execution.
- `adapters/standalone/adapter.py` — local adapter facade. It is useful for adapter contract testing and local tool simulation, but should not be required for core CLI/kernel operation.
- `adapters/opencode/**` — OpenCode adapter implementation, `plugin.json`, six OpenCode skill documents, and four OpenCode agent markdown definitions.
- `adapters/claude_code/**` — minimal Claude Code adapter implementation and Claude skill markdown.
- `install.json` platform entries — platform distribution/install metadata for OpenCode and Claude Code.
- Adapter tests — `tests/test_opencode_adapter.py`, `tests/test_claude_code_adapter.py`, `tests/test_standalone_adapter.py`, and repository-hygiene checks for adapter manifests.

Optional add-on success criterion for later steps: adapter packages and docs can be installed/copied separately from the core, and their tests/documentation clearly indicate they are optional integrations layered over the standalone core.

## 3. OpenCode Support Findings

Current OpenCode support is implemented as an optional integration surface:

- `adapters/opencode/adapter.py` implements `OpenCodeAdapter` with `platform_name == "opencode"`.
- Tool mapping exists for `bash`, `read`, `write`, `edit`, `glob`, `grep`, `skill`, and `task`.
- High-risk adapter tools are funneled through shared permission checks in `adapters/base_adapter.py` for `bash`, `write`, and `edit`.
- Project-root sandboxing exists in `adapters/base_adapter.py` for read/write/edit/glob/grep path operations.
- `adapters/opencode/plugin.json` declares platform metadata, tool permissions, six skills, four agents, and capability labels.
- `adapters/opencode/skills/*.md` contains integration-facing workflow documentation for RAG, harness, medical writing/citation, Python statistics, and R survival.
- `adapters/opencode/agents/*.md` contains alpha/beta/gamma/delta role definitions mapped to OpenCode roles.
- `tests/test_opencode_adapter.py` and `tests/test_repo_hygiene.py` cover adapter import, tool behavior, permission denial before mutation/execution, sandbox behavior, `plugin.json`, skills, and agents.

Historical pre-remediation gaps / clarification needs:

- `OpenCodeAdapter.subagent_dispatch(...)` falls back to reading local markdown when no orchestrator is injected. It does not actually invoke an external OpenCode subagent runtime by itself.
- `adapters/opencode/plugin.json` declares broad tool permissions but does not document the SuperMedicine standalone-core boundary.
- Pre-Step-6 finding: `README.md` and `ARCHITECTURE.md` presented OpenCode as a project feature rather than clearly as an optional add-on. Current post-Step-6 docs now describe OpenCode as optional add-on content and preserve the no-native-runtime-bridge limitation.
- Packaging currently includes `adapters*` in the default package discovery in `pyproject.toml`, so OpenCode artifacts are shipped with the base package rather than clearly separated as optional integration content.

Current documentation status after Step 6:

- User docs now call OpenCode an optional add-on, not a core dependency.
- Claims are limited to the implemented adapter surface, metadata, skills,
  agent role files, and permission-gated tool paths.
- Native external OpenCode subagent runtime dispatch is not claimed unless
  implemented; current behavior depends on an injected SuperMedicine
  orchestrator or local metadata fallback.

## 4. Claude Code Support Completeness Findings

Claude Code support is intentionally minimal and should be documented as such:

- `adapters/claude_code/adapter.py` implements `ClaudeCodeAdapter` with registration metadata and `platform_name == "claude-code"`.
- Supported tools are `claude.capabilities`, `claude.runtime_status`, and `claude.invoke`.
- `claude.invoke` can call a local `claude --print <prompt>` runtime when available on PATH.
- Runtime-unavailable, timeout, runtime-error, unsupported-tool, invalid-input, and permission-denied states are structured.
- Sensitive-looking prompt/runtime output values are redacted via shared adapter redaction helpers.
- Permission checks use the canonical policy path before Claude adapter tool execution.
- `tests/test_claude_code_adapter.py` covers capability reporting, runtime unavailable state, mock invocation, timeout, redaction, permission denial, explicit unavailable subagent dispatch, unsupported tools, and skill doc examples.

Historical pre-remediation gaps / mismatch risks:

- `ClaudeCodeAdapter.capabilities()` explicitly reports `native_subagent_dispatch: False` and `native_skill_load: False`.
- `ClaudeCodeAdapter.subagent_dispatch(...)` returns `status: "unavailable"`; it is not a native Claude Code sub-agent bridge.
- `ClaudeCodeAdapter.skill_load(...)` returns contract metadata only; it does not load native Claude Code skills.
- Pre-Step-6 finding: `install.json` declared Claude Code as `"type": "skill+subagent"`, which overstated adapter behavior because native subagent dispatch and native skill loading are unavailable. Current manifest wording uses `"skill-doc+cli-adapter"` to avoid claiming unsupported native capability.
- `adapters/claude_code/SKILL.md` has a “Sub-Agent Configuration” section with OpenCode mapping terminology; this should be reframed for Claude Code or marked as conceptual SuperMedicine roles.
- Pre-Step-6 finding: `README.md` and `ARCHITECTURE.md` said “minimal” in some places while the manifest and add-on boundary still needed alignment. Current post-Step-6 docs and manifest consistently describe Claude Code as a minimal optional add-on.

Current documentation status after Step 6:

- User docs now call Claude Code a minimal optional add-on, not a core
  dependency.
- Supported claims remain limited to `claude.capabilities`,
  `claude.runtime_status`, and permission-checked `claude.invoke` using local
  `claude --print` when available.
- Native Claude Code skill loading and native subagent dispatch remain
  documented as unavailable.

## 5. Coupling Risks and Exact File-Level Modification Targets for Steps 2-7

### Risk A — Default Package/Distribution Blurs Core and Adapters

- Evidence: `pyproject.toml` includes `adapters*` in `[tool.setuptools.packages.find].include`.
- Risk: a base SuperMedicine install ships platform adapters as default package content, making optional integrations look like core runtime.
- Modification targets:
  - `pyproject.toml` — decide whether adapters remain shipped as data but documented optional, or move platform-specific install into optional extras/package-data boundaries.
  - `tests/test_repo_hygiene.py` — update packaging/manifest assertions if adapter packaging is split or optionalized.
  - `README.md` and `ARCHITECTURE.md` — document core package versus optional adapter package/content boundary.

### Risk B — Canonical Permission Policy Contains Platform-Specific Claude Scopes

- Evidence: `permission/default_policy.yaml` allows `tool_call` scopes `claude.capabilities`, `claude.runtime_status`, and `claude.invoke` for `alpha`.
- Risk: core default policy embeds Claude-specific resources, weakening the “core has no platform dependency” story.
- Modification targets:
  - `permission/default_policy.yaml` — move or clearly isolate platform-specific scopes.
  - `.supermedicine/policies/default.yaml` — keep tracked project policy aligned with packaged default policy if policy structure changes.
  - `permission/policy.py` and `permission/engine.py` — only if policy composition/overlay support is added.
  - `adapters/claude_code/adapter.py` — update default policy expectations if Claude adapter uses a platform overlay policy.
  - `tests/test_claude_code_adapter.py`, `tests/test_permission_engine.py`, `tests/test_policy.py`, `tests/test_integration.py` — update policy fixtures/expectations.

### Risk C — Standalone Adapter Loads OpenCode Skill Files

- Evidence: `adapters/standalone/adapter.py` resolves skills from `adapters/opencode/skills/{skill_name}.md`.
- Risk: even the standalone adapter has a direct file-level dependency on OpenCode skill layout.
- Modification targets:
  - `adapters/standalone/adapter.py` — switch to standalone/core-neutral skill source or return explicit unsupported metadata.
  - `adapters/standalone/__init__.py` — update export docs if needed.
  - `tests/test_standalone_adapter.py` — assert no dependency on `adapters/opencode/skills` for standalone behavior.
  - Optional new target: `adapters/standalone/skills/**` or core-neutral docs if standalone skill loading remains supported.

### Risk D — Installer Platform Detection is Mixed into the Core Installer

- Evidence: `Install.py` detects `~/.claude` and `~/.config/opencode` via `detect_platform()`.
- Risk: a core installer script contains assistant-platform discovery logic and may imply platform setup is part of core initialization.
- Modification targets:
  - `Install.py` — keep `--init` core-only and move/label `--detect` as optional platform detection.
  - `install.json` — split core install steps from optional platform add-on steps.
  - `INSTALL.md` and `README.md` — clarify platform detection is optional and not required for standalone operation.
  - `tests/test_integration.py` — protect `init_config(...)` as core-only.

### Risk E — Install Manifest Overstates Claude Code Support

- Pre-Step-6 evidence: `install.json` declared `claude-code` as `"type": "skill+subagent"`, while `ClaudeCodeAdapter` reported native subagent dispatch unavailable.
- Current status: the manifest type is `"skill-doc+cli-adapter"`, matching the minimal optional adapter model and avoiding native skill/subagent overclaim.
- Historical risk: downstream users or installers could assume full Claude Code subagent integration existed.
- Modification targets:
  - `install.json` — change Claude Code type/capability wording to minimal skill/CLI-adapter integration until native subagents exist.
  - `adapters/claude_code/SKILL.md` — clarify conceptual roles versus native Claude Code features.
  - `tests/test_repo_hygiene.py` — update manifest expectations.
  - `tests/test_claude_code_adapter.py` — keep explicit unavailable subagent expectation.

### Risk F — Documentation Presented Adapters as Peer Architecture Layer, Not Optional Add-Ons

- Pre-Step-6 evidence: `README.md` architecture tree listed `adapters/` alongside `core/`, `permission/`, `agents/`, and `plugins/`; `ARCHITECTURE.md` showed Adapter Layer as a peer of Agent and Plugin layers.
- Current status: `README.md` and `ARCHITECTURE.md` now annotate adapters as optional platform add-ons around the standalone Python core.
- Historical risk: documentation could obscure that SuperMedicine core must run without OpenCode/Claude Code.
- Modification targets:
  - `README.md` — add “Core standalone vs optional platform adapters” section and adjust feature wording.
  - `ARCHITECTURE.md` — redraw or annotate adapter layer as optional boundary around core.
  - `Architecture/PhaseImplementationPlan.md` — update compatibility invariants to preserve standalone core and optional add-on separation.
  - `Architecture/WorkspaceTuiRagGuide.md` — only if platform assumptions are found in user workflows.

### Risk G — Adapter Tests are Mixed into the Single Default Test Suite

- Evidence: `pyproject.toml` sets all `tests/test_*.py` as one suite; adapter tests import `adapters.opencode` and `adapters.claude_code` directly.
- Risk: core-only verification cannot be distinguished from optional adapter verification.
- Modification targets:
  - `pyproject.toml` — consider pytest markers such as `core`, `adapter`, `opencode`, `claude_code`.
  - `tests/test_opencode_adapter.py`, `tests/test_claude_code_adapter.py`, `tests/test_standalone_adapter.py` — mark optional adapter tests if markers are introduced.
  - `tests/test_backward_compatibility.py`, `tests/test_integration.py`, `tests/test_kernel.py`, `tests/test_plugin_registry.py`, `tests/test_permission_engine.py` — identify as core verification set.
  - `README.md` — document core verification versus optional adapter verification commands.

### Risk H — Architecture Wording Can Imply Kernel Depends on Adapters

- Evidence: `ARCHITECTURE.md` overview says Kernel integrates “plugins, adapters, and agents”; data-flow diagram starts with `CLI / Platform Adapter`.
- Risk: readers may believe adapters are part of Kernel initialization.
- Modification targets:
  - `ARCHITECTURE.md` — state that `Kernel` initializes core subsystems and plugins; adapters are external entrypoints into the kernel, not kernel dependencies.
  - `core/kernel.py` — no runtime behavior change appears necessary; keep it adapter-free.
  - `tests/test_kernel.py` and `tests/test_backward_compatibility.py` — protect no adapter import/requirement in kernel execution if a regression test is added later.

## 6. Verification Checklist for Later Steps

Use this checklist after Steps 2-7 modify code/docs:

- Core standalone boundary:
  - `Cli.py` and `core/kernel.py` can be imported without importing `adapters.opencode` or `adapters.claude_code`.
  - `supermedicine init` / `CLI().init(...)` creates `.supermedicine/config.yaml` and default policy without platform config directories.
  - `Kernel(...)` plugin discovery and execution use only `core/**`, `permission/**`, `agents/**`, and `plugins/**` paths.
  - `Install.py --init` remains core-only and does not require OpenCode/Claude Code runtime/config.

- Optional adapter boundary:
  - OpenCode-specific files remain under `adapters/opencode/**` and are documented as optional add-on content.
  - Claude Code-specific files remain under `adapters/claude_code/**` and are documented as minimal optional add-on content.
  - Standalone adapter no longer depends on OpenCode skill file layout, or the dependency is explicitly documented as a temporary compatibility bridge.
  - Platform-specific policy scopes are isolated from the core default policy or explicitly marked as adapter overlay policy.

- OpenCode support:
  - `adapters/opencode/plugin.json` entries point to existing skills/agents.
  - `OpenCodeAdapter` still supports the declared tool ids and preserves permission-gated high-risk operations.
  - Documentation states whether subagent dispatch is native OpenCode runtime dispatch or local/orchestrator fallback.

- Claude Code support:
  - `ClaudeCodeAdapter.capabilities()` truthfully reports native skill/subagent limits.
  - `install.json` does not claim native Claude Code subagent support unless implemented.
  - `claude.invoke` remains permission-checked, timeout-bounded, and redacted.

- Tests and docs:
  - Core tests and optional adapter tests are distinguishable by path, marker, or documented command.
  - `README.md`, `ARCHITECTURE.md`, and `install.json` consistently describe core standalone operation and optional platform add-ons.
  - Repository hygiene checks still prevent generated/cache/secret artifacts from being tracked.

## 7. Final Execution Summary

Step 9 closes the platform-integration clarification work with the following final support status:

- Standalone core independence is the primary supported operating model. The Python CLI, installer initialization path, kernel, permissions, core agents, plugins, workspace, paper import, experience learning, and TUI documentation are described as runnable without OpenCode, Claude Code, or any assistant-platform runtime.
- OpenCode is documented as an optional add-on surface. Current support covers the OpenCode adapter, declared tool mapping, plugin metadata, skill documents, agent role files, and permission-gated adapter operations. It does not include a standalone native OpenCode subagent runtime bridge; subagent behavior remains limited to an injected SuperMedicine orchestrator path or local metadata fallback.
- Claude Code is documented as a minimal optional add-on. Current support covers adapter capability reporting, runtime status checks, and permission-checked local `claude --print` invocation when the Claude CLI is available. It does not include native Claude Code skill loading or native Claude Code subagent dispatch.
- Documentation and manifest wording were aligned to avoid presenting platform adapters as core dependencies or overstating unsupported native platform features.

Verification results available for this execution set:

- `ruff` pass.
- `mypy` pass: `Success`, 126 source files.
- `pytest`: 424 passed, 3 skipped.
- Build pass.
- Installed wheel smoke pass.

Remaining limitations:

- Platform adapters are still present in the repository/package tree as optional integration content, so distribution splitting remains a future packaging decision rather than a completed separation.
- Core and optional adapter tests are covered by the current verification set, but a separately documented core-only versus adapter-only command split can still improve release diagnostics.
- OpenCode native subagent runtime dispatch is not implemented by this work.
- Claude Code native skill loading and native subagent dispatch are not implemented by this work.

Follow-up recommendations:

- Decide whether to keep adapters bundled as optional content in the base package or split them into optional extras/packages with corresponding packaging tests.
- Add explicit test markers or documented commands for core-only, OpenCode-adapter, Claude-Code-adapter, and full-suite verification.
- If native platform integration is desired later, implement it as new adapter functionality with tests before changing support claims in user documentation or manifests.

## 8. AI/LLM, Installation, Platform Adapter, and Configuration Boundary Audit

Date: 2026-05-27

Scope: audit-only inventory of the current AI/LLM, installation/configuration,
OpenCode, Claude Code, permission, documentation, and test contracts. No runtime
feature implementation was performed, and no real API keys, private endpoints, or
secrets were added to source, tests, or documentation.

### 8.1 Installation and Local Configuration Contracts

- `install.json` is the agent-readable installation manifest. It declares the
  standalone core install steps (`git clone`, `pip install -e .`, optional
  `Install.py --detect`, and `Install.py --init`) plus two optional platform
  entries: `claude-code` and `opencode`. Both platform entries are marked
  `optional_add_on: true`, `core_runtime_required: false`, and expose exactly one
  user-facing surface, `SuperMedicine`; `alpha`, `beta`, `gamma`, and `delta` are
  internal role contexts only. The manifest points to repository-local adapter
  files, not user-local `.claude` or `.opencode` configuration directories.
- `Install.py` keeps `--init` core-only. `init_config(...)` creates
  `.supermedicine/config.yaml`, `.supermedicine/agents`, `.supermedicine/plugins`,
  and the canonical permission policy without probing OpenCode, Claude Code, or
  assistant-platform directories. Platform probing is isolated behind explicit
  `--detect`, which checks for `~/.claude` and `~/.config/opencode` and returns a
  platform label only.
- `.supermedicine/config.yaml` currently contains only bootstrap metadata:
  project name and `Beta0.3.0` version. It contains no LLM endpoint, BaseURL,
  OpenAI/Anthropic/OpenRouter key, or private platform configuration.
- Tracked `.supermedicine/**` is intentionally limited by
  `tests/test_repo_hygiene.py` to `.supermedicine/config.yaml` and
  `.supermedicine/policies/default.yaml`; runtime audit logs and checkpoints are
  treated as ignored/generated artifacts.
- `README.md`, `INSTALL.md`, and `ARCHITECTURE.md` consistently describe the
  default setup as standalone Python core installation. OpenCode and Claude Code
  are documented as optional add-ons and are not prerequisites for installation,
  `Kernel` initialization, or ordinary CLI use.
- Uninstall guidance in `INSTALL.md` is core-local: `pip uninstall supermedicine`
  and removal of `.supermedicine/`; it does not instruct users to remove or alter
  user-local assistant-platform configuration directories.

### 8.2 LLM Provider and Secret-Boundary Contracts

- `core/llm_client.py` defines the abstract `LLMClient` contract with `chat(...)`
  and `complete(...)` methods returning dictionaries with `content`, `model`, and
  `usage` fields. The factory `create_llm_client(...)` supports `openai`,
  `anthropic`, and legacy `openrouter`, and raises `ValueError` for unsupported
  providers.
- `core/llm_providers/base.py` implements configured OpenAI-compatible and
  Anthropic-compatible HTTP clients. `core/llm_providers/config.py` normalizes
  provider, API format, custom BaseURL, API key or API key environment variable,
  model, timeout, and headers.
- Installer defaults are `https://api.openai.com/v1` with `OPENAI_API_KEY` and
  `gpt-4o-mini`, and `https://api.anthropic.com/v1` with `ANTHROPIC_API_KEY` and
  `claude-3-5-sonnet-latest`. Custom compatible BaseURL values are supported by
  installer flags, `SM_LLM_BASE_URL`, and project configuration.
- `Install.py --init` accepts `--provider openai|anthropic`, `--base-url`,
  `--api-key`, `--model`, and `--interactive`. It also reads `SM_LLM_PROVIDER`,
  `SM_LLM_BASE_URL`, `SM_LLM_API_KEY`, `SM_LLM_MODEL`, `OPENAI_API_KEY`, and
  `ANTHROPIC_API_KEY`. Installer output redacts supplied API keys.
- OpenRouter remains available as a legacy provider path with
  `OPENROUTER_API_KEY`; it is not the only LLM provider path.
- Missing provider values return structured validation errors such as
  `missing_api_key`, `missing_base_url`, and `missing_model`; request/HTTP errors
  sanitize known secret values.
- `tests/test_llm_client.py` uses dummy values such as `test-key` and
  `test-model` only. It covers default/custom model initialization, missing-key
  behavior, mocked chat/complete responses, and unsupported provider errors. It
  does not contain or require real OpenRouter, OpenAI, or Anthropic credentials.
- Related RAG external-provider contracts use environment-variable references
  such as `api_key_env`/`SM_RAG_API_KEY` rather than storing secret values in
  repository configuration.

### 8.3 OpenCode Adapter Contracts

- `adapters/opencode/adapter.py` implements `OpenCodeAdapter` as an optional
  add-on. It reports `platform_name == "opencode"`, `optional_add_on: true`, and
  `core_runtime_dependency: false`.
- Supported OpenCode tool ids are exactly `bash`, `read`, `write`, `edit`,
  `glob`, `grep`, `skill`, `task`, and `opencode.capabilities`. High-risk paths
  are routed through the shared permission and project-root sandbox logic.
- OpenCode skill loading is local-file loading from the declared skill allowlist:
  `rag-query.md`, `harness-monitor.md`, `medical-writing.md`,
  `medical-citation.md`, `python-stats.md`, and `r-survival.md` under
  `adapters/opencode/skills/`.
- OpenCode role context files are declared for `alpha`, `beta`, `gamma`, and
  `delta` under `adapters/opencode/agents/`. They are non-user-facing internal
  role context only. `adapters/opencode/agents/supermedicine.md` is the single
  user-facing OpenCode agent document.
- `OpenCodeAdapter.subagent_dispatch(...)` executes a real SuperMedicine
  orchestrator dispatch only when an orchestrator/runtime bridge is injected by
  the caller. Without one, it returns a structured degraded result and explicitly
  reports that native OpenCode subagent dispatch was not executed.
- `adapters/opencode/plugin.json` is the OpenCode manifest. It declares the
  adapter module, plugin entry, one user-facing agent, six skills, four internal
  role context documents, permission boundaries, and the no-native-runtime-bridge
  limitation.

### 8.4 Claude Code Adapter Contracts

- `adapters/claude_code/adapter.py` implements `ClaudeCodeAdapter` as a minimal
  optional add-on. It reports `platform_name == "claude-code"`, optional status,
  no core runtime dependency, and no native skill/subagent support.
- Supported Claude Code tool ids are exactly `claude.capabilities`,
  `claude.runtime_status`, and `claude.invoke`.
- `claude.invoke` is a permission-checked, timeout-bounded local CLI invocation
  path for `claude --print <prompt>` when a local `claude` runtime is available
  on `PATH`. Missing `claude` is returned as an adapter-unavailable state, not a
  SuperMedicine core failure.
- Claude Code adapter responses include structured unavailable, timeout,
  runtime-error, unsupported-tool, invalid-input, and permission-denied states;
  sensitive-looking prompt/runtime output is redacted via shared adapter helpers.
- `adapters/claude_code/SKILL.md` is a Claude Code-facing skill/documentation
  surface. It documents the manifest entry, supported tools, explicit limitations,
  one user-facing `SuperMedicine` surface, and internal role contexts. It does not
  claim native Claude Code skill loading or native subagent dispatch.

### 8.5 Documentation and Test Coverage Contracts

- `README.md` contains user-facing installation, quick start, optional platform
  add-on setup, capability matrix, testing commands, and safety/security notes.
  It explicitly states that OpenCode, Claude Code, and other assistant platforms
  are not prerequisites.
- `INSTALL.md` is the detailed setup reference. It keeps core installation,
  optional R support, platform add-ons, safety boundaries, and uninstall guidance
  separate. It notes that `Install.py --init` creates `.supermedicine/` core
  configuration only and does not create OpenCode/Claude Code configuration.
- `ARCHITECTURE.md` documents `core/llm_providers/` as OpenRouter integration,
  describes secrets as environment-variable references, and frames `adapters/` as
  optional platform add-ons rather than Kernel requirements.
- `tests/test_opencode_adapter.py` verifies OpenCode adapter import, capability
  reporting, single user-facing agent, supported tools, sandbox/permission
  behavior, skill files, agent files, manifest declarations, and degraded versus
  orchestrator-backed dispatch behavior.
- `tests/test_claude_code_adapter.py` verifies Claude Code optional import,
  capability/runtime reporting, mocked invocation, runtime unavailable behavior,
  timeout handling, redaction, permission denial before subprocess execution,
  unsupported tools, unavailable subagent dispatch, and skill-document boundary
  wording.
- `tests/test_repo_hygiene.py` enforces repository hygiene around generated
  artifacts, tracked `.supermedicine/**` limits, external platform config
  exclusions, install manifest adapter paths, supported tool declarations,
  single user-facing platform agent, OpenCode manifest resources, and forbidden
  legacy platform agent names.
- The audit found no real OpenAI, Anthropic, OpenRouter, or platform API key
  value written into the inspected source, docs, manifests, config, or tests.
  Existing test strings such as `test-key`, `secret-key`, and redaction payloads
  are dummy fixtures used to exercise missing-key and redaction behavior.

### 8.6 Current Implementation Boundary and Follow-Up Risks

- Current AI/LLM functionality includes direct OpenAI-compatible and
  Anthropic-compatible provider clients, custom BaseURL configuration, environment
  variable and installer injection, and legacy OpenRouter support. Documentation
  examples must continue to use placeholders only.
- Platform adapters are packaged in the repository tree and tested in the default
  suite, but their docs and manifests label them optional. A future packaging or
  test-marker split may improve core-only versus adapter-only diagnostics without
  changing behavior.
- Any future support for additional provider formats, native OpenCode runtime
  dispatch, or native Claude Code skill/subagent loading must be added as new
  functionality with tests before updating manifests or user-facing support
  claims.
