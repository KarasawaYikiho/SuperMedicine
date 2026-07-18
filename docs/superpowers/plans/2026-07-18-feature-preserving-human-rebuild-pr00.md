# PR-00 Feature-Preserving Human Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a machine-readable Feature ID baseline and contract suite that prevents existing SuperMedicine product surfaces from being removed during later rebuild phases.

**Architecture:** A test-only AST/YAML inventory discovers declared product surfaces without importing runtime services. `feature_manifest.json` is the reviewed baseline; contract tests compare current discovery to the manifest and execute critical runtime contracts. A hygiene fixture captures structural metrics and the non-linear audit-reference relationship.

**Tech Stack:** Python 3.10+, pytest, stdlib `ast`/`json`/`pathlib`, PyYAML, FastAPI test client, existing package metadata.

## Global Constraints

- Do not modify or delete production behaviour in PR-00.
- Do not import optional external runtimes while collecting static inventory.
- Every Feature ID has a category, entrypoint, expected result, and primary contract-test node.
- RAG and Harness are `required` and `default_enabled`.
- Alpha, Beta, Gamma, and Delta are `preserved`; multi-agent execution is `optional_enabled` with both modes tested.
- A Feature ID count may never decrease; unclassified discovered entries fail.
- Use `D:\GIT\CodexTem\SuperMedicine` for test caches and temporary output.

---

## File Structure

- Create: `feature_manifest.json` — reviewed product-surface baseline.
- Create: `tests/feature_contract/__init__.py`, `conftest.py`, `inventory.py` — test-only inventory package.
- Create: `tests/feature_contract/test_manifest_contract.py` — integrity and static-parity tests.
- Create: `tests/feature_contract/test_runtime_contract.py` — required-default and optional-mode contracts.
- Modify: `tests/test_repo_hygiene.py` — no Feature ID regression gate.
- Create: `docs/maintainers/feature-parity.md`; modify `docs/maintainers/README.md`.

### Task 1: Create the manifest contract

**Files:**
- Create: `tests/feature_contract/__init__.py`
- Create: `tests/feature_contract/conftest.py`
- Create: `tests/feature_contract/test_manifest_contract.py`
- Create: `feature_manifest.json`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> dict[str, object]`.
- Consumes: repository-root `Path` and JSON manifest.

- [ ] **Step 1: Write the failing test**

```python
def test_manifest_has_unique_ids_and_required_contract_fields(manifest):
    records = manifest["features"]
    assert records
    ids = [record["feature_id"] for record in records]
    assert len(ids) == len(set(ids))
    for record in records:
        assert {"feature_id", "category", "entrypoint", "expected_result", "contract_test"} <= set(record)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/feature_contract/test_manifest_contract.py::test_manifest_has_unique_ids_and_required_contract_fields -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-red-1`

Expected: FAIL because `feature_manifest.json` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a JSON object with `schema_version`, `implementation_baseline`, `audit_reference`, `baseline_relationship`, `metrics`, and `features`. Add records for canonical CLI entrypoints, RAG, Harness, Alpha/Beta/Gamma/Delta, adapters, installer entrypoints, and every plugin `provides` ID. Add the required enabled-policy flags.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/feature_contract/test_manifest_contract.py::test_manifest_has_unique_ids_and_required_contract_fields -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-green-1`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add feature_manifest.json tests/feature_contract
git commit -m "test: add feature manifest contract baseline"
```

### Task 2: Add static discovery and complete parity

**Files:**
- Create: `tests/feature_contract/inventory.py`
- Modify: `tests/feature_contract/test_manifest_contract.py`
- Modify: `feature_manifest.json`

**Interfaces:**
- Produces: `discover_cli_commands(root: Path) -> set[str]`, `discover_web_routes(root: Path) -> set[str]`, `discover_plugin_provides(root: Path) -> set[str]`, `discover_adapter_names(root: Path) -> set[str]`, and `discovered_surface(root: Path) -> dict[str, set[str]]`.
- Consumes: AST source and tracked YAML/JSON declarations only.

- [ ] **Step 1: Write the failing test**

```python
def test_each_discovered_entry_has_a_manifest_feature(repository_root, manifest):
    discovered = discovered_surface(repository_root)
    manifest_entries = {record["entrypoint"] for record in manifest["features"]}
    missing = sorted({entry for entries in discovered.values() for entry in entries} - manifest_entries)
    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/feature_contract/test_manifest_contract.py::test_each_discovered_entry_has_a_manifest_feature -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-red-2`

Expected: FAIL because no discovery implementation exists.

- [ ] **Step 3: Write minimal implementation**

Parse `cli/parser.py` for `add_parser`, `core/web/server.py` for decorated HTTP/websocket routes, plugin/tool YAML for `provides[].id`, adapters for registration platform names, and package/installer entrypoints. Normalize records as `surface:value`, sort them, then add one manifest record per normalized entry.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/feature_contract/test_manifest_contract.py -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-green-2`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add feature_manifest.json tests/feature_contract
git commit -m "test: inventory preserved product surfaces"
```

### Task 3: Protect required defaults and optional multi-agent modes

**Files:**
- Create: `tests/feature_contract/test_runtime_contract.py`
- Modify: `feature_manifest.json`

**Interfaces:**
- Consumes: `Kernel`, `PluginRegistry`, `Orchestrator`, role agents, and isolated temporary project roots.
- Produces: assertions that RAG/Harness are discovered/executable and that disabled/enabled orchestration preserves four role identities.

- [ ] **Step 1: Write the failing test**

```python
def test_manifest_marks_rag_and_harness_required_and_default_enabled(manifest):
    records = {record["feature_id"]: record for record in manifest["features"]}
    assert records["plugin:rag-interface"]["required"] is True
    assert records["plugin:harness-core"]["default_enabled"] is True

def test_manifest_preserves_all_multi_agent_roles(manifest):
    roles = {record["entrypoint"] for record in manifest["features"] if record["category"] == "multi_agent_role"}
    assert roles == {"agent:alpha", "agent:beta", "agent:gamma", "agent:delta"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/feature_contract/test_runtime_contract.py -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-red-3`

Expected: FAIL because records and runtime contracts are absent.

- [ ] **Step 3: Write minimal implementation**

Add required records, then reuse public APIs to verify local RAG query, Harness checkpoint discovery, and orchestrator registration/dispatch for all roles. Parameterize a configuration fixture for `multi_agent.enabled=False` and `True`; assert documented lightweight and complete-flow outcomes.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/feature_contract/test_runtime_contract.py -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-green-3`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add feature_manifest.json tests/feature_contract/test_runtime_contract.py
git commit -m "test: protect required and optional capability modes"
```

### Task 4: Record structural metrics and enforce no-regression

**Files:**
- Modify: `tests/feature_contract/inventory.py`
- Modify: `tests/test_repo_hygiene.py`
- Modify: `feature_manifest.json`

**Interfaces:**
- Produces: `collect_metrics(root: Path) -> dict[str, int]` and manifest `metrics`.
- Consumes: production Python files only; excludes tests, generated output, and external worktrees.

- [ ] **Step 1: Write the failing test**

```python
def test_feature_manifest_count_never_regresses(repository_root):
    manifest = load_manifest(repository_root / "feature_manifest.json")
    assert len(manifest["features"]) >= manifest["metrics"]["feature_id_count"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_repo_hygiene.py::test_feature_manifest_count_never_regresses -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-red-4`

Expected: FAIL because the hygiene gate and metrics baseline are absent.

- [ ] **Step 3: Write minimal implementation**

Use `ast.walk` to count functions/methods and public top-level symbols, count production files and physical/nonblank/noncomment lines, identify >60 and >100 line functions from AST positions, and record static top-level import edges. Save metrics in the manifest. Validate the count and every declared contract-test node.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_repo_hygiene.py::test_feature_manifest_count_never_regresses tests/feature_contract -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-green-4`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add feature_manifest.json tests/feature_contract/inventory.py tests/test_repo_hygiene.py
git commit -m "test: enforce feature parity hygiene gate"
```

### Task 5: Document regeneration and validate the gate

**Files:**
- Create: `docs/maintainers/feature-parity.md`
- Modify: `docs/maintainers/README.md`

**Interfaces:**
- Produces: maintainer procedure and required PR report inputs.

- [ ] **Step 1: Write the failing documentation-link test**

```python
def test_maintainer_docs_link_to_feature_parity_guide():
    content = Path("docs/maintainers/README.md").read_text(encoding="utf-8")
    assert "feature-parity.md" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_maintainer_markdown_links.py -q --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-red-5`

Expected: FAIL until the guide and link are present.

- [ ] **Step 3: Write minimal implementation**

Document baseline relationship, schema, inventory coverage and limitations, regeneration command, review requirements, and the mandatory PR report format. Link it from the maintainer README.

- [ ] **Step 4: Run focused and full validation**

```powershell
python -m pytest tests/feature_contract tests/test_repo_hygiene.py tests/test_maintainer_markdown_links.py -q --override-ini addopts= -p no:cacheprovider --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-focused
python -m pytest -q --override-ini addopts= -p no:cacheprovider --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-pr00-full
python -m mypy core permission cli plugins agents adapters installer --cache-dir D:\GIT\CodexTem\SuperMedicine\mypy-pr00
python -m ruff check .
python -m build --outdir D:\GIT\CodexTem\SuperMedicine\build-pr00
npm run opentui:smoke
```

Expected: each command exits 0; unavailable platform-specific checks are reported as unverified, never silently skipped.

- [ ] **Step 5: Commit**

```powershell
git add docs/maintainers/feature-parity.md docs/maintainers/README.md
git commit -m "docs: document feature parity maintenance"
```

