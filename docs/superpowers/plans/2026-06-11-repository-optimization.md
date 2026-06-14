# Repository Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comprehensive repository cleanup and optimization to improve code quality, fix broken references, and standardize naming conventions.

**Architecture:** Rename entry point files to snake_case, fix stale cross-references, clean up orphaned files, and standardize documentation naming.

**Tech Stack:** Python, Git, Markdown

---

## File Structure

### Files to Rename
| Current | New |
|---------|-----|
| `Cli.py` | `cli_entry.py` |
| `Install.py` | `install_entry.py` |
| `Uninstall.py` | `uninstall_entry.py` |

### Files to Modify
- `pyproject.toml` - Update entry point references
- `setup.py` - Update entry point references
- `CONTRIBUTING.md` - Fix `Architecture/` references
- `FUNCTION_MAP.md` - Fix `Architecture/` references
- `INSTALL.md` - Fix `Architecture/` references
- `tests/test_repo_hygiene.py` - Fix `Architecture/` references
- `docs/superpowers/plans/2026-06-10-repository-structure-optimization.md` - Fix `Architecture/` references
- `MANIFEST.in` - Remove stale `prune` entries

### Files to Create
- `plugins/tools/python_data_analysis/__init__.py` - Missing package init

### Files to Delete
- `assets/logo.svg` - Orphaned file

### Files to Rename (Documentation)
| Current | New |
|---------|-----|
| `docs/archive/MULTI_AGENT_STATUS.md` | `docs/archive/MultiAgentStatus.md` |
| `docs/archive/REFACTORING_PLAN.md` | `docs/archive/RefactoringPlan.md` |
| `docs/archive/REQUIREMENTS_TRACEABILITY.md` | `docs/archive/RequirementsTraceability.md` |
| `docs/archive/SECURITY_HARDENING_CHECKLIST.md` | `docs/archive/SecurityHardeningChecklist.md` |

---

## Task 1: Rename Entry Point Files

**Files:**
- Rename: `Cli.py` → `cli_entry.py`
- Rename: `Install.py` → `install_entry.py`
- Rename: `Uninstall.py` → `uninstall_entry.py`
- Modify: `pyproject.toml:69`
- Modify: `setup.py:21-54`

- [ ] **Step 1: Rename Cli.py to cli_entry.py**

```bash
git mv Cli.py cli_entry.py
```

- [ ] **Step 2: Rename Install.py to install_entry.py**

```bash
git mv Install.py install_entry.py
```

- [ ] **Step 3: Rename Uninstall.py to uninstall_entry.py**

```bash
git mv Uninstall.py uninstall_entry.py
```

- [ ] **Step 4: Update pyproject.toml entry point**

Read `pyproject.toml` line 69 and update:
```toml
# Before
supermedicine = "Cli:main"

# After
supermedicine = "cli_entry:main"
```

- [ ] **Step 5: Update setup.py entry points**

Read `setup.py` lines 21-54 and update all references to `Cli`, `Install`, `Uninstall` to use new names.

- [ ] **Step 6: Verify tests pass**

```bash
pytest tests/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add cli_entry.py install_entry.py uninstall_entry.py pyproject.toml setup.py
git commit -m "refactor: rename entry point files to snake_case"
```

---

## Task 2: Fix Stale Cross-References

**Files:**
- Modify: `CONTRIBUTING.md`
- Modify: `FUNCTION_MAP.md`
- Modify: `INSTALL.md`
- Modify: `tests/test_repo_hygiene.py`
- Modify: `docs/superpowers/plans/2026-06-10-repository-structure-optimization.md`

- [ ] **Step 1: Fix CONTRIBUTING.md references**

Read `CONTRIBUTING.md` and replace all `Architecture/` with `docs/archive/`.

- [ ] **Step 2: Fix FUNCTION_MAP.md references**

Read `FUNCTION_MAP.md` and replace all `Architecture/` with `docs/archive/`.

- [ ] **Step 3: Fix INSTALL.md references**

Read `INSTALL.md` and replace all `Architecture/` with `docs/archive/`.

- [ ] **Step 4: Fix test_repo_hygiene.py references**

Read `tests/test_repo_hygiene.py` and replace all `Architecture/` with `docs/archive/`.

- [ ] **Step 5: Fix optimization plan references**

Read `docs/superpowers/plans/2026-06-10-repository-structure-optimization.md` and replace all `Architecture/` with `docs/archive/`.

- [ ] **Step 6: Verify no stale references remain**

```bash
grep -r "Architecture/" --include="*.md" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.toml" .
```

Expected: No results outside `docs/archive/` directory.

- [ ] **Step 7: Commit**

```bash
git add CONTRIBUTING.md FUNCTION_MAP.md INSTALL.md tests/test_repo_hygiene.py docs/superpowers/plans/2026-06-10-repository-structure-optimization.md
git commit -m "fix: update Architecture/ references to docs/archive/"
```

---

## Task 3: Fix MANIFEST.in

**Files:**
- Modify: `MANIFEST.in`

- [ ] **Step 1: Read MANIFEST.in**

Read `MANIFEST.in` and identify stale entries.

- [ ] **Step 2: Update MANIFEST.in**

Remove stale entries:
```
prune Docs
prune Architecture
```

Add correct entry:
```
prune docs/archive
```

- [ ] **Step 3: Verify MANIFEST.in**

```bash
python setup.py sdist
```

- [ ] **Step 4: Commit**

```bash
git add MANIFEST.in
git commit -m "fix: update MANIFEST.in with correct directory paths"
```

---

## Task 4: Add Missing __init__.py

**Files:**
- Create: `plugins/tools/python_data_analysis/__init__.py`

- [ ] **Step 1: Create __init__.py**

Create empty `__init__.py` file:
```bash
touch plugins/tools/python_data_analysis/__init__.py
```

- [ ] **Step 2: Verify import works**

```bash
python -c "import plugins.tools.python_data_analysis; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/tools/python_data_analysis/__init__.py
git commit -m "feat: add missing __init__.py to python_data_analysis plugin"
```

---

## Task 5: Remove Orphaned Files

**Files:**
- Delete: `assets/logo.svg`

- [ ] **Step 1: Verify logo.svg is orphaned**

```bash
grep -r "logo.svg" --include="*.md" --include="*.py" --include="*.html" --include="*.yaml" --include="*.json" .
```

Expected: No results.

- [ ] **Step 2: Delete logo.svg**

```bash
git rm assets/logo.svg
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove orphaned logo.svg file"
```

---

## Task 6: Standardize Documentation Naming

**Files:**
- Rename: `docs/archive/MULTI_AGENT_STATUS.md` → `docs/archive/MultiAgentStatus.md`
- Rename: `docs/archive/REFACTORING_PLAN.md` → `docs/archive/RefactoringPlan.md`
- Rename: `docs/archive/REQUIREMENTS_TRACEABILITY.md` → `docs/archive/RequirementsTraceability.md`
- Rename: `docs/archive/SECURITY_HARDENING_CHECKLIST.md` → `docs/archive/SecurityHardeningChecklist.md`

- [ ] **Step 1: Rename MULTI_AGENT_STATUS.md**

```bash
git mv docs/archive/MULTI_AGENT_STATUS.md docs/archive/MultiAgentStatus.md
```

- [ ] **Step 2: Rename REFACTORING_PLAN.md**

```bash
git mv docs/archive/REFACTORING_PLAN.md docs/archive/RefactoringPlan.md
```

- [ ] **Step 3: Rename REQUIREMENTS_TRACEABILITY.md**

```bash
git mv docs/archive/REQUIREMENTS_TRACEABILITY.md docs/archive/RequirementsTraceability.md
```

- [ ] **Step 4: Rename SECURITY_HARDENING_CHECKLIST.md**

```bash
git mv docs/archive/SECURITY_HARDENING_CHECKLIST.md docs/archive/SecurityHardeningChecklist.md
```

- [ ] **Step 5: Update cross-references**

Check if any files reference the old names and update them.

- [ ] **Step 6: Verify all files follow PascalCase**

```bash
ls docs/archive/
```

Expected: All files should use PascalCase naming.

- [ ] **Step 7: Commit**

```bash
git add docs/archive/
git commit -m "refactor: standardize docs/archive/ naming to PascalCase"
```

---

## Task 7: Handle Near-Duplicate Policy Files

**Files:**
- Compare: `permission/default_policy.yaml` and `.supermedicine/policies/default.yaml`

- [ ] **Step 1: Compare policy files**

```bash
diff permission/default_policy.yaml .supermedicine/policies/default.yaml
```

- [ ] **Step 2: If identical, update .supermedicine/policies/default.yaml**

If files are identical except formatting:
```bash
cp permission/default_policy.yaml .supermedicine/policies/default.yaml
```

- [ ] **Step 3: Commit**

```bash
git add .supermedicine/policies/default.yaml
git commit -m "fix: sync policy files with permission/default_policy.yaml"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -x -q
```

- [ ] **Step 2: Verify no stale references**

```bash
grep -r "Architecture/" --include="*.md" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.toml" .
```

Expected: No results outside `docs/archive/`.

- [ ] **Step 3: Verify all Python modules follow snake_case**

```bash
find . -name "*.py" | grep -E "[A-Z]" | grep -v "__pycache__"
```

Expected: Only `cli_entry.py`, `install_entry.py`, `uninstall_entry.py` (which are entry points).

- [ ] **Step 4: Verify repository is clean**

```bash
git status
```

Expected: Working tree clean.

- [ ] **Step 5: Push to remote**

```bash
git push origin master
```

---

## Summary

| Task | Description | Files Affected |
|------|-------------|----------------|
| 1 | Rename entry point files | 5 |
| 2 | Fix stale cross-references | 5 |
| 3 | Fix MANIFEST.in | 1 |
| 4 | Add missing __init__.py | 1 |
| 5 | Remove orphaned files | 1 |
| 6 | Standardize documentation naming | 4 |
| 7 | Handle near-duplicate policy files | 1 |
| 8 | Final verification | - |

**Total:** 18 files modified/deleted/created.
