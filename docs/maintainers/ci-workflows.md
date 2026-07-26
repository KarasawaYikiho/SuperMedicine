# CI Workflows

## Required checks

Branch protection should depend on the stable `CI / Required Gate` and
`OpenTUI / Required Gate` summaries. Internal matrices may evolve without
changing those public check names.

## Workflow ownership

| Workflow | Responsibility |
|---|---|
| `ci.yml` | Docs, static analysis, Python versions, platform smoke, Wheel smoke |
| `opentui.yml` | Real Bun/OpenTUI runtime smoke on Linux and Windows |
| `package-smoke.yml` | Non-publishing Windows source, executable, and archive smoke |
| `release.yml` | Tag validation, immutable artifact verification, draft publication |
| `nightly.yml` | Full 3-OS by Python 3.10-3.13 compatibility matrix |

Reusable workflows contain setup, test, and build orchestration only. Release
validation and publication logic belongs in `scripts/ci/`.

## Security and cost controls

All workflows default to `contents: read`, set explicit timeouts, and use
concurrency cancellation for replaceable PR runs. The publication job alone
receives write permission. Clean-install smoke uses an isolated target while
normal dependency installs may use lockfile-backed caches.

Path-conditional required workflows must still start and return an explicit
successful no-op when their expensive work is irrelevant.
