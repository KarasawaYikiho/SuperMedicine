# Project Debug and Repair Record

This document records the repository-wide debug pass performed on 2026-07-28.
It separates confirmed product defects from environment-specific observations
and defines the evidence required before the repair may be pushed.

## Baseline

The zero-change baseline was run from the repository root on `master` at
`cfa835a` with a unique nonexistent `SM_CONFIG` and a pre-created temporary
pytest base directory.

| Gate | Result |
| --- | --- |
| Full Python suite | 1197 passed, 4 skipped |
| Ruff | passed |
| mypy | passed for 145 source files |
| Documentation and repository policy | 5 passed |
| OpenTUI smoke and interaction suite | 26 passed |
| Python bytecode compilation | passed |
| Installed dependency consistency | passed |

The four skips are environment-bound: one case-insensitive filesystem spelling
case and three Windows symlink cases that require privileges unavailable to the
current process. They are not suppressed regressions.

## Confirmed Defects

### DBG-001: clean-process Kernel import fails

Severity: high.

A new Python process running `from core.kernel import Kernel` fails with a
partially initialized module error. `core.kernel.runtime` imports
`core.services.rag`, loading the `core.services` package initializer; that
initializer eagerly imports `ExperimentToolService`, whose module imports
`core.kernel` again.

The aggregate suite missed the defect because its collection order loads other
service modules before the public Kernel import is exercised.

Repair:

- move the `Kernel` dependency in the experiment service to the operation that
  needs it;
- add a clean-subprocess import contract so test collection order cannot mask
  the cycle.

Acceptance:

```powershell
python -c "from core.kernel import Kernel; print(Kernel.__name__)"
```

must exit successfully in a new process.

### DBG-002: `SM_CONFIG` leaks into logical configuration values

Severity: medium.

`SM_CONFIG` is a control variable for the default Kernel configuration path,
but `ConfigCenter.get("config")` and `ConfigCenter.all()` also treated it as a
logical setting named `config`. Secret-safe diagnostics therefore reported a
synthetic setting that was never present in YAML and could be mistaken for
application configuration.

Repair:

- establish one resolver for the environment-selected config path with a
  project-local fallback;
- use it for default Kernel construction while preserving explicitly injected
  configuration paths;
- keep `SM_CONFIG` visible as diagnostic metadata, but exclude it from logical
  configuration values.

Acceptance:

- `SM_CONFIG` does not appear as a synthetic `config` setting;
- explicitly supplied `ConfigCenter(path)` instances remain deterministic.

### Rejected hypothesis: explicit project configuration is not an override bug

The first runtime probe suggested that `status`, `diagnose`, application
services, and Web/TUI should all replace their explicit project configuration
with `SM_CONFIG`. Implementing that interpretation caused seven full-suite
failures and three focused failures by collapsing explicitly isolated projects
onto one shared file.

Current source contracts and behavioral tests establish the intended
precedence: an explicitly injected project or configuration path wins;
`SM_CONFIG` only selects the path when Kernel construction has no explicit
path. The broader change was withdrawn. This is recorded here so the same
environmental symptom is not fixed again by weakening explicit path isolation.

### DBG-003: release metadata uses deprecated license fields

Severity: medium.

The sdist and Wheel build succeeded but warned that the legacy
`project.license` table and `License ::` classifier are deprecated. Current
Python packaging metadata uses an SPDX license expression and declares the
license file directly; setuptools added this support in 77.0.3.

Repair:

- require `setuptools>=77.0.3` for the build backend;
- declare `license = "MIT"` and `license-files = ["LICENSE"]`;
- remove the deprecated license classifier and the redundant standalone
  `wheel` build requirement so setuptools uses its integrated wheel command.

Acceptance:

- Wheel and sdist build without license metadata deprecation warnings;
- both artifacts contain the MIT license file and preserve the project version.

## Environment Observations

### Windows native-output decoding

The source and documentation are valid UTF-8. The initial PowerShell capture
decoded Python's GBK native output as UTF-8 and displayed mojibake. Repeating
the command with `PYTHONUTF8=1` produced correct Chinese text, so no source
rewrite is justified.

### Optional filesystem coverage

The three symlink security tests require Windows Developer Mode or an elevated
token. Their Linux CI coverage remains relevant; this local run records them as
an explicit limitation rather than a pass.

## Final Validation

The repaired tree passed the following gates before commit:

| Gate | Final result |
| --- | --- |
| Clean-process Kernel import and default config path | passed |
| Affected Python contracts | 304 passed, 2 skipped |
| Full Python suite | 1200 passed, 4 skipped |
| Ruff | passed |
| mypy | passed for 145 source files |
| Documentation, repository, release, feature, and runtime contracts | 24 passed |
| OpenTUI smoke, navigation, and interaction suite | 26 passed |
| Wheel and sdist build | passed without license or wheel deprecation warnings |
| Clean Wheel smoke | 15 plugin manifests discovered |
| Python installed dependency consistency | passed |
| npm high-severity audit | 0 vulnerabilities |
| `git diff --check` | passed |

The remaining four pytest skips are the environment-bound cases documented
above. Remote CI is not treated as complete until the pushed commit finishes
its hosted workflows.
