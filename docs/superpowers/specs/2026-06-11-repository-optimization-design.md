# Repository Optimization Design

**Date:** 2026-06-11
**Author:** Brain (Orchestrator)
**Status:** Approved

## Overview

Comprehensive repository cleanup and optimization to improve code quality, fix broken references, and standardize naming conventions.

## Requirements

1. **No functionality changes** - All changes must preserve original behavior
2. **PascalCase for non-Python files** - Independent words capitalized
3. **Snake_case for Python modules** - Per PEP 8
4. **Sync code references** - Update all file name references in code
5. **Remove duplicates** - Delete redundant files
6. **Keep repository clean** - Remove orphaned files

## Design Sections

### 1. Entry Point File Renames

**Files to rename:**
| Current | New |
|---------|-----|
| `Cli.py` | `cli_entry.py` |
| `Install.py` | `install_entry.py` |
| `Uninstall.py` | `uninstall_entry.py` |

**References to update:**
- `pyproject.toml` line 69: `supermedicine = "Cli:main"` → `supermedicine = "cli_entry:main"`
- `setup.py` lines 21-54: Update all entry point references
- Any imports that reference these files

**Verification:** `pytest tests/` should pass after changes.

### 2. Stale Cross-Reference Fixes

**Files with broken `Architecture/` references:**
| File | Fix |
|------|-----|
| `CONTRIBUTING.md` | `Architecture/` → `docs/archive/` |
| `FUNCTION_MAP.md` | `Architecture/` → `docs/archive/` |
| `INSTALL.md` | `Architecture/` → `docs/archive/` |
| `tests/test_repo_hygiene.py` | `Architecture/` → `docs/archive/` |
| `docs/superpowers/plans/2026-06-10-repository-structure-optimization.md` | `Architecture/` → `docs/archive/` |

**Verification:** `grep -r "Architecture/" --include="*.md" --include="*.py"` should return no results outside `docs/archive/`.

### 3. MANIFEST.in Fixes

**Current (stale):**
```
prune Docs
prune Architecture
```

**New (correct):**
```
prune docs/archive
```

**Verification:** `python setup.py sdist` should succeed.

### 4. Missing `__init__.py`

**Directory:** `plugins/tools/python_data_analysis/`
**Action:** Create empty `__init__.py` to make it a proper Python package.

**Verification:** `python -c "import plugins.tools.python_data_analysis"` should succeed.

### 5. Orphaned File Cleanup

**File:** `assets/logo.svg`
**Reason:** Not referenced by any tracked file. Only `assets/logo.jpg` is used in `README.md`.

**Verification:** `git status` should show file deleted.

### 6. Documentation Naming Standardization

**Files in `docs/archive/` with UPPER_CASE names:**
| Current | New |
|---------|-----|
| `MULTI_AGENT_STATUS.md` | `MultiAgentStatus.md` |
| `REFACTORING_PLAN.md` | `RefactoringPlan.md` |
| `REQUIREMENTS_TRACEABILITY.md` | `RequirementsTraceability.md` |
| `SECURITY_HARDENING_CHECKLIST.md` | `SecurityHardeningChecklist.md` |

**Verification:** All files in `docs/archive/` should follow PascalCase.

### 7. Near-Duplicate Policy Files

**Files:**
- `permission/default_policy.yaml` (5,976 bytes)
- `.supermedicine/policies/default.yaml` (5,988 bytes)

**Action:** Compare content. If identical except for minor formatting, keep `permission/default_policy.yaml` as source of truth and update `.supermedicine/policies/default.yaml` to be a symlink or copy.

**Verification:** `diff` should show no differences.

## Summary

| Category | Files Affected | Risk |
|----------|----------------|------|
| Entry point renames | 5 files | Medium (breaking change) |
| Cross-reference fixes | 5 files | Low |
| MANIFEST.in | 1 file | Low |
| Missing __init__.py | 1 file | Low |
| Orphaned file | 1 file | Low |
| Doc naming | 4 files | Low |
| Policy duplicates | 2 files | Low |

**Total:** 19 files modified/deleted.

## Success Criteria

1. All tests pass (`pytest tests/`)
2. No broken references (`grep -r "Architecture/"` returns empty)
3. All Python modules follow snake_case
4. All non-Python files follow PascalCase
5. No orphaned files
6. Repository size reduced
