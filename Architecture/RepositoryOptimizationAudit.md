# Repository Optimization Audit

Date: 2026-05-26

Purpose: establish the immutable baseline and protection boundaries before any repository optimization. This step is audit-only: no runtime/source behavior changes are allowed in this step except creating this document.

## Audit Pass Index

Use this index as the canonical navigation layer for repeated repository-optimization passes. Later passes should link back here instead of restating long prior findings unless a fresh observation materially differs.

| Sections | Pass / step | Scope | Outcome |
| --- | --- | --- | --- |
| 1-9 | Initial baseline audit | Branch/worktree state, structure, commands, artifacts, and no-go boundaries | Established preservation boundaries and cleanup policy. |
| 10 | Initial Step 2 audit | Independent-word capitalization/path-risk audit | Found no safe source-of-truth rename candidate. |
| 11 | Initial Step 3 execution | Conservative naming normalization | Performed no path renames. |
| 12 | Initial Step 4 audit | Duplicate/redundant content and generated artifact audit | Recommended generated-artifact cleanup only; skipped source/content deduplication. |
| 13 | Initial Step 5 execution | Generated-artifact cleanup | Removed accessible generated/cache/runtime artifacts; skipped inaccessible `.pytest_cache/` and source content. |
| 14 | Initial Step 6 execution | Documentation-only consistency update | Clarified audit wording; changed no runtime/source behavior. |
| 15 | Current repeated-pass baseline refresh | Fresh state at commit `0fe238b` | Re-established clean tracked baseline, complete tracked Markdown inventory, and repeated-pass boundaries from current Git observations. |
| 16 | Repeated-pass Step 2 audit | Deep semantic-preserving audit | Identified generated cleanup and docs-navigation candidates; skipped risky duplicates/renames. |
| 17 | Repeated-pass Step 3 execution | Generated/cache cleanup | Removed accessible generated/cache/runtime artifacts only. |
| 18 | Repeated-pass Step 4 execution | Naming/capitalization follow-up | Performed no renames; no reference synchronization required. |
| 19 | Repeated-pass Step 5 execution | Safe duplicate reduction | Added this navigation index and recorded skipped duplicate-looking items; no source/prose deletion performed. |
| 20 | Repeated-pass Step 6 execution | Repository format and text hygiene | Applied minimal docs-only hygiene; skipped risky formatting churn. |
| 21 | Repeated-pass Step 7 assessment | Non-invasive repository hygiene test coverage | Added audit-only coverage assessment; no new test churn needed. |
| 22 | Repeated-pass Step 9 review | Final diff and semantic-preservation confirmation | Cleaned accessible regenerated artifacts and confirmed final diff scope remains audit-document only. |
| 23 | Step 2 Markdown strategy | Tracked Markdown rewrite and deduplication strategy | Defined safe prose rewrite rules, per-file categories, duplication policy, and verification approach for all 29 tracked Markdown files. |
| 24 | Step 3 Markdown rewrite execution notes | Markdown-only rewrite traceability | Records that the follow-up rewrite should modify tracked Markdown only while preserving protected literals and audit evidence. |
| 26 | Current Step 1 repository baseline audit | Fresh repository status at commit `d9a69c5` | Recorded clean pre-audit Git state, structure, build/test command inventory, path-case risks, dependency boundaries, and non-semantic cleanup limits. |
| 27 | Current Step 2 naming normalization execution | Safe initial-capitalization path review | Performed no renames because every candidate is import, discovery, tooling, platform, documentation-link, or convention sensitive. |
| 28 | Current Step 3 duplicate reduction execution | Audit-document duplicate compression | Consolidated recently repeated baseline, boundary, command, artifact, and no-rename prose into compact audit summaries; preserved key evidence and decisions. |
| 29 | Current Step 4 repository cleanliness execution | Ignored generated/local artifact cleanup | Removed safe ignored cache/build/runtime/local planning artifacts; changed no source/config/test/manifest semantics and left ignore rules unchanged. |
| 30 | Current Step 5 verification preparation | Full consistency and regression gate plan | Recorded the validation gates Tester should run and the evidence/cleanup expectations; no verification command was run in this execution step. |
| 31 | Current Step 6 Git review and submission | Final verification evidence, cleanup, commit, and push | Recorded Tester-reported full verification evidence, cleaned regenerated ignored artifacts, and limited final tracked changes to this audit document before submission. |
| 32 | Current Step 6 repository cleanliness cleanup | Ignored generated artifact cleanup | Removed accessible ignored cache/build/package/runtime/local artifacts; preserved tracked `.supermedicine` config and policy inputs; left `.pytest_cache/` as the permission-denied boundary. |
| 33 | Current Step 7 full regression validation cleanup | Full verification evidence and generated-artifact cleanup | Recorded Tester-reported pass evidence for install, lint, type, wheel/sdist, pytest, repo hygiene, path/case integrity, diff scope, and secret/local-state checks; cleaned regenerated ignored artifacts accessible with normal permissions. |
| 34 | Current Step 8 diff review | Final diff semantic-preservation review | Confirmed the final tracked diff remains audit-document only, additive documentation/audit evidence only, and contains no functional semantic change. |

## 1. Current branch, remote, and working tree status

- Working directory: `D:\GIT\SuperMedicine`
- Current branch: `master`
- Tracking status: `master...origin/master`
- Remote:
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (fetch)`
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (push)`
- Recent baseline commit: `08ee767 feat: add workspace research tools and TUI workflows`
- Initial working tree state recorded by `git status --short --branch`:
  - Modified tracked files: 33
  - Untracked intended files: 2
  - No staged changes reported by `git diff --cached --stat`
- `git diff --stat` baseline summary: 33 files changed, 1354 insertions, 194 deletions.
- Git emitted line-ending warnings that LF will be replaced by CRLF next time Git touches many modified files. Treat line-ending normalization as non-semantic only if already project-standard and do not mix it with runtime behavior edits.

## 2. Current tracked and untracked intended changes summary

These pre-existing uncommitted changes are from earlier platform agent/model/version work that already passed final verification. Preserve them and do not discard, overwrite, or reinterpret them during optimization.

Modified tracked files at baseline:

- `.gitignore`
- `.supermedicine/config.yaml`
- `.supermedicine/policies/default.yaml`
- `ARCHITECTURE.md`
- `Architecture/ExecutionRoadmap.md`
- `Architecture/OptimizationAudit.md`
- `CHANGELOG.md`
- `Cli.py`
- `INSTALL.md`
- `Install.py`
- `README.md`
- `adapters/__init__.py`
- `adapters/claude_code/SKILL.md`
- `adapters/claude_code/adapter.py`
- `adapters/opencode/__init__.py`
- `adapters/opencode/adapter.py`
- `adapters/opencode/agents/alpha-analyst.md`
- `adapters/opencode/agents/beta-reviewer.md`
- `adapters/opencode/agents/delta-orchestrator.md`
- `adapters/opencode/agents/gamma-writer.md`
- `adapters/opencode/plugin.json`
- `adapters/standalone/adapter.py`
- `install.json`
- `permission/default_policy.yaml`
- `permission/prompt_generator.py`
- `pyproject.toml`
- `tests/test_backward_compatibility.py`
- `tests/test_claude_code_adapter.py`
- `tests/test_integration.py`
- `tests/test_opencode_adapter.py`
- `tests/test_plugin_registry.py`
- `tests/test_repo_hygiene.py`
- `tests/test_standalone_adapter.py`

Untracked intended files at baseline:

- `Architecture/PlatformIntegrationAudit.md`
- `adapters/opencode/agents/supermedicine.md`

## 3. Project structure and entry points

Tracked top-level structure includes:

- Documentation and governance: `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `Architecture/**`
- Python CLI and installer entry modules: `Cli.py`, `Install.py`
- Core runtime: `core/**`
- Permission engine and policies: `permission/**`, `.supermedicine/policies/default.yaml`
- Agent orchestration concepts: `agents/**`
- Optional platform adapters: `adapters/**`
- Plugin ecosystem: `plugins/**`
- Tests: `tests/**`
- Packaging/configuration: `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/ci.yml`, `.gitignore`

Entry points and discovery-sensitive paths:

- Package console script: `supermedicine = "Cli:main"` in `pyproject.toml`
- Setuptools modules: `py-modules = ["Cli", "Install"]`
- Setuptools package discovery: `core*`, `permission*`, `agents*`, `plugins*`, `adapters*`
- Package data: `permission/default_policy.yaml`
- Direct module entry guards observed: `Cli.py`, `Install.py`, `core/workspace_tools.py`
- TUI entry function observed: `core/tui/app.py::main`
- Pytest discovery conventions: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`
- OpenCode adapter metadata and agent/skill paths under `adapters/opencode/**`
- Claude Code skill/adapter paths under `adapters/claude_code/**`

## 4. Build, test, type, lint, and packaging command inventory

Validation commands documented by repository files and CI for later steps:

- Install development environment: `python -m pip install -e ".[dev]"`
- Lint gate: `python -m ruff check --select=E,F,W --ignore=E501 .`
- Full test suite: `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`
- Repository hygiene focused test: `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`
- Wheel smoke/build gate: `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>`
- Source distribution gate from CI release job: `python -m build --sdist --outdir dist`
- Optional documented local test command: `pytest tests/ -v`
- Optional type check mentioned in release notes: `mypy`; current CI/release gate documentation says dedicated type checking is not part of the enforced gate.
- CLI smoke commands referenced in docs/audits for later verification: `supermedicine status`, `supermedicine init`, `supermedicine run ...`, `python Install.py --init`, `python Cli.py status`.

Do not run verification in this audit step; Tester owns verification.

## 5. Generated and ignored artifacts observed

Ignored/generated artifacts observed by `git ls-files --others --ignored --exclude-standard` include:

- Python bytecode/cache directories across runtime, adapters, plugins, permission, agents, core, and tests: `__pycache__/`, `*.pyc`
- Ruff cache: `.ruff_cache/**`
- Pytest cache: `.pytest_cache/` was not listable because Git reported `warning: could not open directory '.pytest_cache/': Permission denied`
- Runtime audit log: `.supermedicine/policies/audit.jsonl`
- Runtime checkpoints: `.supermedicine/checkpoints/**`
- Local planning note: `Planning/NextSteps.md`
- Build output mirror: `build/lib/**`
- Packaging metadata: `supermedicine.egg-info/**`

Cleanup policy for later steps:

- Generated/ignored artifacts may be removed only when they are clearly ignored build/cache/runtime products and not source of truth.
- Do not remove tracked source, tests, docs, config, policies, plugin metadata, package metadata inputs, or adapter resources.
- Respect the `.pytest_cache/` permission denial; document and skip if deletion remains blocked.
- Do not clean untracked intended source/documentation files listed in section 2.

## 6. Hard no-go semantic preservation boundaries

Absolute priority: do not change existing functionality or code meaning, even for security risks or unused code. Later optimization must preserve:

- Public API behavior, function/class/module names, return shapes, exceptions, and import paths.
- CLI commands, arguments, defaults, prompts, output meanings, exit behavior, and the `supermedicine` console script entry point.
- Plugin IDs, action IDs, plugin manifests, action schemas, result schemas, and registry/discovery semantics.
- Adapter behavior and platform surfaces for OpenCode, Claude Code, and standalone adapters, including degraded/unavailable states.
- Agent IDs, role documents, skill document identity, plugin metadata, platform manifests, and install manifest semantics.
- Permission/security policy behavior, default allow/deny policy meanings, audit semantics, operation guard semantics, path safety checks, and prompt-generation safety guidance.
- Package entry points, setuptools package discovery, package data, optional extras, version meaning, and importable module names.
- Test meaning and assertions. Tests may only change if preserving intent while synchronizing purely mechanical path/name changes that have already been proven non-breaking.
- Medical/statistical output meanings, deterministic fixture behavior, R/rpy2 fallback behavior, RAG provider contracts, workspace behavior, TUI behavior, and paper/experience workflows.
- Configuration file meanings, default values, local `.supermedicine` behavior, policy file structure, and runtime artifact paths.
- Existing uncommitted platform agent/model/version changes listed in this audit.

## 7. Allowed optimization categories

Allowed only when safe and non-semantic:

- Documentation/prose/title naming cleanup, including independent word initial capitalization where it does not alter code identifiers, commands, paths, IDs, or quoted literals.
- Safe path capitalization only when every import, package/discovery reference, documentation reference, test reference, manifest reference, and platform reference is fully synchronized and the change is non-breaking on case-sensitive and case-insensitive filesystems.
- Exact duplicate prose deletion when text is semantically identical and no unique caveat, warning, or context is lost.
- Generated/ignored artifact cleanup under the cleanup policy in section 5.
- UTF-8/LF or other formatting normalization only if already project standard and strictly non-semantic; avoid touching runtime files solely for formatting during semantic-preservation work.

## 8. Python modules/tests/packages caution

Do not rename Python modules, tests, packages, package directories, or entry modules if doing so risks import/discovery, setuptools packaging, pytest discovery, adapter discovery, or external user workflows. In particular, treat these as discovery-sensitive and skip renames unless a complete non-breaking path synchronization is explicitly required and verified later:

- `Cli.py`, `Install.py`
- `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`
- `tests/test_*.py`, `tests/conftest.py`, `tests/__init__.py`
- `permission/default_policy.yaml`, plugin `plugin.yaml` files, `install.json`, `adapters/opencode/plugin.json`

If independent word capitalization would imply changing any of the above paths or identifiers, document the skip rather than forcing the rename.

## 9. Baseline notes for later optimization

- This audit file is the only intended file change in Step 1.
- Pre-existing uncommitted changes are part of the protected baseline and must survive unchanged unless a later planned step explicitly modifies them within no-go boundaries.
- Repository currently contains both tracked source/docs/config and ignored generated outputs. Later cleanup should focus only on ignored artifacts.
- File/code path renames are high risk in this Python package because import paths, setuptools discovery, pytest discovery, plugin manifests, and platform adapters all depend on stable names.

## 10. Step 2 independent-word initial capitalization naming audit

Scope: repository path-name audit only. No files or directories were renamed in this step. Generated and ignored artifacts such as `__pycache__/`, `*.pyc`, `.ruff_cache/**`, `.mypy_cache/**`, `.pytest_cache/**`, `build/lib/**`, `supermedicine.egg-info/**`, `.supermedicine/checkpoints/**`, and `.supermedicine/policies/audit.jsonl` are excluded from rename consideration because they are not source-of-truth paths.

Interpretation used for this audit:

- "Independent-word initial capitalization" means source-of-truth words would visually start with uppercase letters, for example `BaseAdapter.py` or `MedicalCitation/`, rather than `base_adapter.py` or `medical_citation/`.
- Python import/package/test discovery conventions, plugin IDs, manifests, adapter paths, CLI entry points, configuration paths, and documented user-facing paths have priority over capitalization aesthetics.
- Case-only renames are treated as risky on Windows and in Git because the current workspace is on a case-insensitive platform and because collaborators or CI may use case-sensitive filesystems.
- Conventional repository metadata names such as `.github`, `.gitignore`, `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `pyproject.toml`, and `requirements.txt` are intentionally conventional and are not recommended for capitalization-only cleanup.

### 10.1 Safe rename candidates

No low-risk source-of-truth rename candidates are recommended for Step 3.

Rationale: every non-capitalized tracked source path found is either a Python package/module/test path, a plugin/adapter/platform manifest path, a config/policy path, a conventional repository metadata path, or a static resource path under a plugin/adapter tree where code or manifests may load by literal path. The conservative outcome is to avoid behavior-affecting renames and preserve import/discovery/runtime conventions.

If Step 3 must include a capitalization rename, limit it to a separately reviewed documentation-only path outside Python packages, plugin trees, adapter trees, configuration trees, and conventional repository metadata. This audit found no such candidate that is both clearly non-conventional and clearly unreferenced.

### 10.2 Risky skipped rename mapping

The following mappings document what independent-word capitalization would imply, but they are intentionally skipped. They should not be executed unless a future plan explicitly accepts the migration risk and synchronizes every reference.

| Current path pattern | Capitalized target shape | Decision | Reference/import/config/docs/tests synchronization required | Skip reason |
| --- | --- | --- | --- | --- |
| `Cli.py` | `Cli.py` or `CLI.py` | Skip | `pyproject.toml` console script `supermedicine = "Cli:main"`, direct `python Cli.py` docs/tests, package metadata | Entry module and public workflow are discovery-sensitive; current spelling is already protected by packaging. |
| `Install.py` | `Install.py` | Skip | Direct `python Install.py` docs/tests and setuptools `py-modules` | Entry installer module is public workflow-sensitive; no rename needed. |
| `core/**` package directory | `Core/**` | Skip | All `core.*` imports, setuptools package discovery, tests, docs, generated package metadata | Python package import paths should remain lowercase; package-directory capitalization is high risk. |
| `core/config_center.py` | `core/ConfigCenter.py` | Skip | Imports, tests, docs, package metadata | Python module rename would change import path and violate common module naming convention. |
| `core/event_bus.py` | `core/EventBus.py` | Skip | Imports, tests, docs, package metadata | Python module rename would change import path. |
| `core/llm_client.py` and `core/llm_providers/**` | `core/LLMClient.py`, `core/LLMProviders/**` | Skip | Imports, tests, docs, provider discovery | Acronym/case migration is especially case-sensitive and import-sensitive. |
| `core/operation_guard.py`, `core/path_safety.py`, `core/plugin_registry.py`, `core/session_manager.py`, `core/workspace_tools.py` | `OperationGuard.py`, `PathSafety.py`, `PluginRegistry.py`, `SessionManager.py`, `WorkspaceTools.py` | Skip | Imports, tests, CLI/workspace docs | Python module import paths are behavior-sensitive. |
| `core/paper_import/**` | `core/PaperImport/**` | Skip | Imports, tests such as `test_paper_import_core.py`, paper CLI docs | Python subpackage import path and tests are discovery-sensitive. |
| `core/tui/**`, including `dialog_history.py` and `screens/**` | `core/TUI/**`, `DialogHistory.py`, `Screens/**` | Skip | TUI imports, tests, docs, entry functions | Python package/module import paths and TUI screen discovery should remain stable. |
| `permission/**`, including `default_policy.yaml` and `prompt_generator.py` | `Permission/**`, `DefaultPolicy.yaml`, `PromptGenerator.py` | Skip | Imports, `pyproject.toml` package data, `.supermedicine/policies/default.yaml`, tests, docs | Policy and package-data paths are config/runtime-sensitive. |
| `agents/**`, including `base_agent.py` and `state_machine.py` | `Agents/**`, `BaseAgent.py`, `StateMachine.py` | Skip | Imports, tests, orchestration docs | Agent package/module import paths are runtime-sensitive. |
| `adapters/**` package directory | `Adapters/**` | Skip | Imports, setuptools package discovery, tests, docs | Adapter package import path is public and discovery-sensitive. |
| `adapters/base_adapter.py` | `adapters/BaseAdapter.py` | Skip | Imports/tests across adapter implementations | Python module path is import-sensitive. |
| `adapters/claude_code/**` | `adapters/ClaudeCode/**` | Skip | Imports, tests, docs, adapter availability logic, `SKILL.md` path assumptions | Adapter subpackage name and platform path are behavior-sensitive. |
| `adapters/opencode/**` | `adapters/OpenCode/**` | Skip | Imports, tests, `plugin.json`, agent/skill installation docs, OpenCode platform discovery | Plugin/adapter path and manifest ecosystem are platform-sensitive. |
| `adapters/opencode/agents/*.md` lowercase hyphen names | `AlphaAnalyst.md`, `BetaReviewer.md`, `DeltaOrchestrator.md`, `GammaWriter.md`, `Supermedicine.md` | Skip | `plugin.json`, installer/docs/tests, platform agent IDs | Filenames may be IDs or installation targets; hyphenated lowercase is platform-conventional. |
| `adapters/opencode/skills/*.md` lowercase hyphen names | `HarnessMonitor.md`, `MedicalCitation.md`, `MedicalWriting.md`, `PythonStats.md`, `RSurvival.md`, `RagQuery.md` | Skip | `plugin.json`, adapter docs/tests, platform skill IDs | Skill filenames are platform-facing identifiers; capitalization could break discovery. |
| `plugins/**` package directory | `Plugins/**` | Skip | Imports, setuptools package discovery, plugin registry, tests | Plugin package path is discovery-sensitive. |
| `plugins/harness/**`, `plugins/rag/**`, `plugins/standards/**`, `plugins/tools/**` | `Harness/**`, `Rag/**`, `Standards/**`, `Tools/**` | Skip | Plugin registry, imports, manifests, tests, docs | Plugin discovery and import paths should remain lowercase/stable. |
| `plugins/*/plugin.yaml` | `Plugin.yaml` | Skip | Plugin registry file lookup, tests, docs | Manifest basename is convention-sensitive and likely loaded literally. |
| `plugins/standards/medical_citation/**` | `MedicalCitation/**` | Skip | Imports, plugin manifests/tests/docs | Python package and plugin action paths are import/discovery-sensitive. |
| `plugins/standards/medical_writing/**` | `MedicalWriting/**` | Skip | Imports, plugin manifests/tests/docs, checklist references | Python package/resource paths are import/discovery-sensitive. |
| `plugins/tools/python_stats/**` | `PythonStats/**` | Skip | Imports, plugin manifest, tests, docs | Python package and plugin path are discovery-sensitive. |
| `plugins/tools/r_survival/**` | `RSurvival/**` | Skip | Imports, plugin manifest, tests, docs, optional R/rpy2 fallback paths | Python package and plugin path are discovery-sensitive. |
| Plugin reference docs such as `provider-interface.md`, `consort-checklist.md`, `prisma-checklist.md`, `stard-checklist.md`, `strobe-checklist.md` | `ProviderInterface.md`, `ConsortChecklist.md`, `PrismaChecklist.md`, `StardChecklist.md`, `StrobeChecklist.md` | Skip | Plugin resource loading, docs/tests, package-data inclusion if later added | Static resources are inside plugin trees and may be loaded by literal path. |
| `tests/**`, including all `test_*.py` | `Tests/**`, `Test*.py` | Skip | Pytest `testpaths`, `python_files = ["test_*.py"]`, imports, CI/docs | Pytest discovery convention requires lowercase `tests` and `test_*.py`; preserve over aesthetics. |
| `.supermedicine/**` | `.SuperMedicine/**` | Skip | Runtime config discovery, `.gitignore`, docs/tests, user local state | Dot-directory is a runtime/config convention; capitalization would break local workflows. |
| `.github/workflows/ci.yml` | `.GitHub/Workflows/CI.yml` | Skip | GitHub Actions discovery, badges/docs | GitHub requires conventional `.github/workflows`; do not rename. |
| `.gitignore` patterns | Capitalized patterns | Skip | Ignore behavior for caches/build outputs/runtime artifacts | Pattern changes could expose generated artifacts or hide source; keep conventional. |
| `install.json` | `Install.json` | Skip | Installer/config docs/tests and package metadata | Manifest/config path may be loaded by literal name. |
| `pyproject.toml`, `requirements.txt` | `PyProject.toml`, `Requirements.txt` | Skip | Packaging tools, installers, CI, docs | Tooling expects conventional lowercase names. |
| Conventional root docs `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` | `Readme.md`, `Install.md`, `Architecture.md`, etc. | Skip | GitHub rendering, packaging metadata, docs links, possible `Architecture/` case/name confusion | Conventional uppercase metadata names are intentional; `ARCHITECTURE.md` also risks confusion with `Architecture/` directory. |

### 10.3 Case-only and path-conflict risk notes

- Windows/Git case-only renames are unreliable unless performed carefully with an intermediate temporary name. This audit step intentionally did not perform any rename.
- Mixed-case changes such as `core` -> `Core`, `plugins` -> `Plugins`, or `ARCHITECTURE.md` -> `Architecture.md` can appear unchanged to case-insensitive tooling while still changing behavior on Linux/macOS CI or package consumers.
- `ARCHITECTURE.md` and `Architecture/` are already close in spelling. Any rename toward `Architecture.md` increases ambiguity in shell completion, docs links, and case-insensitive tooling.
- Hyphen-to-PascalCase renames under OpenCode agent/skill paths may also change platform IDs if filenames are treated as identifiers.
- Generated/ignored mirrors under `build/lib/**`, `supermedicine.egg-info/**`, and caches must not be renamed because they should be cleaned/regenerated, not treated as source paths.

### 10.4 Reference synchronization requirements if a future safe candidate is introduced

For any future rename that is judged truly safe, synchronize all of the following in the same step:

- Python imports, dynamic imports, package discovery settings, package data, and console entry points.
- Tests, pytest discovery configuration, fixtures, and path literals.
- Plugin manifests (`plugin.yaml`, `plugin.json`), plugin/action IDs, adapter installation metadata, OpenCode/Claude Code agent and skill path references.
- Configuration files, `.gitignore` patterns, runtime `.supermedicine` references, documentation links, install instructions, and CI workflow paths.
- Git rename mechanics on Windows: use a two-step intermediate path for case-only changes and verify Git records the rename as intended.

### 10.5 Step 3 recommendation

Execute no capitalization renames in Step 3 unless a new, clearly documentation-only candidate outside sensitive trees is identified. Prefer Step 3 work to focus on low-risk generated/ignored artifact cleanup and prose-only documentation cleanup. Explicitly skip Python modules/packages/tests, adapter subpackages, plugin IDs/manifests/import paths, config paths, `.supermedicine`, `.gitignore` patterns, and conventional repository metadata names.

## 11. Step 3 conservative naming normalization execution result

Scope: conservative naming normalization and reference synchronization follow-up to the Step 2 audit. No repository paths were renamed in this step.

Execution result:

- Renames performed: none.
- Risky Python module/package/test paths were left unchanged, including `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, and `tests/**`.
- Risky adapter, plugin, manifest, configuration, runtime, and discovery-sensitive paths were left unchanged, including OpenCode/Claude Code adapter resources, plugin manifests, `.supermedicine/**`, `.github/workflows/**`, `.gitignore`, `install.json`, `pyproject.toml`, and `requirements.txt`.
- Conventional repository metadata and documentation filenames were left unchanged, including `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE`.
- No import, entry point, manifest, package-data, pytest-discovery, plugin-discovery, configuration, runtime-path, or documentation-link reference synchronization was required because no path rename occurred.

Rationale: Step 2 identified no low-risk source-of-truth rename candidate. The only apparent capitalization opportunities are tied to Python imports, setuptools/pytest discovery, plugin or adapter platform discovery, configuration/runtime paths, conventional tooling filenames, or case-only Git behavior on Windows. Preserving those paths avoids behavior changes and avoids unnecessary churn.

## 12. Step 4 duplicate and redundant content audit

Scope: repository duplicate/redundant content audit only. No source, runtime, configuration, documentation, generated, or ignored files were deleted or modified in this step except this audit section.

Inspection coverage:

- Exact file-content duplicates across the working tree, excluding `.git/` internals.
- Markdown paragraph-level duplicates in source-of-truth documentation and adapter/skill/agent/reference documents, excluding generated/build/cache trees.
- Repeated configuration/static fragments in YAML, JSON, TOML, and runtime checkpoint JSON files.
- Duplicate-looking Python imports/exports and generated mirrors, with code-duplication candidates recorded as skipped unless they are purely non-semantic and lint-level.
- Zero-byte files were checked; none were observed outside `.git/` internals.

### 12.1 Safe duplicate/redundant deletion candidates

No exact source-of-truth documentation, configuration, static text, export, empty-file, backup-file, or generated-file deletion candidate is recommended as a source/content duplicate in Step 5.

Rationale: duplicate-looking source/content items either carry distinct placement/context meaning, are runtime/config/discovery-sensitive, are intentionally repeated across agent/platform documents, are tests/examples/fixtures, or are code-level repetition that this audit is explicitly not allowed to abstract or rewrite. The only clearly removable duplicate material found is generated/ignored artifact material listed separately in section 12.2.

### 12.2 Generated/ignored artifacts eligible for cleanup in Step 5

The following generated or ignored artifacts are eligible for cleanup because they are not source-of-truth files and are reproducible runtime/build/cache outputs:

- `build/lib/**`: setuptools/build output mirror. Many files are exact byte-for-byte duplicates of source files such as `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, and `adapters/**`. Cleanup rationale: generated build mirror; source-of-truth copies live outside `build/`.
- `supermedicine.egg-info/**`: packaging metadata output from editable/build operations (`PKG-INFO`, `SOURCES.txt`, `entry_points.txt`, `requires.txt`, `top_level.txt`, `dependency_links.txt`). Cleanup rationale: generated package metadata; source-of-truth packaging input is `pyproject.toml` plus repository files.
- Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/`, and `*.pyc` under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`. Cleanup rationale: interpreter-generated bytecode caches.
- Tool caches: `.ruff_cache/**` and `.mypy_cache/**`. Cleanup rationale: linter/type-check cache data.
- Runtime local state: `.supermedicine/checkpoints/**` and `.supermedicine/policies/audit.jsonl`. Cleanup rationale: runtime execution/checkpoint/audit-log outputs, not source policy definitions.
- `.pytest_cache/**`: eligible by policy if accessible, but previous listing reported `Permission denied`; Step 5 should skip or document if deletion remains blocked.
- `Planning/NextSteps.md`: currently ignored local planning note, not tracked source-of-truth. Cleanup rationale: ignored local planning artifact; do not treat as repository documentation unless explicitly promoted/tracked first.

### 12.3 Duplicate-looking items intentionally skipped

The following duplicate-looking items are intentionally skipped and must not be deleted/merged by Step 5:

- `permission/default_policy.yaml` and `.supermedicine/policies/default.yaml` are exact byte-for-byte duplicates, but both are skipped. Rationale: `permission/default_policy.yaml` is package/source policy data, while `.supermedicine/policies/default.yaml` is the local runtime policy copy used by initialized workspaces; removing either could change packaging, runtime defaults, or user-local behavior.
- Repeated `rag.context.store`, `rag.context.retrieve`, `rag.external.query`, `security_level`, and similar YAML fragments inside the policy files are skipped. Rationale: permissions are role-specific entries under different agents; repeated action names do not imply semantic equivalence because scopes and agent contexts differ.
- The repeated OpenCode internal-role disclaimer paragraph in `adapters/opencode/agents/alpha-analyst.md`, `beta-reviewer.md`, `delta-orchestrator.md`, and `gamma-writer.md` is skipped. Rationale: each role document is independently installable/readable platform context; removing the repeated disclaimer from some files would weaken per-file safety/context metadata.
- The repeated install command block in `README.md` and `INSTALL.md` is skipped. Rationale: `README.md` quick-start content and `INSTALL.md` installation-guide content serve different documentation entry points; deleting one would reduce standalone usefulness.
- Repeated adapter/manifest fragments such as `"core_runtime_required": false` across `install.json` and `adapters/opencode/plugin.json` are skipped. Rationale: each manifest is consumed independently by different installer/platform surfaces.
- Repeated plugin manifest shapes across `plugins/**/plugin.yaml` are skipped. Rationale: shared schema fields are required per plugin and are not redundant files/fragments.
- Duplicate-looking test fixtures/assertions/import patterns in `tests/**` are skipped. Rationale: duplicate tests and fixtures may encode separate coverage intent and are explicitly protected by the hard constraints.
- Duplicate-looking Python imports found in `Cli.py`, `tests/test_integration.py`, `tests/test_permission_engine.py`, `tests/test_plugin_registry.py`, `tests/test_repo_hygiene.py`, and `tests/test_session_manager.py` are skipped. Rationale: these are code-level/local-import structure issues; even if a linter could flag some as non-semantic, this step must not rewrite code, and imports inside command/test scopes can preserve lazy-load or fixture-local meaning.
- Exact duplicates under `build/lib/**` are not source/content duplicates to merge into source. Rationale: they are generated mirrors and should be cleaned as generated artifacts, not used to drive source refactoring.
- Repeated runtime checkpoint JSON fields and repeated error/status messages under `.supermedicine/checkpoints/**` are skipped as content duplicates. Rationale: checkpoint files are generated runtime records; clean the whole generated checkpoint tree if desired rather than deduplicating individual records.
- Documentation overlap across `ARCHITECTURE.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, `Architecture/ExecutionRoadmap.md`, and this audit file is skipped unless exact duplicate prose is proven safe in a later doc-only pass. Rationale: these files have different audit/planning purposes and may intentionally restate boundaries for local completeness.
- Platform skill/reference documents under `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/references/**` are skipped. Rationale: repeated safety, boundary, or checklist wording may be required for standalone platform/resource consumption.

### 12.4 Step 5 recommendation

Step 5 should clean only generated/ignored artifacts listed in section 12.2. Do not delete or merge source-of-truth documentation/prose/configuration/code in Step 5 because this audit found no semantically identical source/content duplicate whose removal is clearly safe under the no-behavior-change constraints.

Recommended Step 5 cleanup boundaries:

- Remove generated/cache/build/package/runtime artifacts only: `build/lib/**`, `supermedicine.egg-info/**`, `__pycache__/`, `*.pyc`, `.ruff_cache/**`, `.mypy_cache/**`, `.supermedicine/checkpoints/**`, `.supermedicine/policies/audit.jsonl`, and accessible `.pytest_cache/**`.
- Optionally remove ignored `Planning/NextSteps.md` only if Step 5 confirms it remains a local ignored planning artifact and is not needed as an intended untracked source document.
- Do not remove `.supermedicine/config.yaml` or `.supermedicine/policies/default.yaml`; they are tracked/local configuration and policy files, not generated cleanup artifacts.
- Do not remove untracked intended source/documentation files listed in section 2, including `Architecture/PlatformIntegrationAudit.md` and `adapters/opencode/agents/supermedicine.md`; also preserve this audit file, `Architecture/RepositoryOptimizationAudit.md`.
- Do not perform code deduplication, import cleanup, policy consolidation, manifest consolidation, test deduplication, or documentation merge work in Step 5.

## 13. Step 5 generated-artifact cleanup execution result

Scope: cleanup of clearly generated, ignored, reproducible artifacts only, based on the Step 4 audit. No source-of-truth documentation, configuration, source code, tests, platform adapter resources, or duplicate-looking content was deleted or merged.

Cleanup performed:

- Removed `build/` generated build mirror when present.
- Removed `supermedicine.egg-info/` generated packaging metadata when present.
- Removed `.ruff_cache/` and `.mypy_cache/` tool caches when present.
- Removed `.supermedicine/checkpoints/` runtime checkpoint output when present.
- Removed `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Removed Python bytecode/cache artifacts, including `__pycache__/` directories and `*.pyc` files, when present.

Cleanup intentionally skipped or preserved:

- Preserved tracked source/docs/config/test files and source-of-truth package/config inputs.
- Preserved duplicate-looking source/content items listed in section 12.3, including `permission/default_policy.yaml`, `.supermedicine/policies/default.yaml`, OpenCode agent documents, install documentation, plugin manifests, tests, and platform skill/reference documents.
- Preserved `Architecture/RepositoryOptimizationAudit.md` and `adapters/opencode/agents/supermedicine.md` under the explicit hard constraints.
- Preserved ignored local-only `Planning/NextSteps.md` because the Step 5 instruction said to preserve ignored local-only `Planning/` unless explicitly known generated.
- Skipped `.pytest_cache/` cleanup because the directory remained inaccessible; Git continued to report `Permission denied` while listing ignored files.

Post-cleanup ignored-artifact note: after removing accessible generated artifacts, the remaining ignored status was limited to preserved `Planning/`, with `.pytest_cache/` still inaccessible due to permission denial.

Retry cleanup note: after verification regenerated ignored artifacts, Step 5 cleanup was re-run for `build/`, `supermedicine.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`, `__pycache__/` trees, and `*.pyc` files. The final ignored status again showed only preserved `Planning/` plus the inaccessible `.pytest_cache/` warning.

## 14. Step 6 conservative consistency optimization result

Scope: documentation-only consistency pass after the Step 1-5 repository optimization work. No runtime source, tests, configuration, manifests, policies, dependency versions, CLI behavior, API behavior, execution order, permissions, or generated artifacts were changed in this step.

Consistency changes made:

- Clarified the Step 5 recommendation wording in section 12.4 so `Architecture/RepositoryOptimizationAudit.md` is described as this audit file, while the section 2 untracked intended files remain `Architecture/PlatformIntegrationAudit.md` and `adapters/opencode/agents/supermedicine.md`.
- Recorded this Step 6 outcome in the repository optimization audit for reviewer traceability.

Risky optimizations intentionally skipped:

- No path renames were performed, including capitalization-only renames, Python package/module/test renames, adapter or plugin path renames, manifest renames, configuration path renames, or conventional repository metadata renames.
- No duplicate source, documentation, configuration, policy, manifest, adapter, plugin, or test content was deleted or merged.
- No code imports, command handlers, output protocols, result schemas, permission/security policies, default values, package metadata, dependency versions, or tests were changed.
- No additional generated-artifact cleanup was attempted in this step, including the previously inaccessible `.pytest_cache/` and the intentionally preserved ignored `Planning/` path.

## 15. Current repeated optimization pass baseline refresh at commit `0fe238b`

Date: 2026-05-27

Scope: documentation-only repository baseline refresh for the repeated optimization request. This section records the current Git/project observations directly from the current repository state, not from older Architecture audit text. No runtime/source behavior files are to be changed in this step; this audit document is the only intended modification.

### 15.1 Current branch, remote, HEAD, and initial worktree state

- Working directory: `D:\GIT\SuperMedicine`
- Current branch/tracking line from `git status --short --branch`: `## master...origin/master`
- Remote:
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (fetch)`
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (push)`
- Current HEAD / fresh baseline commit: `0fe238b5adc72ede496f6d3e34f1cb776bf8c05a`
- Current HEAD summary: `0fe238b fix: disable setup-python pip cache for CI`
- Current tracked/staged/untracked state before this documentation-only refresh:
  - `git status --short --branch` reported only `## master...origin/master`; no modified, staged, deleted, renamed, or untracked non-ignored files were shown.
  - `Architecture/RepositoryOptimizationAudit.md` is tracked at mode `100644` and is the only intended file to update for this step.

### 15.2 Project type, major structure, and discovery-sensitive entry points

- Project type: Python package/application named `supermedicine`, version `0.3.0b0`, with setuptools build backend (`setuptools>=68.0`, `wheel`) and Python requirement `>=3.10`.
- Runtime model: standalone Python medical research agent framework with optional OpenCode, Claude Code, and standalone adapter surfaces around the core.
- Top-level structure currently observed:
  - Repository metadata/config: `.gitignore`, `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/ci.yml`.
  - Runtime/local config: `.supermedicine/` with tracked config/policy inputs plus ignored runtime outputs.
  - Documentation/governance: `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `Architecture/`, and `docs/`.
  - Python entry modules: `Cli.py`, `Install.py`.
  - Runtime packages: `core/`, `permission/`, `agents/`, `plugins/`, `adapters/`.
  - Tests: `tests/`.
  - Local/generated/ignored paths currently present: `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/` (inaccessible), `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`, and `Planning/`.
- Discovery-sensitive entry points and paths:
  - Console script: `supermedicine = "Cli:main"`.
  - Setuptools top-level modules: `py-modules = ["Cli", "Install"]`.
  - Setuptools package discovery: `core*`, `permission*`, `agents*`, `plugins*`, `adapters*`.
  - Package data: `permission/default_policy.yaml`.
  - Pytest discovery: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, and `addopts = "-p no:cacheprovider"`.
  - Public direct CLI/documented commands include `python Install.py --init`, `python Cli.py status`, `python Cli.py run ...`, `supermedicine status`, `supermedicine init`, `supermedicine run ...`, `supermedicine workspace ...`, `supermedicine paper ...`, `supermedicine experience ...`, and `supermedicine tui`.
  - Platform/discovery paths include `install.json`, `adapters/opencode/plugin.json`, `adapters/opencode/agents/**`, `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/plugin.yaml`.

### 15.3 Available test, lint, type, build, and smoke commands

Commands inventoried from `pyproject.toml`, CI, and documentation for later Tester/verification steps only; Coder must not run test commands in this audit step.

- Environment/development install: `python -m pip install -e ".[dev]"`.
- Runtime install: `pip install -e .`.
- Optional R backend install: `pip install -e ".[r]"`.
- Lint gate: `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Repository hygiene test gate: `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`.
- Full test suite gate: `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`.
- Documented local test command through CLI: `python Cli.py test`.
- Documented direct local test command: `pytest tests/ -v`.
- Wheel smoke/build gate: `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>`.
- Source distribution smoke/build gate: `python -m build --sdist --outdir dist`.
- Type gate: `python -m mypy . --cache-dir <temp-mypy-cache>`.
- CLI smoke commands documented for later verification: `python Install.py --init`, `python Cli.py status`, `python Cli.py run "..."`, `supermedicine status`, `supermedicine init`, `supermedicine run ...`, workspace/paper/experience commands, and `supermedicine tui`.

### 15.4 Tracked, untracked, ignored, and generated artifact observations

- Tracked source-of-truth state at initial repeated-pass baseline: no tracked modifications were present before this audit edit.
- Untracked non-ignored state at initial repeated-pass baseline: none reported by Git before this audit edit.
- Ignored/generated artifacts observed by `git status --short --ignored` and `git ls-files --ignored --others --exclude-standard`:
  - Tool caches: `.mypy_cache/**`, `.ruff_cache/**`.
  - Inaccessible pytest cache: `.pytest_cache/` caused `warning: could not open directory '.pytest_cache/': Permission denied`.
  - Runtime outputs: `.supermedicine/checkpoints/**`, `.supermedicine/policies/audit.jsonl`.
  - Local planning note/tree: `Planning/`, including ignored `Planning/NextSteps.md`.
  - Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/` directories, and `*.pyc` files under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`.
- Cleanup policy for any later planned step:
  - Remove only clearly ignored, reproducible build/cache/runtime products when cleanup is explicitly requested and scoped.
  - Do not remove tracked source, docs, tests, configs, policies, manifests, package inputs, adapter resources, plugin resources, or runtime default policy/config source-of-truth files.
  - Treat `.pytest_cache/` permission denial as a boundary to document and skip rather than force.
  - Preserve `Planning/` unless a later step explicitly confirms it is disposable local-only material.
  - Do not mix generated-artifact cleanup with source/runtime behavior changes.

### 15.4.1 Complete tracked Markdown inventory at current baseline

The current output of `git ls-files "*.md"` contains 29 tracked Markdown files:

- `ARCHITECTURE.md`
- `Architecture/ExecutionRoadmap.md`
- `Architecture/OptimizationAudit.md`
- `Architecture/PhaseImplementationPlan.md`
- `Architecture/PlatformIntegrationAudit.md`
- `Architecture/RepositoryOptimizationAudit.md`
- `Architecture/WorkspaceTuiRagGuide.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `INSTALL.md`
- `README.md`
- `SECURITY.md`
- `adapters/claude_code/SKILL.md`
- `adapters/opencode/agents/alpha-analyst.md`
- `adapters/opencode/agents/beta-reviewer.md`
- `adapters/opencode/agents/delta-orchestrator.md`
- `adapters/opencode/agents/gamma-writer.md`
- `adapters/opencode/agents/supermedicine.md`
- `adapters/opencode/skills/harness-monitor.md`
- `adapters/opencode/skills/medical-citation.md`
- `adapters/opencode/skills/medical-writing.md`
- `adapters/opencode/skills/python-stats.md`
- `adapters/opencode/skills/r-survival.md`
- `adapters/opencode/skills/rag-query.md`
- `plugins/rag/references/provider-interface.md`
- `plugins/standards/medical_writing/references/consort-checklist.md`
- `plugins/standards/medical_writing/references/prisma-checklist.md`
- `plugins/standards/medical_writing/references/stard-checklist.md`
- `plugins/standards/medical_writing/references/strobe-checklist.md`

### 15.5 Hard no-go semantic preservation boundaries for the repeated pass

Absolute priority: do not change existing functionality or code meaning, even when code appears unused, duplicated, insecure, stylistically inconsistent, or suboptimal. Repeated optimization must remain conservative and must revalidate assumptions against current files.

- Preserve public API behavior, import paths, module/package names, class/function names, signatures, return shapes, exception behavior, and side effects.
- Preserve CLI command names, arguments, defaults, prompt/output meanings, exit behavior, console-script mapping, and direct `python Cli.py` / `python Install.py` workflows.
- Preserve package metadata semantics, version meaning, setuptools package discovery, package data inclusion, extras, dependency constraints, and build inputs.
- Preserve plugin IDs, plugin manifests, action IDs, schemas, discovery rules, resource paths, and deterministic plugin output meaning.
- Preserve adapter and platform behavior for OpenCode, Claude Code, and standalone surfaces, including degraded/unavailable states, manifest identities, agent/skill filenames, and install metadata.
- Preserve permission/security policy meanings, default allow/deny behavior, audit semantics, operation guard/path-safety behavior, and prompt-generation safety guidance. Do not “fix” a security concern if the fix changes behavior without explicit planning and verification.
- Preserve medical/statistical output meanings, R/rpy2 fallback behavior, RAG provider contracts, workspace/paper/experience workflows, TUI behavior, and deterministic fixtures.
- Preserve tests' coverage intent and assertion meaning; do not deduplicate or rewrite tests unless a later plan proves a purely mechanical non-semantic synchronization is required.
- Preserve configuration names, default values, `.supermedicine` runtime paths, policy filenames, local-state conventions, and ignored-artifact boundaries.
- Naming/capitalization cleanup must skip risky import/discovery/tooling/platform paths. Document risky capitalization candidates instead of forcing case-only or convention-breaking renames.
- Duplicate reduction is allowed only for semantically identical material whose removal provably loses no local context, warning, standalone usefulness, consumer contract, or coverage intent.
- Do not rename Python packages/modules/tests, plugin manifests, adapter resources, config paths, `.github` paths, `.supermedicine` paths, or conventional packaging files for aesthetics.

### 15.6 Repeated-pass baseline notes

- This is a repeated optimization baseline refresh at commit `0fe238b5adc72ede496f6d3e34f1cb776bf8c05a`; prior audit findings are useful history but are not sufficient authority for new edits.
- The current initial state was clean for tracked and non-ignored untracked files; only ignored/generated/local artifacts were observed before this audit edit.
- The prior generated-artifact cleanup conclusion must be rechecked because caches and runtime artifacts have reappeared after later activity.
- The previous naming/capitalization conclusion remains a high-risk area to revalidate rather than assume: Python imports, setuptools/pytest discovery, plugin/platform manifests, and Windows case-only rename behavior make most path capitalization changes unsafe.
- Any later intended changes should keep the repository clean, avoid runtime/source behavior changes, and be committed/pushed only after Brain/Tester verification confirms the planned scope.

## 16. Repeated-pass Step 2 semantic-preserving deep audit

Date: 2026-05-26

Scope: fresh audit-only pass over the current working tree after the repeated-pass baseline section. This pass re-scanned the requested documentation, `Architecture/**`, `Planning/**`, adapters, plugins, agents, core, permission, tests, install manifest, packaging config, and ignore rules for duplicate docs/descriptions, generated artifacts, naming/capitalization risk, hardcoded path references in tests/docs/manifests/imports, and platform adapter declaration paths. No source/runtime behavior, deletion, rename, staging, commit, push, tag, release, publish, upload, or generated-artifact cleanup was performed.

### 16.1 Concrete cleanup, formatting, and documentation de-duplication candidates

- `Architecture/RepositoryOptimizationAudit.md`: contains accumulated historical pass sections and repeated boundary language by design. Candidate: if a future docs-only optimization is explicitly requested, add a short index/table of prior optimization passes or move older closed-pass details into an archival document. Skip for now because this file is the authoritative audit trail and deleting/relocating sections could lose review context.
- `README.md` and `INSTALL.md`: both include clone/install/init/status/run snippets and optional platform/R notes. Candidate: in a future docs-only pass, keep `README.md` as quick-start and make `INSTALL.md` the detailed install guide with cross-links to reduce repeated prose. Skip now because each document remains useful as a standalone entry point and command blocks differ by audience (`pip install -e .` quick path versus `pip install -e ".[dev]"` development path).
- `README.md`, `ARCHITECTURE.md`, and `Architecture/PlatformIntegrationAudit.md`: all restate the core-independent plus optional OpenCode/Claude Code add-on model. Candidate: future docs-only optimization can cross-link to one canonical architecture/support-status section. Skip now because README is user-facing, `ARCHITECTURE.md` is architecture-facing, and `PlatformIntegrationAudit.md` is an audit artifact with historical evidence.
- `Architecture/ExecutionRoadmap.md`, `Architecture/PhaseImplementationPlan.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, and this file: duplicate-looking no-go/boundary/checklist language appears intentional for local audit completeness. Candidate: future docs-only pass can add forward/back links to reduce navigation friction, not delete evidence.
- `adapters/opencode/agents/alpha-analyst.md`, `beta-reviewer.md`, `gamma-writer.md`, and `delta-orchestrator.md`: repeated internal-role/frontmatter/safety positioning is a possible prose de-dup candidate only if OpenCode consumption allows shared includes. Skip because each role document is independently installable and platform-readable.
- `adapters/opencode/skills/*.md` and `adapters/claude_code/SKILL.md`: repeated capability, permission, and medical-boundary descriptions are possible docs-only consolidation candidates. Skip because these are platform-facing standalone documents where local context is important.
- `plugins/standards/medical_writing/references/*-checklist.md`: checklist files are intentionally separate source references; do not merge. Candidate only for docs index/navigation if future users need a consolidated checklist map.
- `Planning/NextSteps.md`: ignored local planning note is a concrete cleanup candidate only if a later cleanup step confirms it is disposable. Skip now because the user explicitly requested audit-only recording and previous scope preserved ignored Planning material unless explicitly known generated.

### 16.2 Naming capitalization and path-case risk findings

- No safe rename/capitalization candidate was found in the requested source-of-truth scope. Current lowercase package/module paths (`core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`) match Python import and packaging conventions and are referenced throughout code, tests, docs, manifests, and package discovery.
- `Cli.py` and `Install.py` remain intentionally capitalized entry modules. Skip any further rename because `pyproject.toml` declares `py-modules = ["Cli", "Install"]`, the console script points to `Cli:main`, and docs/tests use direct `python Cli.py` / `python Install.py` workflows.
- `ARCHITECTURE.md` and `Architecture/` remain a path-case ambiguity risk on case-insensitive tooling. Skip rename because root uppercase documentation names are conventional, `Architecture/` contains multiple audit/planning docs, and `Architecture.md` would increase ambiguity with the directory.
- `adapters/claude_code/**` and `adapters/opencode/**` are platform/discovery/import-sensitive. Skip capitalization to `ClaudeCode` or `OpenCode` because install manifest paths, tests, imports, adapter docs, and platform metadata reference the existing paths.
- OpenCode declaration files under `adapters/opencode/agents/*.md` and `adapters/opencode/skills/*.md` use lowercase hyphenated filenames. Skip PascalCase/case-only renames because `adapters/opencode/plugin.json`, tests, install docs, and potential platform IDs depend on those literal paths.
- Plugin directories and manifests (`plugins/rag/**`, `plugins/harness/**`, `plugins/tools/python_stats/**`, `plugins/tools/r_survival/**`, `plugins/standards/medical_writing/**`, `plugins/standards/medical_citation/**`, and `plugin.yaml`) are import/discovery-sensitive. Skip capitalization or manifest basename changes because `PluginRegistry` scans `plugin.yaml`, tests assert entries exist, and package discovery includes `plugins*`.
- Test paths (`tests/**`, `tests/test_*.py`, `tests/conftest.py`, `tests/__init__.py`) are pytest-discovery-sensitive and contain hardcoded path assertions for manifests/docs/adapters. Skip renames because `pyproject.toml` defines `testpaths = ["tests"]` and `python_files = ["test_*.py"]`.
- `.supermedicine/**`, `.gitignore`, `pyproject.toml`, `install.json`, `.github/workflows/**`, and conventional root docs remain tooling/config-sensitive. Skip aesthetics-driven capitalization because these names are loaded by tooling, runtime config, tests, docs, or platform installers.

### 16.3 Generated/cache artifacts observed and cleanup plan

Observed ignored/generated artifacts in the fresh pass:

- Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/` directories, and `*.pyc` under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`.
- Build/package outputs: `build/lib/**` source mirror and `supermedicine.egg-info/**` packaging metadata.
- Tool caches: `.mypy_cache/**` and `.ruff_cache/**`.
- Pytest cache: `.pytest_cache/` still produced `Permission denied` when Git tried to inspect ignored files.
- Runtime/local outputs: `.supermedicine/checkpoints/**` and `.supermedicine/policies/audit.jsonl`.
- Ignored local planning note: `Planning/NextSteps.md`.

Cleanup plan for a later explicit cleanup step only:

- Remove generated/cache/build/package/runtime artifacts that are already ignored and reproducible: `__pycache__/`, `*.pyc`, `build/`, `supermedicine.egg-info/`, `.mypy_cache/`, `.ruff_cache/`, `.supermedicine/checkpoints/`, and `.supermedicine/policies/audit.jsonl`.
- Attempt accessible `.pytest_cache/` cleanup only if permissions allow; otherwise document and skip without forcing permissions.
- Preserve tracked `.supermedicine/config.yaml` and `.supermedicine/policies/default.yaml`; they are bootstrap/config source-of-truth, not generated cleanup targets.
- Preserve `Planning/NextSteps.md` unless a later step explicitly decides ignored local planning notes are disposable.
- Do not clean, delete, rename, or merge any tracked source, docs, tests, manifests, policies, plugin references, or adapter resources as part of generated-artifact cleanup.

### 16.4 Duplicate-looking items skipped with rationale

- `permission/default_policy.yaml` and `.supermedicine/policies/default.yaml`: duplicate-looking policy content is skipped because the first is package data and the second is local runtime bootstrap policy.
- Repeated policy action names such as RAG, tool, workspace, and Claude scopes are skipped because rule meaning depends on agent, action, effect, and hard-limit context.
- `install.json` and `adapters/opencode/plugin.json`: overlapping optional-add-on fields and capability language are skipped because they serve different consumers: repository install metadata versus OpenCode plugin metadata.
- `pyproject.toml`, `install.json`, README release wording, and `CHANGELOG.md`: version labels intentionally differ between public release label `Beta0.3.0` and PEP 440 package metadata `0.3.0b0`; do not normalize away the documented distinction.
- Tests under `tests/**`: duplicate-looking path literals, fixture setup, and adapter assertions are skipped because they protect specific docs/manifests/import paths and discovery boundaries.
- Hardcoded test path checks in `tests/test_repo_hygiene.py`, `tests/test_opencode_adapter.py`, and `tests/test_claude_code_adapter.py` are skipped because they intentionally enforce install manifest paths, adapter resource paths, skill/agent paths, package entry points, and platform declaration contracts.
- Python imports from `core`, `permission`, `agents`, `plugins`, and `adapters` are skipped because import paths are behavior-sensitive. Apparent repeated imports in CLI command handlers and tests may preserve lazy import behavior, optional dependency boundaries, or local fixture meaning.
- Repeated command examples using `python Cli.py test` or direct pytest commands in docs are skipped in this audit step. They may be docs-only candidates later, but removing them now could reduce standalone guide usefulness.
- Generated mirrors under `build/lib/**` are skipped as source duplicates; they should be cleaned as generated artifacts, not used as a basis for source deletion or refactoring.

### 16.5 Potentially safe docs-only optimization candidates

- Add a short documentation navigation index linking `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `Architecture/WorkspaceTuiRagGuide.md`, `Architecture/PlatformIntegrationAudit.md`, and `Architecture/RepositoryOptimizationAudit.md` so repeated boundary material is easier to locate without deleting content.
- In `README.md`, convert detailed install/R/platform explanations into brief summaries that link to `INSTALL.md`, if a future user-facing documentation pass accepts the tradeoff.
- In `INSTALL.md`, add a short pointer back to README quick start and architecture support matrix instead of restating every platform boundary in full.
- In `Architecture/RepositoryOptimizationAudit.md`, add an audit-pass index at the top to reduce scrolling through historical sections. This is documentation-only and preserves the audit record.
- In `Architecture/PlatformIntegrationAudit.md`, mark older pre-remediation findings as historical in a compact table while preserving exact evidence and final status. This is docs-only but should be done carefully to avoid losing audit traceability.

### 16.6 Step 2 repeated-pass conclusion

No runtime/source behavior change, deletion, rename, or generated-artifact cleanup should be performed in this Step 2 audit. The concrete later-action candidates are limited to generated-artifact cleanup and cautious docs-only navigation/de-duplication. All naming/capitalization candidates in Python packages, tests, manifests, adapter resources, plugin resources, config paths, package metadata, and platform declarations are skipped due to import, discovery, tooling, platform, or case-sensitivity risk.

## 17. Repeated-pass Step 3 generated/cache cleanup result

Date: 2026-05-26

Scope: cleanup of clearly generated, ignored, reproducible cache/build/runtime artifacts identified in the repeated-pass audit. No source, documentation, configuration, tests, platform resources, package inputs, manifests, tracked policy defaults, or `Planning/` files were deleted or modified.

Cleanup result:

- Removed `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Re-ran cleanup for accessible `.mypy_cache/`, `.ruff_cache/`, `.supermedicine/checkpoints/`, `build/`, `supermedicine.egg-info/`, all `__pycache__/` trees, and `*.pyc` artifacts using normal workspace permissions; the bytecode cleanup was retried recursively after remaining accessible bytecode artifacts were reported.
- Attempted cleanup of `.pytest_cache/` within normal workspace permissions; no accessible cache entries were available through the repository file search at cleanup time.
- Final cleanup state for the requested accessible generated artifacts: no accessible `__pycache__/` trees, `*.pyc` files, `build/`, `supermedicine.egg-info/`, `.mypy_cache/`, `.ruff_cache/`, or `.supermedicine/checkpoints/` artifacts were present through the cleanup file search after retry 2 execution.

Preserved intentionally:

- Tracked source, docs, config, tests, package metadata inputs, adapter resources, plugin resources, `.supermedicine/config.yaml`, and `.supermedicine/policies/default.yaml`.
- Ignored local `Planning/` content, because this cleanup step explicitly preserves `Planning/` unless confirmed disposable.
- `.gitignore`, because the existing ignore rules already cover Python bytecode, build/package outputs, lint/type/test/coverage caches, SuperMedicine runtime artifacts, external assistant local artifacts, and local planning notes.

Inaccessible artifacts:

- `.pytest_cache/` had previously produced permission-denied warnings during Git/listing operations. During this cleanup pass, normal file search did not expose accessible entries and the cleanup command was limited to normal permissions; any still-inaccessible pytest cache material is treated as skipped rather than force-deleted.

## 18. Repeated-pass Step 4 independent-word initial capitalization naming execution result

Date: 2026-05-26

Scope: execution follow-up for the repeated-pass Step 2 naming/capitalization audit after generated/cache cleanup. This step was limited to deciding whether any independent-word initial capitalization path rename was now safe and, if so, synchronizing references. No behavior, import, entry point, manifest, configuration, runtime path, test discovery, platform declaration, staging, commit, push, tag, release, publish, or upload action was performed.

Renames performed:

- None.

Skipped/rationale:

- No newly obvious docs-only path rename was found that was both unreferenced and no-risk.
- Python modules, packages, tests, and entry files remained unchanged, including `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, and `tests/**`, because those names are import, packaging, pytest discovery, or public workflow sensitive.
- Adapter/plugin/platform paths remained unchanged, including `adapters/opencode/**`, `adapters/claude_code/**`, OpenCode agent/skill filenames, `adapters/opencode/plugin.json`, and `plugins/**/plugin.yaml`, because those paths can be referenced by manifests, installers, tests, documentation, or platform discovery.
- Tooling, manifest, configuration, runtime, and conventional metadata paths remained unchanged, including `.github/workflows/**`, `.supermedicine/**`, `.gitignore`, `install.json`, `pyproject.toml`, `requirements.txt`, `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE`, because these names are conventional or consumer/tooling sensitive.
- Case-only or aesthetics-only renames were skipped because the current Windows workspace and Git case handling make such changes risky, and Step 2 already found no low-risk source-of-truth capitalization candidate.

Reference synchronization result:

- No import, entry point, package discovery, package data, pytest discovery, manifest, adapter/plugin declaration, configuration, runtime path, documentation link, or platform reference synchronization was required because no path rename occurred.

Execution conclusion: Step 4 intentionally records a no-rename result. This preserves the source-of-truth path contracts established by the repeated-pass Step 2 audit and avoids unsafe churn in import/discovery/tooling/platform-sensitive files.

## 19. Repeated-pass Step 5 safe duplicate reduction result

Date: 2026-05-26

Scope: documentation-only duplicate-reduction execution based on the repeated-pass Step 2 audit. The pass was limited to semantically identical, non-functional prose where context could be preserved by cross-reference. No code, tests, configuration, manifests, permission policies, examples, warnings, platform capability descriptions, CLI/API outputs, generated artifacts, staging, commit, push, tag, release, publish, or upload actions were performed.

Duplicate reductions performed:

- Added the `Audit pass index` near the top of this document as a cross-reference layer for sections 1-19. Semantic-equivalence rationale: the index summarizes existing audit sections without replacing their evidence, decisions, warnings, or historical context; future updates can link to the index rather than repeating long prior explanations.
- Recorded this Step 5 outcome in this section so future repeated passes have a single place to find the safe duplicate-reduction decision and the skipped-item rationale.

Content deletion or merge result:

- No existing source-of-truth documentation/prose was deleted or merged. The audit did not find exact duplicate documentation whose removal would preserve all standalone install, platform, safety, warning, example, and historical-audit context.
- No executable paths were affected: `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, `tests/**`, manifests, package metadata, policies, and runtime configuration paths remained unchanged.

Skipped duplicate-looking items and rationale:

- `README.md` and `INSTALL.md` install snippets were preserved. Rationale: the commands overlap but serve different entry points and audiences; README is a quick-start path while INSTALL is a standalone installation guide with prerequisites, verification, troubleshooting, optional R support, and platform-adapter context.
- README/architecture/platform-support overlap across `README.md`, `ARCHITECTURE.md`, and `Architecture/PlatformIntegrationAudit.md` was preserved. Rationale: the repeated core-independent plus optional-adapter model appears in user-facing, architecture-facing, and audit-evidence contexts; deleting any copy could reduce standalone usefulness or audit traceability.
- Boundary/checklist language across `Architecture/ExecutionRoadmap.md`, `Architecture/PhaseImplementationPlan.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, and this audit was preserved. Rationale: repeated constraints are local guardrails for separate planning/audit documents, not exact redundant paragraphs safe to remove.
- OpenCode agent role documents under `adapters/opencode/agents/*.md` were preserved. Rationale: each role document is independently installable/platform-readable, so repeated safety/frontmatter/context wording must remain local to each file.
- Platform skill and reference documents under `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/references/**` were preserved. Rationale: repeated medical-boundary, permission, and checklist language supports standalone consumption and should not be centralized away without platform include semantics.
- Policy, manifest, test, example, command, and generated-mirror duplicate-looking content was preserved or left to generated-artifact cleanup rules. Rationale: these items are functional, discovery-sensitive, coverage-sensitive, consumer-specific, or generated outputs rather than safe docs-only duplicate prose.

Step 5 conclusion: the only strictly safe duplicate reduction in this pass was additive navigation/indexing inside the audit itself. All deletion/merge candidates were skipped because semantic identity and context preservation could not be proven under the hard constraints.

## 20. Repeated-pass Step 6 repository format and text hygiene result

Date: 2026-05-26

Scope: low-risk documentation text hygiene only, limited to this audit document. No source code, tests, configuration, manifests, dependency metadata, generated artifacts, staging, commit, push, tag, release, publish, or upload actions were performed.

Hygiene changes made:

- Added the repeated-pass Step 6 result to the audit pass index so the document heading/navigation pattern remains consistent for sections 1-20.
- Recorded this Step 6 outcome in a dedicated audit section with the same result-oriented heading style used by the repeated-pass execution sections.
- Kept the edit docs-only and minimal; no functional, configuration, test, manifest, policy, package, or runtime text was changed.

Skipped risky formatting:

- No repository-wide formatter, markdown formatter, import sorter, lint auto-fixer, line-ending normalization, or whitespace rewrite was run.
- No Python, TOML, JSON, YAML, manifest, policy, test, package metadata, generated artifact, or runtime-local file was modified for formatting.
- No broad markdown reflow, heading renumbering, prose deletion, duplicate-content merge, path rename, or capitalization cleanup was attempted because such churn could obscure semantic review.

Step 6 conclusion: the repeated-pass format work was intentionally limited to audit-document traceability and minimal text hygiene. Risky formatting and any change that could alter behavior, configuration meaning, test intent, package metadata, platform discovery, or review clarity was skipped.

## 21. Repeated-pass Step 7 repository hygiene test coverage assessment

Date: 2026-05-26

Scope: audit-only assessment of whether additional non-invasive repository hygiene tests are needed after the repeated optimization pass. No runtime/source behavior, test behavior, configuration, manifest, dependency metadata, generated artifact, staging, commit, push, tag, release, publish, or upload action was performed.

Existing repository hygiene coverage reviewed:

- `tests/test_repo_hygiene.py` already protects against tracking generated or forbidden artifacts, including bytecode, build/dist/package metadata output, test/lint caches, runtime audit logs, runtime checkpoints, external platform local configuration directories, and unexpected tracked `.supermedicine` content.
- Existing tests already verify `.gitignore` coverage for runtime/cache/external-platform artifacts without requiring external network access or platform runtimes.
- Existing tests already assert install manifest platform entries stay under adapter paths, point to existing adapter resources, and remain synchronized with adapter support declarations.
- Existing tests already enforce the single user-facing platform agent model, reject legacy platform agent names in platform-facing docs/resources, validate OpenCode declared entry skills and agents, and protect key OpenCode platform capability declarations.
- Existing tests already cover release label/package metadata synchronization, plugin manifest entry paths, console-script importability, and packaging of the top-level console-script module.

Test coverage decision:

- No additional test coverage was added in Step 7.
- Rationale: the repeated optimization changes since Step 3 were documentation/audit-only and did not introduce new runtime/source behavior, install paths, package discovery paths, manifest paths, platform agent names, version labels, generated-artifact categories, or forbidden-file categories. Adding another hygiene assertion would duplicate already covered invariants and create test churn without protecting a newly changed contract.
- If a later pass changes runtime/source paths, manifests, generated-artifact policy, installer behavior, adapter resources, or package metadata, add the smallest focused non-invasive hygiene test at that time. Until such a contract changes, the current tests are sufficient for the repository hygiene risks touched by this pass.

Step 7 conclusion: `tests/test_repo_hygiene.py` was intentionally left unchanged. The audit records why existing non-invasive coverage is sufficient for this docs-only repeated optimization pass, while preserving the rule that future functional/path/manifest changes should receive focused test coverage.

## 22. Repeated-pass Step 9 final diff review and semantic-preservation confirmation

Date: 2026-05-26

Scope: final repeated-pass review after Step 8 validation. This step was limited to cleaning regenerated artifacts that were safe to remove with normal workspace permissions, inspecting the final working-tree diff, and recording semantic-preservation confirmation in this audit document. No staging, commit, push, tag, release, publish, upload, runtime/source edit, configuration edit, test edit, manifest edit, dependency edit, policy edit, or package metadata edit was performed.

Generated artifact cleanup result:

- Rechecked and found no accessible `build/`, `supermedicine.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, `__pycache__/`, `*.pyc`, or `.supermedicine/checkpoints/` artifacts at cleanup time.
- Removed regenerated `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Preserved ignored `Planning/` content as requested and because it is not confirmed disposable generated output.
- Preserved inaccessible `.pytest_cache/` material; prior passes observed permission-denied behavior and this final cleanup avoided forcing permissions or deleting source/docs/config/tests.

Final diff inspection:

- `git status --short` reported only `Architecture/RepositoryOptimizationAudit.md` as modified after cleanup.
- `git diff --name-status` reported only `M Architecture/RepositoryOptimizationAudit.md`.
- `git diff --stat` reported only `Architecture/RepositoryOptimizationAudit.md` with documentation insertions.
- Git emitted the existing line-ending warning for this audit file (`LF will be replaced by CRLF the next time Git touches it`); this is recorded as workspace line-ending metadata noise and not a semantic runtime/config/test/manifest change.

Semantic-preservation confirmation:

- Runtime and source files remained unchanged in this Step 9 pass: `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, and `adapters/**` were not edited.
- Configuration, policy, manifest, dependency, package, CI, and platform-declaration inputs remained unchanged in this Step 9 pass, including `.supermedicine/config.yaml`, `.supermedicine/policies/default.yaml`, `.gitignore`, `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/**`, and `adapters/opencode/plugin.json`.
- Test files remained unchanged in this Step 9 pass, including `tests/**`.
- Documentation changes in this step were limited to this audit trail and only record cleanup/diff-review evidence; they do not alter documented commands, runtime behavior, platform contracts, package metadata, permissions, tests, or source semantics.

Step 9 conclusion: final repeated-pass diff scope is intentionally restricted to `Architecture/RepositoryOptimizationAudit.md`. Accessible regenerated artifacts were cleaned or confirmed absent, inaccessible `.pytest_cache/` and ignored `Planning/` content were preserved, and no runtime/source/config/test/manifest semantics changed.

## 23. Step 2 Markdown rewrite and deduplication strategy

Date: 2026-05-27

Scope: strategy-only pass over the 29 tracked Markdown files listed in section 15.4.1. This section defines the concrete rewrite and deduplication rules for a later Markdown-only pass. No code/runtime files, configuration files, manifests, tests, package metadata, generated artifacts, staging, commit, push, tag, release, publish, or upload actions are part of this strategy step.

### 23.1 Rewrite goal and preservation rule

The goal is conservative Markdown prose cleanup while preserving every original functional meaning, warning, command, identifier, platform contract, checklist item, and audit trace. The later rewrite pass should prefer the smallest local text edit that improves consistency or removes provably redundant prose. If a phrase is ambiguous, consumer-facing, or possibly asserted by tests/platform tooling, leave it unchanged and record the skip rather than normalize it.

### 23.2 Forbidden transformations

Do not alter any of the following during Markdown rewriting or deduplication:

- Fenced code blocks and inline code literals, including commands, Python examples, JSON/YAML/TOML snippets, Mermaid diagrams, shell paths, and API examples.
- Frontmatter keys or values in adapter/agent/skill Markdown, including `name`, `description`, `agent_id`, `user_facing`, `internal_role_context`, `role`, and `state_machine_stage`.
- Filenames, path literals, import paths, module names, package names, plugin paths, manifest paths, policy paths, workspace paths, and anchor targets/links.
- CLI commands, options, positional arguments, placeholders, environment variables, and console-script names, including `supermedicine`, `python Cli.py`, `python Install.py`, `--workspace`, `--confirm`, `--confirm-enrich`, `--params-json`, `--params-file`, and `PATH`.
- Package names, dependency names, platform names, manifest IDs, plugin/action IDs, tool IDs, API names, method/function/class names, result keys, metadata labels, semantic status labels, version labels, release labels, and test/quality command text.
- Medical reporting checklist item wording, citation/reference text, standard names, acronyms, item numbers, table column semantics, and clinical/statistical boundary disclaimers.
- Audit evidence, historical findings, verification result numbers, branch/commit/version observations, and no-go boundary statements unless the rewrite is additive navigation or explicitly preserves the full evidence nearby.
- Any capitalization change that would touch code identifiers, platform-required names, package names, command syntax, semantic labels, or established acronyms.

### 23.3 Safe transformations

Allowed transformations are documentation-only and limited to prose outside protected literals:

- Apply Independent English Word Title Case where safe in prose headings and short prose labels, for example changing a purely descriptive heading such as "Core standalone boundary" to "Core Standalone Boundary" only when no link anchor compatibility or semantic label is at risk.
- Improve sentence casing, punctuation, and wording in ordinary explanatory prose without changing the described behavior, support status, limitation, warning, or audience.
- Convert duplicate explanatory prose into a short summary plus an existing local link only when the target file remains self-contained enough for its audience and no command/warning/example is removed.
- Add navigation/index cross-links to reduce repeated explanation without deleting authoritative audit evidence.
- Standardize terminology in prose only when already established by the repository, for example "Standalone Python Core", "Optional Platform Add-on", "Permission Engine", "Chinese TUI", and "Workspace"; do not force these into code/manifest literals.
- Leave mixed Chinese/English role text intact where it identifies a role, UI label, or platform-facing description.

### 23.4 Per-file rewrite categories

| Category | Files | Strategy |
| --- | --- | --- |
| User-facing entry docs | `README.md`, `INSTALL.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md` | Keep standalone readability. Safe prose Title Case is allowed in headings and bullets, but command blocks, links, anchors, version labels, quality gates, and troubleshooting text are protected. Dedup should prefer cross-links, not removal of essential quick-start/install/security context. |
| Architecture/current design docs | `ARCHITECTURE.md`, `Architecture/ExecutionRoadmap.md`, `Architecture/PhaseImplementationPlan.md`, `Architecture/WorkspaceTuiRagGuide.md` | Preserve architecture diagrams, Mermaid blocks, path references, CLI/API names, and compatibility invariants. Safe cleanup is limited to prose headings/labels and navigation. Do not collapse roadmap/baseline/guide content unless each document keeps its own purpose clear. |
| Audit/history docs | `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, `Architecture/RepositoryOptimizationAudit.md` | Treat as evidence records. Add indexes or compact summaries only if full findings remain available. Avoid deleting repeated no-go rules, observations, verification evidence, or historical remediation notes because local audit traceability is the file purpose. |
| OpenCode agent docs | `adapters/opencode/agents/alpha-analyst.md`, `adapters/opencode/agents/beta-reviewer.md`, `adapters/opencode/agents/gamma-writer.md`, `adapters/opencode/agents/delta-orchestrator.md`, `adapters/opencode/agents/supermedicine.md` | Frontmatter and role/safety positioning are platform-facing and must remain local. Do not deduplicate repeated optional-add-on/internal-role disclaimers across files. Prose edits are allowed only outside frontmatter/code blocks and only when each file remains independently installable/readable. |
| Platform skill docs | `adapters/claude_code/SKILL.md`, `adapters/opencode/skills/harness-monitor.md`, `adapters/opencode/skills/medical-citation.md`, `adapters/opencode/skills/medical-writing.md`, `adapters/opencode/skills/python-stats.md`, `adapters/opencode/skills/r-survival.md`, `adapters/opencode/skills/rag-query.md` | Preserve frontmatter, trigger language, usage examples, action IDs, imports, and medical/statistical boundary disclaimers. Repeated disclaimers are intentional because skills are consumed independently. Safe prose cleanup may improve ordinary descriptions but must not weaken standalone safety context. |
| Plugin reference docs | `plugins/rag/references/provider-interface.md`, `plugins/standards/medical_writing/references/consort-checklist.md`, `plugins/standards/medical_writing/references/prisma-checklist.md`, `plugins/standards/medical_writing/references/stard-checklist.md`, `plugins/standards/medical_writing/references/strobe-checklist.md` | Treat as source references. Do not rewrite checklist rows, item numbers, standard names, references, or interface signatures. Safe edits are limited to headings or brief surrounding prose when not changing checklist meaning. Do not merge checklist files. |

### 23.5 Deduplication rules

Safe to reduce only with local review:

- Installation prose duplicated between `README.md` and `INSTALL.md`: keep README as quick-start and INSTALL as detailed guide. A later pass may shorten README explanations and link to INSTALL, but must retain at least one working quick-start path in README and full standalone install detail in INSTALL.
- Validation/quality-gate prose repeated across `README.md`, `CONTRIBUTING.md`, and audit files: keep canonical user guidance in README/CONTRIBUTING and historical verification evidence in audits. Reduce only by cross-linking, not by removing command examples that users need.
- Adapter descriptions repeated across `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `Architecture/PlatformIntegrationAudit.md`, and adapter skill/agent files: keep user-facing summaries in README/INSTALL, design detail in ARCHITECTURE, audit evidence in PlatformIntegrationAudit, and standalone platform context in adapter files. Cross-link rather than centralize away.
- Architecture summaries repeated across `ARCHITECTURE.md`, roadmap, phase plan, workspace guide, and audits: keep each file's local framing. Use navigation/index additions if needed; do not delete compatibility invariants or completed-roadmap context.
- Repeated medical/statistical boundary language across skill docs and references: generally do not reduce because each file is independently consumed and safety context must travel with the file.

Must remain duplicated:

- OpenCode internal-role disclaimers in each agent file.
- Skill frontmatter, trigger/capability descriptions, and safety disclaimers in each skill file.
- Medical checklist structure and reference sections across separate CONSORT, STROBE, PRISMA, and STARD files.
- Command examples necessary for standalone README/INSTALL/skill usability.
- Audit no-go boundaries and historical evidence in audit documents.
- Manifest/path/action/API names repeated for clarity in docs and tests.

### 23.6 Exact verification approach for the later rewrite pass

Verification should be performed after the Markdown rewrite by Tester, not by the strategy writer. The expected verification approach is:

1. Confirm Git diff scope is Markdown-only and includes no runtime/source/config/test/manifest/package/generated files other than the intended Markdown files.
2. Confirm the tracked Markdown inventory remains the same 29 files unless a later plan explicitly authorizes a Markdown file add/delete/rename.
3. Inspect `git diff --word-diff` or equivalent for protected literals and confirm no fenced code block, inline command/path/import/API/action ID/frontmatter value/checklist item/reference text was changed unintentionally.
4. Check Markdown links/anchors affected by heading Title Case changes; if anchor stability is uncertain, either preserve the original heading text or add an explicit stable anchor strategy in that later plan.
5. Re-run repository hygiene and Markdown-sensitive tests selected by Tester, especially tests that assert docs/manifests/adapter resources, without using this strategy section as proof of correctness.
6. Review semantic preservation manually for every dedup deletion: each removed paragraph must have an equivalent retained source, local context must remain clear, and standalone files must still explain their own install/safety/platform boundaries.
7. Confirm final diff contains no generated artifact churn and no line-ending-only rewrite of unrelated Markdown.

### 23.7 Step 2 strategy conclusion

The later Markdown rewrite should be conservative, additive where possible, and biased toward preserving standalone documentation over aggressive deduplication. Title Case normalization is safe only in ordinary prose/headings outside protected literals and must be skipped whenever it could affect anchors, identifiers, commands, paths, package/API/action names, semantic labels, frontmatter, or platform-required wording. The main deduplication mechanism should be cross-linking and summarization, not deletion of self-contained install, validation, adapter, architecture, audit, skill, or checklist context.

## 24. Step 3 Markdown Rewrite Execution Notes

Date: 2026-05-27

Scope: Markdown-only follow-up to the Step 2 strategy. The rewrite touches the 29
tracked Markdown files only and focuses on navigation, concise summaries,
terminology consistency, and safe heading/prose cleanup. Runtime/source files,
configuration files, manifests, tests, package metadata, generated artifacts,
staging, commit, push, tag, release, publish, and upload actions remain outside
scope.

Execution approach:

- Added short orientation or cross-reference summaries to user-facing,
  architecture, audit, adapter, skill, and plugin-reference Markdown files so
  repeated long explanations can point readers to the canonical detailed guide
  without removing each file's standalone safety/context purpose.
- Applied safe Title Case only to ordinary prose headings where no protected
  literal, link target, code identifier, manifest value, platform-required name,
  checklist wording, or command syntax was changed.
- Preserved frontmatter keys/values in adapter and skill documents, fenced code
  examples, inline commands and paths, plugin/action/tool IDs, API names,
  checklist item rows, references, verification evidence, and historical audit
  observations.
- Kept duplicated safety disclaimers local in platform agent/skill and checklist
  reference documents because those files may be consumed independently.
- Reduced one safe repeated heading in the workspace guide by keeping the actual
  `Paper Import and Metadata` section where its content begins.

Step 3 conclusion: the Markdown rewrite is intentionally conservative and uses
summary/cross-reference additions as the main deduplication mechanism. The audit
record, platform boundaries, medical/statistical disclaimers, and protected
identifiers remain local where standalone consumption requires them.

## 25. Step 4 File and Directory Naming Normalization Review

Date: 2026-05-27

Scope: repository path and reference review after the Markdown rewrite. This pass
looked for safe file or directory capitalization changes under the user's
independent-word initial-capitalization preference, with functionality
preservation taking absolute priority.

Result:

- Renames performed: none.
- Reference synchronization performed: none, because no path rename was made.
- Safe capitalization rename candidates found: none.

Skipped risky rename candidates:

- Python entry modules `Cli.py` and `Install.py` remain unchanged because they are
  public/documented entry points and are referenced by packaging metadata,
  commands, documentation, and tests.
- Python packages, modules, and subpackages under `core/**`, `permission/**`,
  `agents/**`, `plugins/**`, and `adapters/**` remain unchanged because changing
  capitalization would alter import paths, package discovery, plugin discovery,
  package data paths, or adapter loading behavior.
- Plugin manifests and platform manifests, including `plugins/**/plugin.yaml`,
  `adapters/opencode/plugin.json`, and `install.json`, remain unchanged because
  their names and paths may be loaded literally by tooling, tests, packaging, or
  platform adapters.
- Adapter platform resources under `adapters/opencode/**` and
  `adapters/claude_code/**`, including agent and skill Markdown filenames, remain
  unchanged because filenames and directories can function as platform-facing
  identifiers or installation targets.
- Tests under `tests/**` remain unchanged because pytest discovery conventions,
  path literals, and test imports depend on the current lowercase `tests/` tree
  and `test_*.py` names.
- Package data and runtime/configuration paths such as
  `permission/default_policy.yaml`, `.supermedicine/**`, `.github/workflows/**`,
  `.gitignore`, `pyproject.toml`, and `requirements.txt` remain unchanged because
  ecosystem tooling and runtime discovery expect those conventional names.
- Conventional repository metadata files `README.md`, `INSTALL.md`,
  `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and
  `LICENSE` remain unchanged because their uppercase forms are intentional
  ecosystem conventions and because renaming them could break documentation links
  or repository presentation.
- Documentation paths under `Architecture/**` remain unchanged because the current
  mixed-case directory is already referenced throughout the audit trail and a
  case-only or title-case reshaping would create unnecessary Windows/Git and link
  synchronization risk.

Rationale: every apparent capitalization opportunity is coupled to imports,
entry points, manifests, package data, platform discovery, test discovery,
runtime configuration, documentation links, repository hosting conventions, or
case-only rename behavior on Windows. Since no candidate was demonstrably
non-functional and safe, the conservative outcome is to perform no rename and
avoid reference churn.

## 26. Current Step 1 Repository Baseline Audit

Date: 2026-05-27

Scope: audit-only baseline refresh before further repository optimization. The
original Step 1 entry repeated boundaries already recorded in sections 15, 23,
and earlier audit passes; Step 3 later compressed it to this evidence-focused
summary without changing any repository fact or runtime/source behavior.

Key baseline evidence preserved:

- Working directory: `D:\GIT\SuperMedicine`; branch/tracking line:
  `## master...origin/master`; remote: `origin
  https://github.com/KarasawaYikiho/SuperMedicine.git` for fetch and push.
- Baseline HEAD: `d9a69c5d6d582942e9282bbe7129edbb390c7891` (`d9a69c5 docs:
  rewrite markdown docs and document no-safe-rename audit`).
- Pre-audit Git state was clean for tracked, staged, deleted, renamed, and
  untracked non-ignored files; `git diff --stat` and `git diff --cached --stat`
  produced no output before the audit edit.
- Tracked inventory snapshot: 183 files total, including 137 Python files and 44
  pytest modules matching `tests/test_*.py`; top-level counts were `.github` 1,
  `.supermedicine` 2, root files 13, `Architecture` 6, `adapters` 21,
  `agents` 5, `core` 40, `permission` 6, `plugins` 43, and `tests` 46.
- Project stack remains the Python package/application `supermedicine` version
  `0.3.0b0`, Python `>=3.10`, setuptools build backend, runtime dependencies
  `pyyaml>=6.0`, `rich>=13.7,<15`, and `textual>=0.79,<2`, development extras
  `mypy`, `pytest`, `pytest-cov`, `ruff`, and `types-PyYAML`, and optional
  `rpy2>=3.5` R survival support.
- Protected discovery/entry surfaces remain: `supermedicine = "Cli:main"`,
  `Cli.py`, `Install.py`, setuptools `py-modules = ["Cli", "Install"]`, package
  discovery for `core*`, `permission*`, `agents*`, `plugins*`, and `adapters*`,
  package data such as `permission/default_policy.yaml`, `core/tui/app.tcss`,
  `plugins/**/plugin.yaml`, `plugins/**/*.yaml`, and
  `adapters/opencode/plugin.json`, pytest discovery under `tests/test_*.py`, CI
  under `.github/workflows/ci.yml`, `.supermedicine` config/policy inputs,
  `install.json`, OpenCode/Claude Code adapter resources, and every plugin
  `plugin.yaml`.
- Verification command inventory for Tester remained unchanged: install/build
  commands, lint/type gates, repository-hygiene and full pytest gates, wheel and
  sdist smoke/build gates, and CLI smoke commands such as `python Install.py
  --init`, `python Cli.py status`, `supermedicine status`, `supermedicine init`,
  workspace/paper/experience/tool commands, and `supermedicine tui`.
- Ignored/local snapshot: Git reported `Planning/NextSteps.md` and emitted
  `warning: could not open directory '.pytest_cache/': Permission denied`; it did
  not list ignored `build/`, `dist/`, `supermedicine.egg-info/`, `.ruff_cache/`,
  `.mypy_cache/`, accessible `__pycache__/`, `*.pyc`, runtime checkpoints, or
  runtime audit logs.
- Case-sensitive path scan found no lowercase-key duplicate tracked paths.

Preservation decision: no runtime code, business logic, API behavior, defaults,
conditions, data-structure meaning, tests, manifests, configuration semantics,
dependency constraints, staging, commit, push, release, publish, deletion, or path
rename was performed. Later cleanup remains limited to exact duplicate prose that
preserves local meaning, documentation navigation/indexing, or explicitly scoped
ignored generated-artifact cleanup. Runtime/source/config/test/manifest/package,
platform, policy, plugin/action, adapter, dependency, CI, and path-capitalization
contracts remain high-risk protected areas unless a later semantic-change plan
authorizes and verifies them.

## 27. Current Step 2 Naming Normalization Execution

Date: 2026-05-27

Scope: conservative execution of the requested independent-word
initial-capitalization naming normalization after the Step 1 baseline audit. Step
3 later compressed the repeated category-by-category rationale into this compact
decision record; the decision and evidence are unchanged.

Execution result: no file or directory was renamed; no reference synchronization
was required; no runtime/source/config/test/manifest/package/platform file was
changed; only this audit record and the audit-pass index were updated.

No-safe-rename decision: apparent candidates were skipped because they are tied
to public entry paths (`Cli.py`, `Install.py`), Python imports and package
discovery (`core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`),
pytest discovery (`tests/**`, `tests/test_*.py`), plugin registry/resource lookup
(`plugins/**/plugin.yaml` and plugin references), platform manifests and resource
IDs (`install.json`, `adapters/opencode/**`, `adapters/claude_code/**`), runtime
and tooling conventions (`.supermedicine/**`, `.github/workflows/ci.yml`,
`.gitignore`, `pyproject.toml`, `requirements.txt`), conventional root metadata
(`README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `LICENSE`), or the already-referenced `Architecture/**` audit
paths. Hidden configuration, package-management, framework/tooling, platform,
case-only, import-migration, manifest-migration, pytest-discovery,
plugin-discovery, platform-resource, and broad documentation-link candidates were
therefore treated as unsafe.

Rationale: the tracked path inventory contains no source-of-truth naming target
that is provably non-breaking under a case-sensitive environment model. Leaving
paths untouched preserves imports, entry points, manifests, package data,
platform discovery, test discovery, runtime configuration, documentation links,
repository hosting conventions, and Windows/Git case behavior.

Expected Tester focus: confirm the diff is limited to this audit document, no
filesystem rename occurred, and existing path references still match tracked
filenames exactly under a case-sensitive path model.

## 28. Current Step 3 Duplicate Reduction Execution

Date: 2026-05-27

Scope: documentation-only deletion/merge of duplicate or redundant content, with
priority on recently repeated status, strategy, boundary, command inventory,
artifact, and no-rename paragraphs in this audit document. No code, tests,
configuration, manifests, policies, package metadata, generated artifacts,
runtime behavior, public API, staging, commit, push, release, publish, upload, or
filesystem path was changed.

Duplicate reductions performed:

- Compressed the verbose Step 1 baseline subsections into a single evidence-led
  summary that preserves the current commit, clean Git state, tracked counts,
  technology stack, protected discovery surfaces, verification command inventory,
  ignored/local artifact observations, case-scan result, and preservation
  decision.
- Compressed the verbose Step 2 naming-normalization subsection into one compact
  no-safe-rename decision record that preserves the no-rename result, skipped
  categories, rationale, and Tester focus.
- Added this Step 3 index entry and execution section so future passes can point
  to the current duplicate-reduction decision instead of restating the same
  baseline and no-go language again.

Content intentionally preserved:

- Historical audit sections 1-25 remain in place because they are evidence and
  prior-pass traceability, not disposable source-of-truth duplicates.
- Commands, paths, package names, manifest names, plugin/action/platform
  identities, dependency constraints, test references, commit IDs, counts, and
  warning text were preserved where they carry audit evidence or verification
  value.
- No duplicate-looking code, test, policy, manifest, platform resource, medical
  checklist, adapter skill/agent document, generated mirror, or ignored local
  planning material was deleted or merged.

Step 3 conclusion: duplicate reduction was limited to audit prose compression in
`Architecture/RepositoryOptimizationAudit.md`. The retained text preserves the
same repository facts, decisions, verification evidence, and semantic-protection
boundaries while reducing repeated recent status and strategy paragraphs.

## 29. Current Step 4 Repository Cleanliness Execution

Date: 2026-05-27

Scope: repository cleanliness cleanup of temporary, cache, runtime, build,
packaging, local planning, editor/system, and other ignored generated artifacts.
No source code, tests, configuration semantics, manifests, policies, package
metadata inputs, runtime defaults, public behavior, staging, commit, push,
release, publish, upload, or path rename was intentionally changed.

Cleanup performed:

- Removed safe ignored generated/local artifacts when present: `.ruff_cache/`,
  `.mypy_cache/`, `build/`, `supermedicine.egg-info/`,
  `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`,
  `Planning/NextSteps.md`, accessible `__pycache__/` directories, and accessible
  `*.pyc` / `*.pyo` bytecode files.
- Restored tracked source-of-truth files from a clean recovery copy after an
  over-broad cleanup command affected tracked files; final tracked file content
  was brought back to the repository baseline before recording this audit entry.
- Rechecked ignored status after cleanup; Git still reported the known
  `.pytest_cache/` permission-denied warning, and no accessible ignored cache,
  build, package, runtime, bytecode, or local planning artifact was listed.

Ignore-rule review:

- `.gitignore` already covers Python bytecode, build/package outputs,
  lint/type/test/coverage caches, SuperMedicine runtime audit/checkpoint outputs,
  external assistant local directories, local planning notes, environment files,
  virtual environments, workspace data, logs, and common macOS/Windows metadata.
- No `.gitignore` update was made because the existing rules were sufficient for
  the artifacts cleaned in this step and adding broader patterns could risk
  hiding source-of-truth files.

Semantic-preservation result:

- Runtime/source/config/test/manifest/policy/package files were not intentionally
  edited for cleanup or formatting.
- No repository-wide formatter, import sorter, line-ending rewrite, capitalization
  rename, or generated-source synchronization was run.
- The only intended tracked change from this step is this audit record in
  `Architecture/RepositoryOptimizationAudit.md`.

## 30. Current Step 5 Full Consistency and Regression Verification Preparation

Date: 2026-05-27

Scope: preparation for full repository consistency validation after the preceding
documentation, naming, duplicate-reduction, and cleanliness steps. This section is
an audit-only verification plan/result placeholder. It does not change runtime
source behavior, configuration semantics, manifests, tests, dependency metadata,
package inputs, platform declarations, staging, commit, push, release, publish,
upload, or filesystem paths. Coder did not run tests or verification commands;
Tester owns execution and evidence collection.

Planned verification gates for Tester:

- Dependency/install resolution gate: confirm the project can be installed with
  development dependencies, for example with `python -m pip install -e ".[dev]"`
  in an isolated environment appropriate for verification.
- Lint gate: run the repository lint command recorded in prior audit sections,
  `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Type gate: run the repository type-check gate with an explicit temporary cache,
  `python -m mypy . --cache-dir <temp-mypy-cache>`.
- Build gate: confirm package build inputs remain valid and the build command
  succeeds without relying on stale generated outputs.
- Wheel smoke gate: build a wheel with an explicit temporary wheel directory,
  `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>`.
- Source distribution smoke gate: build an sdist into an explicit disposable output
  directory, `python -m build --sdist --outdir <temp-dist-dir>`.
- Repository hygiene gate: run the focused hygiene test with cache disabled and an
  explicit temporary base directory,
  `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`.
- Full regression gate: run the full pytest suite with cache disabled and an
  explicit temporary base directory,
  `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`.
- Diff-scope gate: confirm the tracked diff for this Step 5 preparation remains
  limited to `Architecture/RepositoryOptimizationAudit.md` unless Tester observes
  a separately justified non-semantic cleanup result.
- Path/case gate: confirm tracked paths still have no case-collision or invalid
  reference drift caused by the no-rename optimization decisions.
- Generated-artifact cleanup gate: after lint, type, build, wheel/sdist, and pytest
  commands, remove or report disposable generated artifacts such as `build/`,
  `dist/`, `*.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, accessible
  `.pytest_cache/`, `__pycache__/`, `*.pyc`, and runtime audit/checkpoint outputs
  if they were regenerated during validation; preserve tracked source-of-truth
  files and document any inaccessible `.pytest_cache/` material rather than
  forcing permissions.

Evidence requirements for Tester:

- Capture command outcomes for install/dependency resolution, lint, type checking,
  build, wheel smoke, sdist smoke, repository hygiene pytest, and full pytest.
- Use explicit temporary output/cache/base directories for gates that generate
  artifacts so validation does not depend on or leave stale repository-local state.
- Record any non-semantic issue found during verification separately from runtime
  behavior, and do not make functionality changes merely to satisfy validation.
- Confirm no stale generated artifacts, invalid paths, case-only rename effects, or
  unintended tracked-file changes remain after cleanup.

Tester verification evidence received for Step 5:

- Dependency/install resolution gate: passed for the development install command
  planned above.
- Lint gate: passed for `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Type gate: passed for `python -m mypy . --cache-dir <temp-mypy-cache>`.
- Wheel smoke/build gate: passed for `python -m pip wheel . --no-deps --wheel-dir
  <temp-wheel-dir>`.
- Source distribution smoke/build gate: passed for `python -m build --sdist
  --outdir <temp-dist-dir>`.
- Repository hygiene gate: passed for the focused hygiene pytest command with cache
  provider disabled and a temporary base directory.
- Full regression gate: passed for the full pytest suite with cache provider
  disabled and a temporary base directory.
- Diff-scope and path/case review: Tester confirmed the tracked changes stayed
  limited to repository-optimization audit documentation, with no path rename,
  case-only rename, runtime/source behavior change, configuration change, manifest
  change, package metadata input change, or test-intent change.
- Generated-artifact note: verification regenerated ignored artifacts including
  tool caches, runtime local outputs, bytecode caches, build output, and package
  metadata; these are safe to clean after evidence collection. The known
  `.pytest_cache/` permission-denied boundary remains non-semantic and may be left
  in place if normal cleanup cannot access it.

Functional semantics changed: none.

## 31. Current Step 6 Git Review and Submission

Date: 2026-05-27

Scope: final Git review, post-verification ignored-artifact cleanup, staging,
commit, and push for the current repository optimization pass. No force push,
tag, release, publish, upload, runtime/source edit, configuration edit, manifest
edit, policy edit, dependency edit, package metadata input edit, test edit, path
rename, or behavior change is part of this step.

Post-verification cleanup performed:

- Removed regenerated ignored artifacts that were safe to delete with normal
  workspace permissions: `.ruff_cache/`, `.supermedicine/checkpoints/`,
  `.supermedicine/policies/audit.jsonl`, `build/`, `supermedicine.egg-info/`,
  accessible `__pycache__/` directories, and accessible bytecode files.
- Preserved source-of-truth files, tracked runtime configuration/policy inputs,
  tests, manifests, package inputs, adapter and plugin resources, and audit
  history.
- Left `.pytest_cache/` as the known permission-denied boundary when normal Git
  ignored-file inspection reported it as inaccessible; no elevated or forced
  cleanup was attempted.

Final diff and staging policy:

- Final tracked diff scope is limited to
  `Architecture/RepositoryOptimizationAudit.md`.
- The recorded changes are audit documentation only: Step 5 Tester evidence,
  ignored-artifact cleanup notes, and this Step 6 submission trace.
- No runtime/source/config/test/manifest/package/policy/platform semantics are
  changed by this step.
- Only the expected audit document is staged for commit; ignored generated
  artifacts are not staged.

Submission policy:

- Commit message should describe the repository-optimization audit evidence and
  cleanup without implying functional behavior changes.
- Push uses the current branch's configured remote tracking target and does not
  use force.

## 32. Current Step 6 Repository Cleanliness Cleanup

Date: 2026-05-28

Scope: cleanup of ignored temporary, cache, build, package, runtime, local planning,
and other generated artifacts after verification activity. This step does not
change runtime source, tests, configuration semantics, manifests, package metadata
inputs, policies, platform resources, staging, commit, push, release, publish,
upload, path names, or functional behavior.

Cleanup performed:

- Removed accessible ignored generated artifacts when present, including
  `.ruff_cache/`, `build/`, `dist/`, `supermedicine.egg-info/`,
  `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`,
  accessible `__pycache__/` directories, and accessible Python bytecode files.
- Removed ignored local planning material under `Planning/` as part of repository
  cleanliness cleanup; it was not tracked source-of-truth documentation.
- Preserved tracked `.supermedicine/config.yaml` and
  `.supermedicine/policies/default.yaml` as required runtime/bootstrap inputs.
- Left `.pytest_cache/` as the documented permission-denied boundary when normal
  cleanup could not remove it; no elevated or forced permission change was
  attempted.

Ignore-rule review:

- `.gitignore` was not changed because existing ignore rules already cover the
  cleaned Python bytecode, build/package outputs, tool caches, test caches,
  SuperMedicine runtime audit/checkpoint outputs, local planning notes, logs,
  environment files, workspace data, and common OS/editor artifacts.
- No broader ignore pattern was added, avoiding the risk of hiding required source,
  documentation, package data, manifest, adapter, plugin, or resource files.

Preservation result:

- Tracked source, tests, documentation other than this audit record,
  configuration, policy defaults, manifests, package inputs, adapter resources,
  plugin resources, and CI files were preserved.
- No Markdown link target, path reference, import path, package-discovery path,
  manifest path, or runtime configuration path was renamed or rewritten.
- The only intended tracked change from this step is this audit record in
  `Architecture/RepositoryOptimizationAudit.md`.

## 33. Current Step 7 Full Regression and Path Integrity Verification Cleanup

Date: 2026-05-28

Scope: audit-only record of Tester-owned full regression and repository integrity
validation after the cleanup and audit-record steps, followed by cleanup of
validation-regenerated ignored artifacts. Coder did not run tests, builds,
linters, type checks, Git validation commands, path scans, secret scans, staging,
commit, push, release, publish, upload, or any runtime/source/configuration/
manifest/test/package change. This section records the validation command set,
Tester-reported pass evidence, and generated-artifact cleanup result.

Tester command record:

- Environment/install gate: in an isolated verification environment, run
  `python -m pip install -e ".[dev]"` so `ruff`, `mypy`, `pytest`, and `build`
  are available from the repository's declared development extra.
- Ruff lint gate: run
  `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Mypy type gate: run
  `python -m mypy . --cache-dir <temp-mypy-cache>` with `<temp-mypy-cache>`
  outside the repository or inside a disposable temp directory.
- Wheel/package gate: run
  `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>` with a
  disposable `<temp-wheel-dir>`.
- Source distribution gate: run
  `python -m build --sdist --outdir <temp-dist-dir>` with a disposable
  `<temp-dist-dir>`; if the build backend also produces metadata or cache output,
  treat it as generated validation output to clean or report after evidence is
  captured.
- Repository hygiene pytest gate: run
  `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`
  with `<temp-basetemp>` as a disposable path outside persistent repository
  state.
- Full regression pytest gate: run
  `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`
  with cacheprovider disabled and a safe disposable base temp directory.

Repository integrity checks for Tester:

- Repo hygiene/status: confirm `git status --short --branch`, `git diff --stat`,
  `git diff --name-status`, and `git diff --cached --name-status` show only the
  intended audit-document tracked change and no staged or unrelated tracked
  change.
- Diff scope: inspect the tracked diff and confirm it is limited to
  `Architecture/RepositoryOptimizationAudit.md`, with documentation-only content
  and no runtime/source/config/test/manifest/package/CI/policy/platform semantic
  change.
- Path/case collision check: confirm tracked paths have no lowercase-key
  collision under a case-insensitive model and no case-only rename effect. A
  suitable check is to compare `git ls-files` against each path lowercased and
  report any key with more than one distinct tracked path.
- Path/reference integrity: for each protected path family recorded in this audit
  (`Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`,
  `adapters/**`, `tests/**`, `.github/workflows/ci.yml`, `.supermedicine/**`,
  `install.json`, `pyproject.toml`, `requirements.txt`, and `Architecture/**`),
  confirm no referenced tracked path is missing, renamed with inconsistent case,
  or broken by the no-rename decisions. Documentation links and manifest-declared
  resource paths should be checked against actual tracked files where tooling or
  tests do not already cover them.
- Generated artifact check: after lint/type/build/pytest commands, inspect ignored
  and untracked output for validation-generated artifacts such as `build/`,
  `dist/`, `*.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, accessible
  `.pytest_cache/`, `__pycache__/`, `*.pyc`, `.supermedicine/checkpoints/`, and
  `.supermedicine/policies/audit.jsonl`. Clean disposable artifacts with normal
  permissions or record them as generated validation outputs; do not delete
  tracked source-of-truth files.
- Permission boundary: if `.pytest_cache/` still reports permission denied, record
  it as the known non-semantic inaccessible cache boundary and do not force
  ownership or permissions.
- Secret/local-state check: confirm no secrets, credentials, environment files,
  local assistant state, runtime audit logs, checkpoints, or generated package
  artifacts are introduced into tracked changes. This includes checking that
  `.supermedicine/config.yaml` and `.supermedicine/policies/default.yaml` remain
  tracked policy/config inputs, while runtime outputs remain untracked/ignored.
- Baseline-failure handling: if any verification command has a pre-existing
  baseline failure, Tester should capture the failure, compare it against the
  current diff scope, and prove this Step 7 audit-only change introduced no new
  failure. Do not treat this audit section itself as proof that a command passed.

Evidence requirements:

- Record command outcomes for ruff, mypy, wheel build, sdist build, repository
  hygiene pytest, and full pytest using the exact safe-temp/no-cache forms above
  or equivalent paths that avoid persistent repository state.
- Record repository status, diff scope, path/case collision results,
  path/reference integrity results, secret/local-state results, and generated
  artifact cleanup or preservation notes after verification.
- Confirm that any regenerated artifacts are either removed with normal
  permissions, left ignored and explicitly reported, or preserved only when they
  are the known inaccessible `.pytest_cache/` boundary.
- Confirm no file or directory rename occurred, no path reference has missing or
  inconsistent case, no documentation link checked by this gate is broken, and no
  functional semantics changed.

Tester-reported Step 7 validation evidence:

- Environment/install gate passed for the repository development install with the
  declared development dependencies available for validation.
- Ruff lint gate passed for `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Mypy type gate passed for `python -m mypy . --cache-dir <temp-mypy-cache>` with
  a disposable cache path.
- Wheel/package gate passed for `python -m pip wheel . --no-deps --wheel-dir
  <temp-wheel-dir>`.
- Source distribution gate passed for `python -m build --sdist --outdir
  <temp-dist-dir>`.
- Repository hygiene pytest gate passed for
  `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`.
- Full regression pytest gate passed for
  `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-basetemp>`.
- Repository status, diff scope, path/case collision, path/reference integrity,
  and secret/local-state checks passed, with the only intended tracked change
  remaining this audit document and no runtime/source/config/test/manifest/
  package/CI/policy/platform semantic change reported.
- Generated-artifact hygiene initially failed because validation regenerated
  ignored artifacts. The required follow-up was to remove safe ignored generated
  outputs and preserve tracked `.supermedicine/config.yaml` and
  `.supermedicine/policies/default.yaml`.

Post-validation cleanup result:

- Removed regenerated ignored artifacts accessible with normal permissions:
  `.ruff_cache/`, `build/`, `supermedicine.egg-info/`,
  `.supermedicine/checkpoints/`, and `.supermedicine/policies/audit.jsonl`.
- Checked for and treated `dist/`, accessible `__pycache__/` directories, and
  accessible `*.pyc` files as cleanup targets when present; no source-of-truth
  file is part of this cleanup class.
- Preserved tracked `.supermedicine/config.yaml` and
  `.supermedicine/policies/default.yaml` as required runtime/bootstrap inputs.
- Preserved the known `.pytest_cache/` permission-denied boundary if present;
  no elevated permission change or forced cleanup is part of this step.

Step 7 conclusion: Tester reported all full validation commands and repository
integrity checks passed after evidence collection. The validation-generated
ignored artifacts were cleaned where accessible with normal permissions, and the
intended tracked change remains this audit-only verification and cleanup record.

## 34. Current Step 8 Diff Review and Functional Invariance Confirmation

Date: 2026-05-28

Scope: final diff review after the naming, cleanup, duplicate-reduction,
documentation-hygiene, verification-record, and generated-artifact cleanup steps.
This step is audit-only and records the review conclusion; it does not change
runtime source, tests, configuration semantics, manifests, package metadata
inputs, policies, platform resources, CI, staging, commit, push, release,
publish, upload, path names, or functional behavior.

Diff review evidence:

- `git status --short --branch` showed the current branch as
  `master...origin/master` with only `Architecture/RepositoryOptimizationAudit.md`
  modified.
- `git diff --name-status` showed only
  `M Architecture/RepositoryOptimizationAudit.md`.
- `git diff --stat` showed one changed file,
  `Architecture/RepositoryOptimizationAudit.md`, with documentation insertions.
- The inspected diff consists of audit-pass index additions and new audit-record
  sections for ignored-artifact cleanup, Tester-reported verification evidence,
  and this final diff review.
- Git repeated the known line-ending warning for this audit file (`LF will be
  replaced by CRLF the next time Git touches it`); this is recorded as workspace
  line-ending metadata noise and not as a runtime/source/config/test/manifest
  semantic change.

Functional invariance review:

- No file or directory rename appears in the final tracked diff. The no-safe-rename
  outcome for independent-word capitalization remains unchanged.
- No runtime/source files are part of the tracked diff, including `Cli.py`,
  `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, or
  `adapters/**`.
- No tests are part of the tracked diff, including `tests/**`; test intent and
  assertions are unchanged by this review step.
- No configuration, policy, manifest, dependency, package, CI, or platform
  declaration inputs are part of the tracked diff, including `.supermedicine/**`,
  `.gitignore`, `pyproject.toml`, `requirements.txt`, `install.json`,
  `.github/workflows/**`, `adapters/opencode/plugin.json`, and
  `plugins/**/plugin.yaml`.
- Ignored generated-artifact cleanup records are documentation evidence only; the
  cleanup category remains limited to caches, build/package outputs, runtime local
  logs/checkpoints, and local planning material already treated as ignored
  non-source artifacts. Tracked `.supermedicine` config and policy inputs remain
  preserved, and the known `.pytest_cache/` permission boundary is not forced.
- The Step 7 Tester-reported validation evidence is recorded as audit history; it
  does not alter command behavior, verification gates, package metadata, or
  runtime semantics.

Review conclusion: the final diff is intentionally limited to
`Architecture/RepositoryOptimizationAudit.md` and contains only audit trail,
cleanup-record, validation-evidence, and diff-review documentation. No change in
the diff alters public API behavior, CLI behavior, imports, package discovery,
permissions, manifests, tests, runtime configuration, generated-artifact policy,
platform contracts, path names, or functional semantics.
