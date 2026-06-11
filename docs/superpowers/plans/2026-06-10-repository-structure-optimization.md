# Repository Structure Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize SuperMedicine repository structure by archiving planning documents, cleaning up root-level files, consolidating scripts, removing redundancy, and updating configuration files.

**Architecture:** Five-phase incremental cleanup that preserves all tracked source, tests, CI, and maintainer documentation while moving planning artifacts to an archive, removing local-only files from git tracking, consolidating script locations, and updating configuration to reflect the new structure.

**Tech Stack:** Git, Python, PowerShell

---

## File Structure Changes

### Files to Archive (move to `docs/archive/`)
- `Architecture/Beta0.4.2ShortTermPlan.md`
- `Architecture/DebugBugFixPlan.md`
- `Architecture/DebugReviewTaskLedger.md`
- `Architecture/ExecutionRoadmap.md`
- `Architecture/FunctionMapASTInventory.md`
- `Architecture/MaintainerRepositoryReading.md`
- `Architecture/MULTI_AGENT_STATUS.md`
- `Architecture/PhaseImplementationPlan.md`
- `Architecture/PlatformIntegrationAudit.md`
- `Architecture/REFACTORING_PLAN.md`
- `Architecture/RepositoryOptimizationAudit.md`
- `Architecture/WEB_INTERFACE_PLAN.md`
- `Architecture/WorkspaceTuiRagGuide.md`

### Files to Remove from Git Tracking
- `REQUIREMENTS_TRACEABILITY.md` (keep local file, remove from index)

### Files to Relocate
- `scripts/tui_preview_artifact.py` → `core/tui/preview_artifact.py`
- `scripts/__init__.py` → delete (empty module after move)

### Files to Modify
- `.gitignore` - add `docs/archive/` tracking rules
- `MANIFEST.in` - no changes needed (already excludes `Architecture/`)
- `pyproject.toml` - no changes needed (scripts not in package-find)
- `tests/test_tui_entrypoint.py` - update import path
- `ARCHITECTURE.md` - update reference to archived files
- `docs/guides/architecture.md` - keep as-is (complementary guide, not redundant)

### Directories to Create
- `docs/archive/`

### Directories to Remove (after moves)
- `Architecture/` - keep folder, remove contents (or delete if empty)

---

## Task 1: Archive Planning Documents from Architecture/

**Files:**
- Create: `docs/archive/` (directory)
- Move: 13 files from `Architecture/` to `docs/archive/`
- Modify: `.gitignore` (add archive tracking rules)
- Modify: `ARCHITECTURE.md` (update references)

- [ ] **Step 1: Create archive directory**

```powershell
New-Item -ItemType Directory -Path "docs\archive" -Force
```

- [ ] **Step 2: Move all Architecture/ files to docs/archive/**

```powershell
$files = @(
    "Beta0.4.2ShortTermPlan.md",
    "DebugBugFixPlan.md",
    "DebugReviewTaskLedger.md",
    "ExecutionRoadmap.md",
    "FunctionMapASTInventory.md",
    "MaintainerRepositoryReading.md",
    "MULTI_AGENT_STATUS.md",
    "PhaseImplementationPlan.md",
    "PlatformIntegrationAudit.md",
    "REFACTORING_PLAN.md",
    "RepositoryOptimizationAudit.md",
    "WEB_INTERFACE_PLAN.md",
    "WorkspaceTuiRagGuide.md"
)
foreach ($f in $files) {
    git mv "Architecture\$f" "docs\archive\$f"
}
```

- [ ] **Step 3: Remove empty Architecture/ folder if git allows**

```powershell
# Check if Architecture/ is empty after moves
$remaining = Get-ChildItem -Path "Architecture" -ErrorAction SilentlyContinue
if (-not $remaining) {
    Remove-Item -Path "Architecture" -Force
}
```

- [ ] **Step 4: Update .gitignore to track docs/archive/**

Add after line 138 (`!Architecture/**`):

```gitignore
!docs/
!docs/**
!docs/archive/
!docs/archive/**
```

- [ ] **Step 5: Update ARCHITECTURE.md references**

In `ARCHITECTURE.md`, update any references to `Architecture/` files to point to `docs/archive/`. Specifically, search for lines like:
- `Architecture/ExecutionRoadmap.md` → `docs/archive/ExecutionRoadmap.md`
- `Architecture/MaintainerRepositoryReading.md` → `docs/archive/MaintainerRepositoryReading.md`
- etc.

- [ ] **Step 6: Update .gitignore to remove Architecture/ tracking rules**

Remove or comment out lines 137-138:
```gitignore
# !Architecture/
# !Architecture/**
```

- [ ] **Step 7: Verify archive structure**

Run: `git status`
Expected: All 13 files show as renamed from `Architecture/` to `docs/archive/`

Run: `ls docs/archive/`
Expected: 13 `.md` files present

---

## Task 2: Remove REQUIREMENTS_TRACEABILITY.md from Git Tracking

**Files:**
- Modify: `REQUIREMENTS_TRACEABILITY.md` (remove from index, keep local)

- [ ] **Step 1: Verify file is currently tracked**

```powershell
git ls-files --error-unmatch REQUIREMENTS_TRACEABILITY.md
```

Expected: File path output (confirms it's tracked)

- [ ] **Step 2: Remove from git index only**

```powershell
git rm --cached REQUIREMENTS_TRACEABILITY.md
```

Expected: `rm 'REQUIREMENTS_TRACEABILITY.md'`

- [ ] **Step 3: Verify .gitignore rule exists**

Check that line 74 contains `/REQUIREMENTS_TRACEABILITY.md`

- [ ] **Step 4: Verify file still exists locally**

```powershell
Test-Path REQUIREMENTS_TRACEABILITY.md
```

Expected: `True`

- [ ] **Step 5: Verify git status shows deletion from index**

```powershell
git status REQUIREMENTS_TRACEABILITY.md
```

Expected: Shows as deleted (from index) but file still on disk

---

## Task 3: Consolidate scripts/tui_preview_artifact.py to core/tui/

**Files:**
- Move: `scripts/tui_preview_artifact.py` → `core/tui/preview_artifact.py`
- Delete: `scripts/__init__.py`
- Delete: `scripts/` directory (if empty after moves)
- Modify: `tests/test_tui_entrypoint.py` (update import)

- [ ] **Step 1: Move the script file**

```powershell
git mv scripts\tui_preview_artifact.py core\tui\preview_artifact.py
```

- [ ] **Step 2: Remove scripts/__init__.py**

```powershell
git rm scripts\__init__.py
```

- [ ] **Step 3: Remove empty scripts/ directory**

```powershell
$remaining = Get-ChildItem -Path "scripts" -ErrorAction SilentlyContinue
if (-not $remaining) {
    Remove-Item -Path "scripts" -Force
}
```

- [ ] **Step 4: Update import in tests/test_tui_entrypoint.py**

Change line 15 from:
```python
from scripts.tui_preview_artifact import write_preview_artifact
```
To:
```python
from core.tui.preview_artifact import write_preview_artifact
```

- [ ] **Step 5: Update import in core/tui/preview_artifact.py if needed**

Check if the file has any relative imports that need adjustment. Current imports are absolute (`from core.tui.app import ...`), so no changes needed.

- [ ] **Step 6: Verify import works**

```powershell
python -c "from core.tui.preview_artifact import write_preview_artifact; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Run affected tests**

```powershell
pytest tests/test_tui_entrypoint.py -v
```

Expected: All tests pass

---

## Task 4: Verify Architecture Doc Redundancy (No Code Changes)

**Files:**
- Read: `ARCHITECTURE.md`
- Read: `docs/guides/architecture.md`

- [ ] **Step 1: Compare document purposes**

After review:
- `ARCHITECTURE.md` (225 lines): Full technical reference for Beta0.4.2 design. Covers microkernel, permission system, plugin registry, workspace, LLM providers, agents, adapters in detail.
- `docs/guides/architecture.md` (263 lines): Guide that explains the architecture in a more accessible way. Line 4 explicitly states: "For the full technical reference, see [ARCHITECTURE.md](../../ARCHITECTURE.md)."

**Conclusion:** These are NOT redundant. They serve complementary purposes:
- `ARCHITECTURE.md` = authoritative technical reference
- `docs/guides/architecture.md` = user-friendly guide pointing to the reference

**Action:** Keep both files unchanged.

- [ ] **Step 2: Document decision**

No code changes required. The two files are complementary, not redundant.

---

## Task 5: Update Configuration Files

**Files:**
- Modify: `.gitignore`
- Verify: `MANIFEST.in` (no changes needed)
- Verify: `pyproject.toml` (no changes needed)

- [ ] **Step 1: Update .gitignore for new structure**

Add tracking rules for `docs/archive/` after the existing `!docs/` rules (around line 136):

```gitignore
# Track docs/ and docs/archive/ for archived planning documents
!docs/
!docs/**
!docs/archive/
!docs/archive/**
```

- [ ] **Step 2: Remove Architecture/ tracking rules**

Remove or comment out lines 137-138:
```gitignore
# !Architecture/
# !Architecture/**
```

- [ ] **Step 3: Verify MANIFEST.in needs no changes**

Current `MANIFEST.in` line 18: `prune Architecture`
This already excludes Architecture from distribution. After archiving, this line becomes harmless (no-op). No change needed.

- [ ] **Step 4: Verify pyproject.toml needs no changes**

Current `pyproject.toml`:
- `py-modules = ["Cli", "Uninstall"]` - scripts not included
- `[tool.setuptools.packages.find]` - `scripts` not in include list
- No references to `scripts/` module

No changes needed.

- [ ] **Step 5: Verify git status is clean**

```powershell
git status
```

Expected: Only intended changes shown (renamed files, deleted files, modified files)

---

## Task 6: Final Verification and Commit

**Files:**
- All modified files from Tasks 1-5

- [ ] **Step 1: Run full test suite**

```powershell
pytest tests/ -v --tb=short
```

Expected: All tests pass (same baseline as before changes)

- [ ] **Step 2: Run repo hygiene tests**

```powershell
pytest tests/test_repo_hygiene.py -v
```

Expected: All hygiene checks pass

- [ ] **Step 3: Verify no broken imports**

```powershell
python -c "from core.tui.preview_artifact import write_preview_artifact; print('Import OK')"
python -c "import Cli; print('CLI OK')"
```

Expected: Both print success messages

- [ ] **Step 4: Verify archive structure**

```powershell
Get-ChildItem docs/archive/ | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: 13 files

- [ ] **Step 5: Verify Architecture/ is empty or removed**

```powershell
Test-Path Architecture
```

Expected: `False` (folder removed) or empty directory

- [ ] **Step 6: Verify REQUIREMENTS_TRACEABILITY.md is untracked but exists**

```powershell
git ls-files REQUIREMENTS_TRACEABILITY.md  # Should return empty
Test-Path REQUIREMENTS_TRACEABILITY.md     # Should return True
```

- [ ] **Step 7: Stage and commit all changes**

```powershell
git add -A
git status  # Review staged changes
git commit -m "refactor: archive planning docs, consolidate scripts, clean up structure

- Move 13 Architecture/ planning docs to docs/archive/
- Remove REQUIREMENTS_TRACEABILITY.md from git tracking (kept local)
- Move scripts/tui_preview_artifact.py to core/tui/preview_artifact.py
- Remove empty scripts/ directory
- Update .gitignore for new structure
- Update test imports for relocated script"
```

---

## Verification Summary

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Archive files exist | `ls docs/archive/` | 13 .md files |
| Architecture empty | `ls Architecture/` | Directory not found or empty |
| Script moved | `ls core/tui/preview_artifact.py` | File exists |
| Scripts removed | `ls scripts/` | Directory not found |
| Import works | `python -c "from core.tui.preview_artifact import write_preview_artifact"` | OK |
| Test passes | `pytest tests/test_tui_entrypoint.py -v` | All pass |
| File untracked | `git ls-files REQUIREMENTS_TRACEABILITY.md` | Empty output |
| File exists locally | `Test-Path REQUIREMENTS_TRACEABILITY.md` | True |
| Git status clean | `git status` | No unexpected changes |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| External references to Architecture/ paths | Broken links in docs | Update all references in ARCHITECTURE.md and other docs |
| Test failures after script move | CI breaks | Update import in test_tui_entrypoint.py before running tests |
| .gitignore rules not taking effect | Files not tracked | Verify with `git status` after changes |
| REQUIREMENTS_TRACEABILITY.md accidentally deleted | Data loss | Use `git rm --cached` not `git rm` |
| docs/archive/ not tracked | Archive files ignored | Add explicit `!docs/archive/` rules to .gitignore |
