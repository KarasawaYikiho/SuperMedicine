# Maintenance Backlog

This backlog is deliberately small. Prefer narrow cleanups over broad rewrites.

## Near Term

- Keep root README files aligned after release or command changes.
- Keep `docs/archive/` empty and ignored; use `Temp/` for local historical notes.
- Move remaining encoding-regression markers out of onboarding prose when tests
  can protect them in a dedicated fixture.
- Keep docs link checks passing for tracked `docs/`.

## Medium Term

- Split large TUI, Web, and installer tests only when behavior is already covered.
- Keep Web routes from weakening CLI confirmation or permission semantics.
- Keep one source of truth for TUI route metadata.
- Add focused tests before changing custom packaging behavior in `setup.py`.

## Long Term

- Review optional adapter claims whenever OpenCode or Claude Code integration
  behavior changes.
- Revisit generated function inventory only when it can be regenerated cleanly
  into ignored `Temp/` output.
