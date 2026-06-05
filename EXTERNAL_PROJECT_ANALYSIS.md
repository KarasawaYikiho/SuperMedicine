# External Project Reference and Fusion Notes

This document records how SuperMedicine may learn from external projects without
copying source code, leaking sensitive information, or overstating implemented
capabilities.

## Current Boundary

- SuperMedicine is an independent Python medical research assistance framework.
- OpenCode and Claude Code are optional platform add-ons under `adapters/`.
- The standalone CLI, Kernel, plugin registry, permission engine, workspaces, TUI,
  RAG, tools, and standards plugins do not require external assistant runtimes.

## Allowed Use of External References

External projects can be used as references for:

- interaction patterns, such as compact TUI status cues and discoverable menus;
- terminology audits, when names are adapted to SuperMedicine concepts;
- adapter boundary design, when the resulting behavior is implemented and tested
  inside this repository;
- release-hygiene practices, such as separating generated artifacts from source.

## Disallowed Use Without Separate Review

- Copying third-party source code, prompts, screenshots, logs, or configuration.
- Importing external runtime assumptions into the standalone core.
- Publishing private paths, local usernames, API endpoints, keys, or raw logs.
- Claiming native platform dispatch, native skill loading, or production-grade
  clinical/statistical behavior before implementation and verification.

## OpenCode-Style Experience Fusion

The current TUI and CLI documentation may reference OpenCode-style experience
principles only as design inspiration: immediate feedback, visible task state,
clear focus, concise status cues, and actionable errors. No OpenCode runtime,
source tree, or user configuration is required for these SuperMedicine behaviors.

## Documentation Rule

Every external-reference note must answer three questions:

1. What idea is being referenced?
2. What SuperMedicine file or behavior actually implements it?
3. What is explicitly not claimed or not copied?

## Final Review Status

- No external project source tree, prompt set, screenshot, runtime log, or local
  configuration is intentionally incorporated into this repository by this review.
- The current fusion method is limited to user-confirmed, high-level experience
  principles: immediate feedback, visible task state, clear focus, concise status
  cues, and actionable errors.
- Live network access to external projects is not required for this boundary
  document. If future comparison work depends on network access and the project is
  unavailable, record the attempted URL/tool output, what analysis could not be
  completed, and the fallback source of evidence before using the result.
- License and safety review remains mandatory before any third-party code,
  configuration, media, or prompt text can be copied into SuperMedicine.
