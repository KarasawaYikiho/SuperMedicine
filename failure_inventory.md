# CI Failure Inventory and Root-Cause Mapping

This file summarizes zip-log findings and maps each category to repository code
or CI configuration. It intentionally omits raw log dumps, credentials, private
endpoints, local user paths, and environment values.

## 1. Real CI failure: standalone installer PyInstaller payload path

- **Observed failure:** Source distribution smoke fails while building `SuperMedicineInstaller.exe` because PyInstaller reports it cannot find `.pyinstaller-installer-spec\.installer-payload-stage\release_payload` and exits with code 1.
- **Root cause:** The CI step stages the release payload at repository root `.installer-payload-stage/release_payload`, but the standalone installer PyInstaller invocation uses `--specpath .pyinstaller-installer-spec` together with a relative `--add-data ".installer-payload-stage/release_payload;release_payload"`. PyInstaller resolves that relative data source from the spec/work context as `.pyinstaller-installer-spec/.installer-payload-stage/release_payload`, where no payload was staged.
- **Primary target:** `.github/workflows/ci.yml` lines 100-174:
  - lines 104-110 remove/create root `.installer-payload-stage/release_payload`;
  - line 172 invokes PyInstaller with `--specpath .pyinstaller-installer-spec` and relative `--add-data` source;
  - line 174 separately proves the root-staged payload path is expected by `Install.py --release-payload-root .installer-payload-stage/release_payload`.
- **Runtime payload targets:**
  - `installer/entrypoint.py` lines 668-686 loads a bundled `release_payload` from PyInstaller `_MEIPASS` when available, or falls back to local `installer/exe_release.py`.
  - `installer/entrypoint.py` lines 737-755 routes `--extract-release-to` through `release_payload_to_directory`.
  - `installer/exe_release.py` lines 21 and 89-121 define `release_payload` and validate the unified payload root.
  - `installer/exe_release.py` lines 164-175 copy/extract the validated payload to the selected directory.
- **Regression-test target:** `tests/test_release_smoke.py` lines 255-274 checks that the workflow includes the standalone installer, `release_payload`, and smoke commands, but the current coverage does not catch this exact `--specpath` plus relative `--add-data` source-resolution mismatch.
- **Classification:** repo-fixable CI packaging path mismatch / missing staging at the resolved PyInstaller data-source path. No production code fix is included here.

## 2. Cache deserialization warnings

- **Observed warning:** macOS setup/dependency logs contain `WARNING: Cache entry deserialization failed, entry ignored`; some Python 3.10 setup-python lines are prefixed with `##[error]WARNING`.
- **Root cause:** Hosted runner/setup-python or pip cache metadata is stale/corrupt. The warning is emitted during environment setup or dependency cache handling, not while executing SuperMedicine application code.
- **Target files/lines:** `.github/workflows/ci.yml` lines 25-35 and 74-84 use `actions/setup-python@v5`, upgrade pip, purge pip cache, and install dependencies. These are workflow-maintenance touch points if mitigation is desired.
- **Classification:** environmental/workflow maintenance. Jobs continued except for the unrelated standalone installer PyInstaller failure.

## 3. Node.js 20 deprecation warnings

- **Observed warning:** GitHub Actions reports Node.js 20 actions are deprecated and explicitly names `actions/checkout@v4` and `actions/setup-python@v5`.
- **Root cause:** GitHub Actions JavaScript runtime deprecation for currently pinned action versions/runtime behavior.
- **Target files/lines:** `.github/workflows/ci.yml` lines 23, 72, and 327 use `actions/checkout@v4`; lines 26 and 75 use `actions/setup-python@v5`.
- **Classification:** workflow maintenance risk, not a repository application-code failure. Update action versions or workflow runtime flags when appropriate.

## 4. Checkout default-branch advisory hints

- **Observed warning/hint:** Checkout logs on non-Windows jobs include Git advisory text beginning with `hint: Using 'master'...` and ending with the suggestion to suppress `advice.defaultBranchName`.
- **Root cause:** Git initializes a temporary repository during checkout and emits its default-branch-name advisory. This is not caused by SuperMedicine source code.
- **Target files/lines:** `.github/workflows/ci.yml` checkout steps at lines 23, 72, and 327. Workflow triggers include both `master` and `main` at lines 4-7, but the advisory is from checkout-time Git initialization.
- **Classification:** environment/advisory. It may be suppressed through workflow Git config if desired, but it is not the CI failure.

## 5. Negative findings from explicit marker rescan

- **No tracebacks:** no `Traceback (most recent call last)` markers were found.
- **No missing modules:** no `ModuleNotFoundError` markers were found.
- **No pytest failures:** no standalone pytest `FAILED` markers were found; occurrences were passing test names/statuses rather than failure markers.
- **No additional non-zero exits:** no additional `Process completed with exit code [1-9]` entries were found beyond the standalone installer PyInstaller failure.
- **No additional errors:** no additional actionable `ERROR` entries were found beyond PyInstaller failing to locate `release_payload`.
- **Classification:** no extra repository code targets are indicated by the logs beyond the mapped CI packaging issue above.
