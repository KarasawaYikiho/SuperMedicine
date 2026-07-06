# Repository Optimization Audit

**Date started:** 2026-05-26 | **Last updated:** 2026-05-28

**Purpose:** Establish and maintain an immutable baseline and protection boundaries for repository optimization. This document is audit-only: no runtime/source behavior changes except creating and updating this document.

---

## Audit Pass Summary

| Pass | Date | Scope | Key Outcome |
| --- | --- | --- | --- |
| 1–9 | 2026-05-26 | Initial baseline audit: branch/worktree state, structure, commands, artifacts, no-go boundaries | Established preservation boundaries and cleanup policy. |
| 10 | 2026-05-26 | Independent-word capitalization/path-risk audit | No safe rename candidate found; every candidate tied to imports, discovery, tooling, or platform conventions. |
| 11 | 2026-05-26 | Conservative naming normalization | No renames performed. |
| 12 | 2026-05-26 | Duplicate/redundant content and generated artifact audit | Recommended generated-artifact cleanup only; no source/content deduplication. |
| 13 | 2026-05-26 | Generated-artifact cleanup | Removed accessible generated/cache/runtime artifacts; skipped inaccessible `.pytest_cache/`. |
| 14 | 2026-05-26 | Documentation-only consistency update | Clarified audit wording; no runtime/source behavior change. |
| 15 | 2026-05-27 | Repeated-pass baseline refresh at commit `0fe238b` | Re-established clean tracked baseline and boundaries. |
| 16 | 2026-05-26 | Deep semantic-preserving audit | Identified generated cleanup and docs-navigation candidates; skipped risky duplicates/renames. |
| 17 | 2026-05-26 | Generated/cache cleanup | Removed accessible generated/cache/runtime artifacts only. |
| 18 | 2026-05-26 | Naming/capitalization follow-up | No renames; no reference synchronization required. |
| 19 | 2026-05-26 | Safe duplicate reduction | Added this navigation index; no source/prose deletion performed. |
| 20 | 2026-05-26 | Repository format and text hygiene | Minimal docs-only hygiene; skipped risky formatting churn. |
| 21 | 2026-05-26 | Repository hygiene test coverage assessment | No new tests needed; existing `test_repo_hygiene.py` covers all relevant invariants. |
| 22 | 2026-05-26 | Final diff and semantic-preservation confirmation | Cleaned accessible regenerated artifacts; final diff limited to this audit document. |
| 23 | 2026-05-27 | Markdown rewrite and deduplication strategy | Defined safe prose rewrite rules, per-file categories, and dedup policy for all 29 tracked Markdown files. |
| 24 | 2026-05-27 | Markdown rewrite execution notes | Conservative rewrite; protected literals and audit evidence preserved. |
| 25 | 2026-05-27 | File/directory naming normalization review | No renames; all candidates tied to imports, discovery, manifests, or conventions. |
| 26 | 2026-05-27 | Fresh repository baseline audit at commit `d9a69c5` | Recorded clean Git state, structure, build/test commands, path-case risks, and cleanup limits. |
| 27 | 2026-05-27 | Naming normalization execution | No renames; all candidates are import/discovery/tooling/platform sensitive. |
| 28 | 2026-05-27 | Duplicate reduction | Compressed repeated baseline/boundary/boundary prose into compact summaries. |
| 29 | 2026-05-27 | Repository cleanliness cleanup | Removed safe ignored cache/build/runtime/local artifacts; preserved tracked config/policy inputs. |
| 30 | 2026-05-27 | Verification preparation | Recorded validation gates and evidence expectations for Tester. |
| 31 | 2026-05-27 | Git review and submission | Recorded Tester-reported verification evidence; cleaned regenerated artifacts; final diff limited to this document. |
| 32 | 2026-05-28 | Repository cleanliness cleanup | Removed accessible ignored cache/build/package/runtime artifacts; preserved canonical `.supermedicine` policy while keeping local runtime config out of repository content. |
| 33 | 2026-05-28 | Full regression and path integrity verification cleanup | All Tester gates passed (install, lint, type, wheel, sdist, pytest, hygiene, path/case, diff scope, secret check). Cleaned regenerated artifacts. |
| 34 | 2026-05-28 | Final diff review and functional invariance confirmation | Final diff confirmed audit-document only; no functional semantic change. |

---

## Hard No-Go Semantic Preservation Boundaries

**Absolute priority:** Do not change existing functionality or code meaning, even for security risks or unused code.

Must preserve:
- **Public API:** behavior, function/class/module names, return shapes, exceptions, import paths.
- **CLI:** commands, arguments, defaults, prompts, output meanings, exit behavior, `supermedicine` console script.
- **Plugins:** IDs, action IDs, manifests, schemas, registry/discovery semantics.
- **Adapters:** OpenCode, Claude Code, and standalone adapter behavior, including degraded/unavailable states.
- **Agents:** agent IDs, role documents, skill document identity, plugin metadata, platform manifests.
- **Permissions/security:** policy behavior, default allow/deny meanings, audit semantics, operation guard semantics, path safety checks, prompt-generation safety guidance.
- **Packaging:** entry points, setuptools discovery, package data, optional extras, version meaning, importable module names.
- **Tests:** meaning and assertions; may only change if preserving intent during purely mechanical path/name synchronization.
- **Medical/statistical outputs:** output meanings, deterministic fixtures, R/rpy2 fallback, RAG provider contracts, workspace/TUI/paper/experience workflows.
- **Configuration:** file meanings, default values, `.supermedicine` behavior, policy structure, runtime artifact paths.
- **Uncommitted changes:** existing platform agent/model/version changes listed in early audit sections.

---

## Naming/Rename Decision (Conservative — No Renames)

Every path in the repository is tied to one or more of: Python imports, setuptools discovery, pytest discovery, plugin manifests, adapter platform discovery, configuration loading, CI workflows, documentation links, or Windows/Git case-sensitivity behavior. **No file or directory has been renamed across all 34 passes.**

Key risky categories documented and permanently skipped:
- Python entry modules: `Cli.py`, `Install.py`
- Python packages: `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`
- Tests: `tests/**`, `tests/test_*.py`
- Plugin manifests: `plugins/**/plugin.yaml`
- Platform manifests: `install.json`, `adapters/opencode/plugin.json`
- Adapter resources: `adapters/opencode/agents/*.md`, `adapters/opencode/skills/*.md`, `adapters/claude_code/SKILL.md`
- Runtime config: `.supermedicine/**`, `.gitignore`, `.github/workflows/ci.yml`
- Conventional metadata: `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`
- Packaging: `pyproject.toml`, `requirements.txt`

If any future rename is judged safe, all of the following must be synchronized in the same step: Python imports, package discovery, package data, console entry points, tests, pytest config, plugin manifests, adapter metadata, config files, `.gitignore` patterns, documentation links, CI workflows, and Git rename mechanics (two-step for case-only on Windows).

---

## Duplicate Reduction Decision

No source-of-truth documentation, configuration, code, test, manifest, policy, adapter, plugin, or platform resource content has been deleted or merged across any pass. Duplicates were reduced only within this audit document via compression of repeated baseline/boundary prose.

Items intentionally kept duplicated:
- `permission/default_policy.yaml` (package data) and `.supermedicine/policies/default.yaml` (local runtime copy)
- Install commands in `README.md` (quick-start) and `INSTALL.md` (detailed guide)
- OpenCode agent role disclaimers across `adapters/opencode/agents/*.md`
- Platform skill safety disclaimers across skill/reference docs
- Medical checklist content across separate CONSORT, STROBE, PRISMA, STARD files
- Audit no-go boundary statements across Architecture audit documents

---

## Generated-Artifact Cleanup Policy

Artifacts eligible for removal when accessible:
- `build/`, `dist/`, `supermedicine.egg-info/` — build/package outputs
- `__pycache__/`, `*.pyc` — Python bytecode caches
- `.ruff_cache/`, `.mypy_cache/` — tool caches
- `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl` — runtime outputs
- `Planning/NextSteps.md` — ignored local planning note

**Not eligible for removal:**
- Local-only `.supermedicine/config.yaml` when present, and tracked `.supermedicine/policies/default.yaml` (bootstrap policy input)
- `.pytest_cache/` when inaccessible due to permission denial (document and skip)

---

## Final Baseline State

| Item | Value |
| --- | --- |
| Branch | `master...origin/master` |
| Remote | `origin https://github.com/KarasawaYikiho/SuperMedicine.git` |
| Last baseline commit | `d9a69c5 docs: rewrite markdown docs and document no-safe-rename audit` |
| Version | `0.4.2b0` |
| Python | `>=3.10` |
| Build backend | `setuptools>=68.0`, `wheel` |
| Runtime deps | `pyyaml>=6.0`, `rich>=13.7,<15`, `textual>=0.79,<2` |
| Dev extras | `mypy`, `pytest`, `pytest-cov`, `ruff`, `types-PyYAML` |
| Optional | `rpy2>=3.5` (R survival support) |
| Tracked files | 183 total (137 Python, 44 pytest modules) |
| Tracked Markdown | 29 files |
| Console script | `supermedicine = "Cli:main"` |
| Setuptools modules | `py-modules = ["Cli", "Install"]` |
| Package discovery | `core*`, `permission*`, `agents*`, `plugins*`, `adapters*` |
| Package data | `permission/default_policy.yaml` |
| Pytest discovery | `testpaths = ["tests"]`, `python_files = ["test_*.py"]` |

### Verification Commands (Tester-owned)

| Gate | Command |
| --- | --- |
| Dev install | `python -m pip install -e ".[dev]"` |
| Lint | `python -m ruff check --select=E,F,W --ignore=E501 .` |
| Type check | `python -m mypy . --cache-dir <temp>` |
| Wheel build | `python -m pip wheel . --no-deps --wheel-dir <temp>` |
| Sdist build | `python -m build --sdist --outdir <temp>` |
| Repo hygiene | `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp>` |
| Full tests | `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp>` |
| CLI smoke | `supermedicine status`, `supermedicine init`, `supermedicine run ...`, `python Install.py --init`, `python Cli.py status` |

### Latest Verification Evidence (Pass 33)

All gates passed: install, lint (`ruff`), type check (`mypy`), wheel build, sdist build, repo hygiene pytest, full regression pytest. Path/case collision, path/reference integrity, diff scope, and secret/local-state checks all passed. Final tracked diff is audit-document only.

---

## Allowed Optimization Categories

Only when safe and non-semantic:
- Documentation/prose cleanup including independent word initial capitalization where it does not alter code identifiers, commands, paths, IDs, or quoted literals.
- Safe path capitalization only when all references are fully synchronized and non-breaking on both case-sensitive and case-insensitive filesystems.
- Exact duplicate prose deletion when semantically identical and no unique context is lost.
- Generated/ignored artifact cleanup per the policy above.
- UTF-8/LF formatting normalization only if already project standard and strictly non-semantic.

---

## Conclusion

Across 34 audit passes, the repository optimization has been intentionally conservative:
- **Zero renames** — every path is tied to import/discovery/manifest/platform conventions
- **Zero source/content deduplication** — all duplicates are preserved for standalone usability or platform consumption
- **Generated artifacts cleaned** on each pass when accessible
- **All verification gates pass** — install, lint, type, build, test, hygiene, path integrity
- **Final diff is always audit-document only** — no functional semantic change across any pass

---

## Appendix: Early Audit Step 1 File Classification

*Extracted from OptimizationAudit.md (2026-05-26) for historical reference.*

### Modified Tracked Documentation / Metadata Files
- `ARCHITECTURE.md`, `Architecture/ExecutionRoadmap.md`, `README.md`, `SECURITY.md`, `pyproject.toml`

### Modified Tracked Application / Plugin Files
- `Cli.py`, `core/kernel.py`, `plugins/rag/main.py`

### Untracked Architecture / Documentation Files
- `Architecture/PhaseImplementationPlan.md`, `Architecture/WorkspaceTuiRagGuide.md`

### Untracked Core Implementation Files / Directories
- `core/experience.py`, `core/operation_guard.py`, `core/paper_import/`, `core/path_safety.py`, `core/tui/`, `core/workspace.py`, `core/workspace_tools.py`

### Untracked Tests
- `tests/test_backward_compatibility.py`, `tests/test_experience_cli.py`, `tests/test_experience_storage.py`, `tests/test_operation_guard.py`, `tests/test_paper_cli.py`, `tests/test_paper_import_core.py`, `tests/test_path_safety.py`, `tests/test_tui_dialog_history.py`, `tests/test_tui_entrypoint.py`, `tests/test_tui_experience_screens.py`, `tests/test_tui_paper_screens.py`, `tests/test_tui.py`, `tests/test_tui_state.py`, `tests/test_tui.py`, `tests/test_workspace.py`, `tests/test_workspace_cli.py`, `tests/test_workspace_full.py`

---

## Appendix: Platform Documentation Model

*Extracted from OptimizationAudit.md Step 6 (2026-05-26).*

The intended model is **core independent + platform add-ons**:
- The SuperMedicine Python core is the default runtime and should remain usable without OpenCode, Claude Code, or assistant-platform configuration.
- User-facing installation examples should include a pure Python path using `pip install -e .`, `python Install.py --init`, `python Cli.py status`, and `python Cli.py run ...`.
- OpenCode documentation should describe the adapter as optional add-on content with implemented tool mappings and metadata, not as a core requirement or as a complete native subagent runtime bridge.
- Claude Code documentation should describe a minimal optional adapter with capability/runtime/local CLI invocation support only; native skill loading and native subagent dispatch are not supported.
- Safety boundaries remain unchanged: runtime PermissionEngine checks are the enforcement path, prompt constraints are advisory, and medical outputs require qualified human review.
