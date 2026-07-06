# Maintenance Backlog

This backlog is ordered for low-risk human maintainability work. It favors small,
reviewable changes over broad rewrites.

## Phase 1: Stabilize Maintainer Orientation

- Keep this `docs/maintainers/` guide current.
- Add status labels to archive docs: current reference, generated inventory,
  historical plan, or stale note.
- Fix broken Markdown links in user-facing docs.
- Move intentional mojibake regression markers out of main onboarding text or
  isolate them in a clearly named compatibility appendix.

## Phase 2: Clarify Entrypoints

- Decide whether legacy names such as `Cli.py`, `Install.py`, `install.py`, and
  `Uninstall.py` are supported release shims or stale docs.
- Prefer `supermedicine ...` in new docs.
- Add or preserve tests for every supported compatibility entrypoint.

## Phase 3: Strengthen Gates Without Broad Refactors

- Install `.[dev,web]` in the Web-specific CI gate.
- Run `npm run opentui:smoke` after `npm ci` where Bun is available.
- Build packaging artifacts into temp locations and install them in a fresh
  environment before release claims.
- Keep generated build and test output outside the repository checkout when
  tooling allows.

## Phase 4: Reduce Large-File Review Cost

- Keep focused test files for TUI screens, Web routes, workspace tools, and
  medical writing standards.
- Extract only behavior-covered slices from `core/tui/app.py`,
  `core/web/server.py`, and `core/web/frontend/app.js`.
- Treat `setup.py` custom behavior as release code with narrow regression tests
  before changing it.

## Phase 5: Clarify UI And API Boundaries

- Pick one source of truth for TUI route inventory.
- Separate Web service semantics from CLI convenience wrappers where destructive
  operations or confirmations are involved.
- Keep permission checks in runtime code paths, not only in UI copy or prompts.

