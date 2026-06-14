# Test Files and CI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor SuperMedicine test files and CI configuration to reduce file count, eliminate duplication, extract inline scripts, and streamline repo hygiene checks.

**Architecture:** Merge 15 groups of functionally-related test files into consolidated modules, extract duplicated helper functions into `conftest.py`, prune purely structural checks from `test_repo_hygiene.py`, and extract two large inline Python scripts from `ci.yml` into standalone `scripts/ci/` modules with shared logic.

**Tech Stack:** Python 3.10+, pytest, PyInstaller, GitHub Actions YAML

---

## File Structure

### Files to Create
| Path | Responsibility |
|------|----------------|
| `tests/test_installer.py` | Merged: installer entrypoint + exe release + uninstall |
| `tests/test_tui.py` | Merged: 13 tui_* files |
| `tests/test_database_full.py` | Merged: database + database_integration |
| `tests/test_checkpoint_full.py` | Merged: checkpoint + checkpoint_verifier |
| `tests/test_kernel_full.py` | Merged: kernel + kernel_llm_chat |
| `tests/test_release.py` | Merged: release_smoke + beta042_release_validation |
| `tests/test_permission_full.py` | Merged: permission_engine + permission_modes |
| `tests/test_agents_full.py` | Merged: agents_unit + orchestrator + state_machine |
| `tests/test_adapters.py` | Merged: claude_code_adapter + opencode_adapter + standalone_adapter |
| `tests/test_workspace_full.py` | Merged: workspace + workspace_cli + workspace_tools |
| `tests/test_experience_full.py` | Merged: experience_storage + experience_cli |
| `tests/test_experiment_full.py` | Merged: experiment_cli + experiment_guide + experiment_log_integration + experiment_wb_plugin |
| `tests/test_paper_full.py` | Merged: paper_cli + paper_import_core |
| `tests/test_llm_full.py` | Merged: llm_client + llm_manager + custom_provider |
| `tests/test_self_evolution_full.py` | Merged: self_evolution + self_evolution_cli |
| `scripts/ci/_packaging_common.py` | Shared packaging logic (should_exclude, include_files, include_dirs, directory traversal copy) |
| `scripts/ci/build_installer_payload.py` | Build standalone installer payload + PyInstaller packaging |
| `scripts/ci/build_release_zip.py` | Build release Zip archive + output GitHub Actions variables |

### Files to Modify
| Path | Change |
|------|--------|
| `tests/conftest.py` | Add 5 shared helper functions/fixtures |
| `tests/test_repo_hygiene.py` | Remove 5 purely structural tests, consolidate duplicate secret scans |
| `.github/workflows/ci.yml` | Replace 2 inline Python scripts with `python scripts/ci/...` calls |

### Files to Delete (after merge verification)
| Path | Reason |
|------|--------|
| `tests/test_installer_entrypoint.py` | Merged into test_installer.py |
| `tests/test_installer_exe_release.py` | Merged into test_installer.py |
| `tests/test_uninstall.py` | Merged into test_installer.py |
| `tests/test_tui_chat_view.py` | Merged into test_tui.py |
| `tests/test_tui_dashboard.py` | Merged into test_tui.py |
| `tests/test_tui_dialog_history.py` | Merged into test_tui.py |
| `tests/test_tui_entrypoint.py` | Merged into test_tui.py |
| `tests/test_tui_experience_screens.py` | Merged into test_tui.py |
| `tests/test_tui_experiment_screen.py` | Merged into test_tui.py |
| `tests/test_tui_invalid_table_actions.py` | Merged into test_tui.py |
| `tests/test_tui_llm_screen.py` | Merged into test_tui.py |
| `tests/test_tui_log_screen.py` | Merged into test_tui.py |
| `tests/test_tui_paper_screens.py` | Merged into test_tui.py |
| `tests/test_tui_permissions.py` | Merged into test_tui.py |
| `tests/test_tui_state.py` | Merged into test_tui.py |
| `tests/test_tui_workspace_screens.py` | Merged into test_tui.py |
| `tests/test_database.py` | Merged into test_database_full.py |
| `tests/test_database_integration.py` | Merged into test_database_full.py |
| `tests/test_checkpoint.py` | Merged into test_checkpoint_full.py |
| `tests/test_checkpoint_verifier.py` | Merged into test_checkpoint_full.py |
| `tests/test_kernel.py` | Merged into test_kernel_full.py |
| `tests/test_kernel_llm_chat.py` | Merged into test_kernel_full.py |
| `tests/test_release_smoke.py` | Merged into test_release.py |
| `tests/test_beta042_release_validation.py` | Merged into test_release.py |
| `tests/test_permission_engine.py` | Merged into test_permission_full.py |
| `tests/test_permission_modes.py` | Merged into test_permission_full.py |
| `tests/test_agents_unit.py` | Merged into test_agents_full.py |
| `tests/test_orchestrator.py` | Merged into test_agents_full.py |
| `tests/test_state_machine.py` | Merged into test_agents_full.py |
| `tests/test_claude_code_adapter.py` | Merged into test_adapters.py |
| `tests/test_opencode_adapter.py` | Merged into test_adapters.py |
| `tests/test_standalone_adapter.py` | Merged into test_adapters.py |
| `tests/test_workspace.py` | Merged into test_workspace_full.py |
| `tests/test_workspace_cli.py` | Merged into test_workspace_full.py |
| `tests/test_workspace_tools.py` | Merged into test_workspace_full.py |
| `tests/test_experience_storage.py` | Merged into test_experience_full.py |
| `tests/test_experience_cli.py` | Merged into test_experience_full.py |
| `tests/test_experiment_cli.py` | Merged into test_experiment_full.py |
| `tests/test_experiment_guide.py` | Merged into test_experiment_full.py |
| `tests/test_experiment_log_integration.py` | Merged into test_experiment_full.py |
| `tests/test_experiment_wb_plugin.py` | Merged into test_experiment_full.py |
| `tests/test_paper_cli.py` | Merged into test_paper_full.py |
| `tests/test_paper_import_core.py` | Merged into test_paper_full.py |
| `tests/test_llm_client.py` | Merged into test_llm_full.py |
| `tests/test_llm_manager.py` | Merged into test_llm_full.py |
| `tests/test_custom_provider.py` | Merged into test_llm_full.py |
| `tests/test_self_evolution.py` | Merged into test_self_evolution_full.py |
| `tests/test_self_evolution_cli.py` | Merged into test_self_evolution_full.py |

---

## Task 1: Extract Shared Helpers to conftest.py

**Files:**
- Modify: `tests/conftest.py`
- Verify: `tests/test_installer_entrypoint.py`, `tests/test_installer_exe_release.py`, `tests/test_release_smoke.py`, `tests/test_repo_hygiene.py`, `tests/test_beta042_release_validation.py`

- [ ] **Step 1: Add shared helper functions to conftest.py**

Add the following functions and fixtures to the end of `tests/conftest.py`:

```python
def _has_exact_child_name(directory: Path, filename: str) -> bool:
    """Return whether a directory contains an entry with this exact spelling.

    Path.exists()/is_file() are not sufficient here because Windows filesystems are
    commonly case-insensitive: ``Path("install_entry.py").is_file()`` can report true
    when only ``install_entry.py`` exists with different casing.
    """
    return filename in {child.name for child in directory.iterdir()}


def _supports_case_distinct_names(directory: Path) -> bool:
    """Return whether this filesystem location can hold exact case-only siblings."""
    upper = directory / "CaseProbe.tmp"
    lower = directory / "caseprobe.tmp"
    try:
        upper.write_text("upper", encoding="utf-8")
        lower.write_text("lower", encoding="utf-8")
        return _has_exact_child_name(directory, upper.name) and _has_exact_child_name(
            directory, lower.name
        )
    finally:
        for path in (upper, lower):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _cp1252_stdio_env() -> dict[str, str]:
    """Return environment dict forcing cp1252 stdio encoding."""
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


@pytest.fixture
def read_pyproject() -> dict:
    """Read and return pyproject.toml as a dict."""
    import re
    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None

    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if tomllib is not None:
        with path.open("rb") as f:
            return tomllib.load(f)
    text = path.read_text(encoding="utf-8")
    result: dict = {"project": {}, "tool": {"setuptools": {"package-data": {}}}}
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if version_match:
        result["project"]["version"] = version_match.group(1)
    optional_dependencies_match = re.search(
        r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if optional_dependencies_match:
        dev_match = re.search(
            r"^dev\s*=\s*\[(.*?)\]",
            optional_dependencies_match.group(1),
            re.MULTILINE | re.DOTALL,
        )
        if dev_match:
            result["project"].setdefault("optional-dependencies", {})["dev"] = (
                re.findall(r'"([^"]+)"', dev_match.group(1))
            )
    current_package_data_key = None
    for line in text.splitlines():
        package_data_match = re.match(r"^(core|installer)\s*=\s*\[", line)
        if package_data_match:
            current_package_data_key = package_data_match.group(1)
            entries = re.findall(r'"([^"]+)"', line)
            result["tool"]["setuptools"]["package-data"][current_package_data_key] = entries
        elif current_package_data_key and line.strip().startswith("]"):
            current_package_data_key = None
    return result


@pytest.fixture
def tracked_files() -> list[str]:
    """Return paths currently present in the Git index."""
    import subprocess
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
```

- [ ] **Step 2: Verify conftest.py loads correctly**

Run: `python -c "import tests.conftest; print('OK')"`
Expected: OK

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `python -m pytest tests/test_installer_entrypoint.py tests/test_installer_exe_release.py tests/test_release_smoke.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass (same as before)

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "refactor(tests): extract shared helpers to conftest.py"
```

---

## Task 2: Create test_installer.py (Merge Group 1)

**Files:**
- Create: `tests/test_installer.py`
- Source: `tests/test_installer_entrypoint.py`, `tests/test_installer_exe_release.py`, `tests/test_uninstall.py`

- [ ] **Step 1: Create test_installer.py by concatenating source files**

Create `tests/test_installer.py` with the following structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 3 files (deduplicated)
3. Module-level constants from all 3 files (deduplicated, e.g. `REPO_ROOT`)
4. Section marker: `# ═══ Installer Entrypoint Tests ═══`
5. All test functions/classes from `test_installer_entrypoint.py` (remove duplicate helper definitions — use `from conftest import _has_exact_child_name, _supports_case_distinct_names, _cp1252_stdio_env`)
6. Section marker: `# ═══ Installer Exe Release Tests ═══`
7. All test functions/classes from `test_installer_exe_release.py` (remove duplicate helper definitions)
8. Section marker: `# ═══ Uninstall Tests ═══`
9. All test functions/classes from `test_uninstall.py`

Key merging rules:
- Remove `_has_exact_child_name`, `_supports_case_distinct_names`, `_cp1252_stdio_env` definitions — import from conftest
- Keep `_git_tracks_exact_path`, `_read_exact_lowercase_install_source`, `_write_minimal_import_stubs`, `_copy_install_entrypoint_without_installer_package`, `_copy_cli_entrypoint_without_installer_package`, `_run_isolated_install`, `_run_isolated_lowercase_install`, `_run_isolated_cli` as local helpers (they are specific to installer tests)
- Keep `_llm_args`, `_make_release_payload` as local helpers
- Keep `REPO_ROOT` as module-level constant
- Keep `INSTALLER_SUBPROCESS_TIMEOUT_SECONDS` as module-level constant

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_installer.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files**

Delete: `tests/test_installer_entrypoint.py`, `tests/test_installer_exe_release.py`, `tests/test_uninstall.py`

- [ ] **Step 4: Verify no test count regression**

Run: `python -m pytest tests/test_installer.py --co -q | wc -l`
Expected: Same total test count as sum of original 3 files

- [ ] **Step 5: Commit**

```bash
git add tests/test_installer.py
git rm tests/test_installer_entrypoint.py tests/test_installer_exe_release.py tests/test_uninstall.py
git commit -m "refactor(tests): merge installer entrypoint + exe release + uninstall into test_installer.py"
```

---

## Task 3: Create test_tui.py (Merge Group 2)

**Files:**
- Create: `tests/test_tui.py`
- Source: 13 `tests/test_tui_*.py` files

- [ ] **Step 1: Create test_tui.py by concatenating source files**

Create `tests/test_tui.py` with the following structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 13 files (deduplicated)
3. Module-level constants and helper classes from all files (deduplicated)
4. For each original file, add a section marker: `# ═══ <original module name> ═══`
5. All test functions/classes from each file, preserving original class structure

Key merging rules:
- Each original file's content goes under a section comment
- Preserve all class-based test organization (e.g., `class CapturingRichLog`, `class CapturingChatView`)
- Deduplicate any shared helper classes/functions
- The file will be large (~2000+ lines) — this is acceptable for a consolidated test module

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_tui.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files**

Delete all 13 `tests/test_tui_*.py` files

- [ ] **Step 4: Verify no test count regression**

Run: `python -m pytest tests/test_tui.py --co -q | wc -l`
Expected: Same total test count as sum of original 13 files

- [ ] **Step 5: Commit**

```bash
git add tests/test_tui.py
git rm tests/test_tui_chat_view.py tests/test_tui_dashboard.py tests/test_tui_dialog_history.py tests/test_tui_entrypoint.py tests/test_tui_experience_screens.py tests/test_tui_experiment_screen.py tests/test_tui_invalid_table_actions.py tests/test_tui_llm_screen.py tests/test_tui_log_screen.py tests/test_tui_paper_screens.py tests/test_tui_permissions.py tests/test_tui_state.py tests/test_tui_workspace_screens.py
git commit -m "refactor(tests): merge 13 tui_* files into test_tui.py"
```

---

## Task 4: Create test_database_full.py (Merge Group 3)

**Files:**
- Create: `tests/test_database_full.py`
- Source: `tests/test_database.py`, `tests/test_database_integration.py`

- [ ] **Step 1: Create test_database_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Database Unit Tests ═══` — all content from `test_database.py`
4. Section: `# ═══ Database Integration Tests ═══` — all content from `test_database_integration.py`
5. Keep `_make_kernel` helper from integration file as local helper

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_database_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_database_full.py
git rm tests/test_database.py tests/test_database_integration.py
git commit -m "refactor(tests): merge database + database_integration into test_database_full.py"
```

---

## Task 5: Create test_checkpoint_full.py (Merge Group 4)

**Files:**
- Create: `tests/test_checkpoint_full.py`
- Source: `tests/test_checkpoint.py`, `tests/test_checkpoint_verifier.py`

- [ ] **Step 1: Create test_checkpoint_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Checkpoint Manager Tests ═══` — all content from `test_checkpoint.py`
4. Section: `# ═══ Checkpoint Verifier Tests ═══` — all content from `test_checkpoint_verifier.py`

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_checkpoint_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_checkpoint_full.py
git rm tests/test_checkpoint.py tests/test_checkpoint_verifier.py
git commit -m "refactor(tests): merge checkpoint + checkpoint_verifier into test_checkpoint_full.py"
```

---

## Task 6: Create test_kernel_full.py (Merge Group 5)

**Files:**
- Create: `tests/test_kernel_full.py`
- Source: `tests/test_kernel.py`, `tests/test_kernel_llm_chat.py`

- [ ] **Step 1: Create test_kernel_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Kernel Tests ═══` — all content from `test_kernel.py`
4. Section: `# ═══ Kernel LLM Chat Tests ═══` — all content from `test_kernel_llm_chat.py`
5. Keep `_create_kernel` and `StreamClient` helpers as local helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_kernel_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_kernel_full.py
git rm tests/test_kernel.py tests/test_kernel_llm_chat.py
git commit -m "refactor(tests): merge kernel + kernel_llm_chat into test_kernel_full.py"
```

---

## Task 7: Create test_release.py (Merge Group 6)

**Files:**
- Create: `tests/test_release.py`
- Source: `tests/test_release_smoke.py`, `tests/test_beta042_release_validation.py`

- [ ] **Step 1: Create test_release.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Module-level constants from both files (deduplicated — `REPO_ROOT`, etc.)
4. Section: `# ═══ Release Smoke Tests ═══` — all content from `test_release_smoke.py`
5. Section: `# ═══ Beta0.4.2 Release Validation ═══` — all content from `test_beta042_release_validation.py`
6. Remove duplicate `_read_pyproject`, `_tracked_files`, `_has_exact_child_name`, `_supports_case_distinct_names`, `_cp1252_stdio_env` — use conftest versions
7. Keep `_extract_bash_pyinstaller_command`, `_token_value`, `_looks_absolute_or_resolved_for_ci_shell`, `_relative_source_is_staged_under_specpath`, `_copy_release_tree`, `_read_git_index_file`, `_run_release_python` as local helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_release.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_release.py
git rm tests/test_release_smoke.py tests/test_beta042_release_validation.py
git commit -m "refactor(tests): merge release_smoke + beta042_release_validation into test_release.py"
```

---

## Task 8: Create test_permission_full.py (Merge Group 7)

**Files:**
- Create: `tests/test_permission_full.py`
- Source: `tests/test_permission_engine.py`, `tests/test_permission_modes.py`

- [ ] **Step 1: Create test_permission_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Permission Engine Tests ═══` — all content from `test_permission_engine.py`
4. Section: `# ═══ Permission Modes Tests ═══` — all content from `test_permission_modes.py`

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_permission_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_permission_full.py
git rm tests/test_permission_engine.py tests/test_permission_modes.py
git commit -m "refactor(tests): merge permission_engine + permission_modes into test_permission_full.py"
```

---

## Task 9: Create test_agents_full.py (Merge Group 8)

**Files:**
- Create: `tests/test_agents_full.py`
- Source: `tests/test_agents_unit.py`, `tests/test_orchestrator.py`, `tests/test_state_machine.py`

- [ ] **Step 1: Create test_agents_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 3 files (deduplicated)
3. Section: `# ═══ Agent Unit Tests ═══` — all content from `test_agents_unit.py`
4. Section: `# ═══ Orchestrator Tests ═══` — all content from `test_orchestrator.py`
5. Section: `# ═══ State Machine Tests ═══` — all content from `test_state_machine.py`
6. Keep `DummyAgent`, `FailingAgent` as local helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_agents_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_agents_full.py
git rm tests/test_agents_unit.py tests/test_orchestrator.py tests/test_state_machine.py
git commit -m "refactor(tests): merge agents_unit + orchestrator + state_machine into test_agents_full.py"
```

---

## Task 10: Create test_adapters.py (Merge Group 9)

**Files:**
- Create: `tests/test_adapters.py`
- Source: `tests/test_claude_code_adapter.py`, `tests/test_opencode_adapter.py`, `tests/test_standalone_adapter.py`

- [ ] **Step 1: Create test_adapters.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 3 files (deduplicated)
3. Section: `# ═══ Claude Code Adapter Tests ═══` — all content from `test_claude_code_adapter.py`
4. Section: `# ═══ OpenCode Adapter Tests ═══` — all content from `test_opencode_adapter.py`
5. Section: `# ═══ Standalone Adapter Tests ═══` — all content from `test_standalone_adapter.py`
6. Deduplicate `FORBIDDEN_PLATFORM_AGENT_NAMES`, `_adapter_with_policy`, `_write_policy` if they appear in multiple files

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_adapters.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_adapters.py
git rm tests/test_claude_code_adapter.py tests/test_opencode_adapter.py tests/test_standalone_adapter.py
git commit -m "refactor(tests): merge claude_code + opencode + standalone adapters into test_adapters.py"
```

---

## Task 11: Create test_workspace_full.py (Merge Group 10)

**Files:**
- Create: `tests/test_workspace_full.py`
- Source: `tests/test_workspace.py`, `tests/test_workspace_cli.py`, `tests/test_workspace_tools.py`

- [ ] **Step 1: Create test_workspace_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 3 files (deduplicated)
3. Section: `# ═══ Workspace Tests ═══` — all content from `test_workspace.py`
4. Section: `# ═══ Workspace CLI Tests ═══` — all content from `test_workspace_cli.py`
5. Section: `# ═══ Workspace Tools Tests ═══` — all content from `test_workspace_tools.py`
6. Deduplicate `REPO_ROOT`, `_copy_default_policy` if shared

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_workspace_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_workspace_full.py
git rm tests/test_workspace.py tests/test_workspace_cli.py tests/test_workspace_tools.py
git commit -m "refactor(tests): merge workspace + workspace_cli + workspace_tools into test_workspace_full.py"
```

---

## Task 12: Create test_experience_full.py (Merge Group 11)

**Files:**
- Create: `tests/test_experience_full.py`
- Source: `tests/test_experience_storage.py`, `tests/test_experience_cli.py`

- [ ] **Step 1: Create test_experience_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Experience Storage Tests ═══` — all content from `test_experience_storage.py`
4. Section: `# ═══ Experience CLI Tests ═══` — all content from `test_experience_cli.py`
5. Deduplicate `_store`, `_prepare_workspace` helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_experience_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_experience_full.py
git rm tests/test_experience_storage.py tests/test_experience_cli.py
git commit -m "refactor(tests): merge experience_storage + experience_cli into test_experience_full.py"
```

---

## Task 13: Create test_experiment_full.py (Merge Group 12)

**Files:**
- Create: `tests/test_experiment_full.py`
- Source: `tests/test_experiment_cli.py`, `tests/test_experiment_guide.py`, `tests/test_experiment_log_integration.py`, `tests/test_experiment_wb_plugin.py`

- [ ] **Step 1: Create test_experiment_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 4 files (deduplicated)
3. Section: `# ═══ Experiment CLI Tests ═══` — all content from `test_experiment_cli.py`
4. Section: `# ═══ Experiment Guide Tests ═══` — all content from `test_experiment_guide.py`
5. Section: `# ═══ Experiment Log Integration Tests ═══` — all content from `test_experiment_log_integration.py`
6. Section: `# ═══ Experiment WB Plugin Tests ═══` — all content from `test_experiment_wb_plugin.py`

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_experiment_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_experiment_full.py
git rm tests/test_experiment_cli.py tests/test_experiment_guide.py tests/test_experiment_log_integration.py tests/test_experiment_wb_plugin.py
git commit -m "refactor(tests): merge 4 experiment files into test_experiment_full.py"
```

---

## Task 14: Create test_paper_full.py (Merge Group 13)

**Files:**
- Create: `tests/test_paper_full.py`
- Source: `tests/test_paper_cli.py`, `tests/test_paper_import_core.py`

- [ ] **Step 1: Create test_paper_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Paper CLI Tests ═══` — all content from `test_paper_cli.py`
4. Section: `# ═══ Paper Import Core Tests ═══` — all content from `test_paper_import_core.py`
5. Deduplicate `REPO_ROOT`, `_copy_default_policy`, `_write_delta_policy` helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_paper_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_paper_full.py
git rm tests/test_paper_cli.py tests/test_paper_import_core.py
git commit -m "refactor(tests): merge paper_cli + paper_import_core into test_paper_full.py"
```

---

## Task 15: Create test_llm_full.py (Merge Group 14)

**Files:**
- Create: `tests/test_llm_full.py`
- Source: `tests/test_llm_client.py`, `tests/test_llm_manager.py`, `tests/test_custom_provider.py`

- [ ] **Step 1: Create test_llm_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from all 3 files (deduplicated)
3. Section: `# ═══ LLM Client Tests ═══` — all content from `test_llm_client.py`
4. Section: `# ═══ LLM Manager Tests ═══` — all content from `test_llm_manager.py`
5. Section: `# ═══ Custom Provider Tests ═══` — all content from `test_custom_provider.py`
6. Deduplicate `_write_config` helpers if shared

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_llm_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_llm_full.py
git rm tests/test_llm_client.py tests/test_llm_manager.py tests/test_custom_provider.py
git commit -m "refactor(tests): merge llm_client + llm_manager + custom_provider into test_llm_full.py"
```

---

## Task 16: Create test_self_evolution_full.py (Merge Group 15)

**Files:**
- Create: `tests/test_self_evolution_full.py`
- Source: `tests/test_self_evolution.py`, `tests/test_self_evolution_cli.py`

- [ ] **Step 1: Create test_self_evolution_full.py**

Structure:
1. Single `from __future__ import annotations` at top
2. All imports from both files (deduplicated)
3. Section: `# ═══ Self Evolution Tests ═══` — all content from `test_self_evolution.py`
4. Section: `# ═══ Self Evolution CLI Tests ═══` — all content from `test_self_evolution_cli.py`
5. Keep `RecordingPermissionEngine`, `_service`, `_cli_json` as local helpers

- [ ] **Step 2: Verify merged file runs correctly**

Run: `python -m pytest tests/test_self_evolution_full.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 3: Delete source files and commit**

```bash
git add tests/test_self_evolution_full.py
git rm tests/test_self_evolution.py tests/test_self_evolution_cli.py
git commit -m "refactor(tests): merge self_evolution + self_evolution_cli into test_self_evolution_full.py"
```

---

## Task 17: Slim Down test_repo_hygiene.py

**Files:**
- Modify: `tests/test_repo_hygiene.py`

- [ ] **Step 1: Remove purely structural tests**

Delete the following test functions from `test_repo_hygiene.py`:

1. `test_function_map_is_authoritative_root_doc_and_traceability_is_local_only` (line 421) — purely structural: checks FUNCTION_MAP.md exists and REQUIREMENTS_TRACEABILITY.md is gitignored
2. `test_case_only_tracked_path_collisions_are_intentional_and_documented` (line 271) — purely structural: checks case-only path collisions
3. `test_local_only_files_are_ignored_by_active_gitignore_rules` (line 399) — partially redundant with `test_gitignore_excludes_runtime_and_external_platform_config_artifacts`; merge the 4 paths into the gitignore pattern test
4. `test_gitignore_keeps_temporary_engineering_artifacts_local_only` (line 438) — purely structural: checks gitignore contains engineering artifact patterns (already covered by `test_gitignore_excludes_runtime_and_external_platform_config_artifacts`)

Also remove associated constants:
- `INTENTIONAL_CASE_ONLY_PATH_COLLISIONS` (line 25) — empty dict, no longer needed
- `COMMIT_ELIGIBLE_MAINTAINER_DOC_EXAMPLES` (line 19) — only used by deleted test
- `FORBIDDEN_LOCAL_ONLY_ROOT_DOCS` (line 24) — only used by deleted tests

- [ ] **Step 2: Consolidate duplicate secret scans**

Merge `test_opencode_adapter_docs_do_not_contain_plaintext_api_key_examples`, `test_claude_code_adapter_docs_do_not_contain_plaintext_api_key_examples`, `test_repository_docs_and_manifests_do_not_contain_realistic_plaintext_secrets`, and `test_root_visible_markdown_docs_do_not_contain_plaintext_example_secrets` into a single parametrized test `test_no_plaintext_secrets_in_docs_and_manifests` that scans all relevant paths in one pass.

- [ ] **Step 3: Verify remaining tests pass**

Run: `python -m pytest tests/test_repo_hygiene.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All remaining tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_repo_hygiene.py
git commit -m "refactor(tests): slim test_repo_hygiene.py — remove structural checks, consolidate secret scans"
```

---

## Task 18: Create scripts/ci/_packaging_common.py

**Files:**
- Create: `scripts/ci/_packaging_common.py`

- [ ] **Step 1: Create the shared packaging module**

Create `scripts/ci/__init__.py` (empty) and `scripts/ci/_packaging_common.py` with:

```python
"""Shared packaging logic for CI build scripts."""

from __future__ import annotations

from pathlib import Path
import shutil

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest-tmp",
    ".pytest_tmp",
}
EXCLUDED_FILE_NAMES = {".env"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".token"}

INCLUDE_FILES = [
    "cli_entry.py",
    "install_entry.py",
    "uninstall_entry.py",
    "pyproject.toml",
    "requirements.txt",
    "install.json",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/guides/INSTALL.md",
]
INCLUDE_DIRS = ["core", "permission", "agents", "plugins", "adapters", "installer"]


def should_exclude(path: Path) -> bool:
    """Return True if this path should be excluded from packaging."""
    if set(path.parts) & EXCLUDED_DIR_NAMES:
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    if path.name.endswith("~") or path.name.endswith(".log"):
        return True
    return False


def copy_include_files(root: Path, target: Path) -> None:
    """Copy INCLUDE_FILES from root to target, respecting exclusions."""
    for relative in INCLUDE_FILES:
        source = root / relative
        if source.exists() and not should_exclude(Path(relative)):
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)


def copy_include_dirs(root: Path, target: Path) -> None:
    """Recursively copy INCLUDE_DIRS from root to target, respecting exclusions."""
    for relative_dir in INCLUDE_DIRS:
        source_dir = root / relative_dir
        if not source_dir.exists():
            continue
        for source in source_dir.rglob("*"):
            relative = source.relative_to(root)
            if should_exclude(relative):
                continue
            dest = target / relative
            if source.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
```

- [ ] **Step 2: Verify module imports correctly**

Run: `python -c "from scripts.ci._packaging_common import should_exclude, copy_include_files, copy_include_dirs; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add scripts/ci/__init__.py scripts/ci/_packaging_common.py
git commit -m "refactor(ci): extract shared packaging logic to scripts/ci/_packaging_common.py"
```

---

## Task 19: Create scripts/ci/build_installer_payload.py

**Files:**
- Create: `scripts/ci/build_installer_payload.py`
- Source: Inline Python in `ci.yml` lines 114-192 (Build standalone installer Exe artifact step)

- [ ] **Step 1: Create the build_installer_payload.py script**

Create `scripts/ci/build_installer_payload.py` that:
1. Imports `should_exclude`, `copy_include_files`, `copy_include_dirs`, `INCLUDE_DIRS` from `scripts.ci._packaging_common`
2. Implements the installer payload build logic currently inline in ci.yml
3. Uses `root = Path.cwd()` as the working directory
4. Creates `.installer-payload-stage/release_payload` directory
5. Copies include_files and include_dirs using shared functions
6. Copies `dist/SuperMedicine.exe` into payload
7. Runs PyInstaller to build `SuperMedicineInstaller.exe`
8. Runs dry-run validation

Key: The script must be runnable as `python scripts/ci/build_installer_payload.py` from the repo root.

- [ ] **Step 2: Verify script syntax**

Run: `python -c "import ast; ast.parse(open('scripts/ci/build_installer_payload.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add scripts/ci/build_installer_payload.py
git commit -m "refactor(ci): extract installer payload build to scripts/ci/build_installer_payload.py"
```

---

## Task 20: Create scripts/ci/build_release_zip.py

**Files:**
- Create: `scripts/ci/build_release_zip.py`
- Source: Inline Python in `ci.yml` lines 198-322 (Build release Zip step)

- [ ] **Step 1: Create the build_release_zip.py script**

Create `scripts/ci/build_release_zip.py` that:
1. Imports `should_exclude`, `copy_include_files`, `copy_include_dirs` from `scripts.ci._packaging_common`
2. Implements the release Zip build logic currently inline in ci.yml
3. Reads version from `pyproject.toml` using `tomllib`
4. Computes `release_label`, `release_title`, `archive_name`
5. Creates staging directory under `.release-zip-stage/`
6. Copies files, exe artifacts (SuperMedicine.exe, SuperMedicineInstaller.exe, SuperMedicineGUI.exe)
7. Creates Zip archive
8. Writes GitHub Actions output variables to `$GITHUB_OUTPUT` if available

Key: The script must be runnable as `python scripts/ci/build_release_zip.py` from the repo root.

- [ ] **Step 2: Verify script syntax**

Run: `python -c "import ast; ast.parse(open('scripts/ci/build_release_zip.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add scripts/ci/build_release_zip.py
git commit -m "refactor(ci): extract release Zip build to scripts/ci/build_release_zip.py"
```

---

## Task 21: Update ci.yml to Use Extracted Scripts

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Replace inline installer payload script**

Replace the `Build standalone installer Exe artifact` step (lines 109-192) with:

```yaml
      - name: Build standalone installer Exe artifact
        shell: bash
        run: |
          set -euo pipefail
          rm -rf .installer-payload-stage
          python scripts/ci/build_installer_payload.py
```

- [ ] **Step 2: Replace inline release Zip script**

Replace the `Build release Zip` step (lines 194-322) with:

```yaml
      - name: Build release Zip
        id: source_zip
        shell: bash
        run: |
          set -euo pipefail
          python scripts/ci/build_release_zip.py
```

- [ ] **Step 3: Verify CI yml is valid YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"`
Expected: OK

- [ ] **Step 4: Verify line count reduction**

Run: `wc -l .github/workflows/ci.yml`
Expected: ~200 lines (down from 446)

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "refactor(ci): replace inline Python scripts with scripts/ci/ modules"
```

---

## Task 22: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 2: Verify test file count**

Run: `ls tests/test_*.py | wc -l`
Expected: ~45 files (down from 77)

- [ ] **Step 3: Verify CI yml line count**

Run: `wc -l .github/workflows/ci.yml`
Expected: ~200 lines (down from 446)

- [ ] **Step 4: Verify no orphaned test files**

Run: `ls tests/test_*.py` and verify all files are either:
- Merged target files (test_installer.py, test_tui.py, etc.)
- Independent files that were never part of a merge group
- conftest.py

- [ ] **Step 5: Run repo hygiene tests**

Run: `python -m pytest tests/test_repo_hygiene.py -v --tb=short --override-ini addopts= -p no:cacheprovider`
Expected: All remaining tests pass

- [ ] **Step 6: Final commit if needed**

```bash
git add -A
git commit -m "refactor: complete test file and CI consolidation"
```

---

## Dependencies

```
Task 1 (conftest.py) ← No dependencies, do first
Task 2-16 (merge groups) ← Depend on Task 1 for shared helpers
Task 17 (repo_hygiene) ← Independent, can parallel with 2-16
Task 18 (_packaging_common.py) ← No dependencies
Task 19 (build_installer_payload.py) ← Depends on Task 18
Task 20 (build_release_zip.py) ← Depends on Task 18
Task 21 (ci.yml update) ← Depends on Tasks 19, 20
Task 22 (final verification) ← Depends on all previous tasks
```

## Verification Method

After each merge task (Tasks 2-16):
1. `python -m pytest tests/<merged_file>.py -v` — all tests pass
2. `python -m pytest tests/<merged_file>.py --co -q | wc -l` — test count matches original files combined
3. No import errors or missing references

After Task 17:
1. `python -m pytest tests/test_repo_hygiene.py -v` — remaining tests pass
2. Structural checks are gone, functional checks remain

After Tasks 18-21:
1. CI yml is valid YAML
2. Extracted scripts are syntactically valid
3. CI yml references the new script paths

After Task 22:
1. Full test suite passes
2. File count target met (~45 test files)
3. CI yml line count target met (~200 lines)
