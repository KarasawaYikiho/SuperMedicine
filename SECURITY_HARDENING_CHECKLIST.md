# SuperMedicine Security Hardening Checklist

This release-scope checklist summarizes documentation and runtime safety themes
for **Beta0.4.2**. It does not add product features; it records the boundaries that
Markdown, examples, adapters, logs, and release packaging must preserve.

## Scope

- Standalone Python CLI/Kernel/TUI operation remains the default supported path.
- OpenCode and Claude Code content are optional adapters, not core requirements.
- Medical, RAG, citation, checklist, and statistics outputs are research-support
  aids only and require qualified human review.
- `docs/` is ignored by repository rules, so release-critical Markdown must be
  visible at the root or intentionally force-tracked.

## Secret and Log Filtering

- Use environment variables, private local config, secret managers, or CI secrets
  for real API keys.
- Use placeholders in committed examples: `<OPENAI_API_KEY>`,
  `<ANTHROPIC_API_KEY>`, `<OPENROUTER_API_KEY>`, `<redacted>`.
- Do not paste raw `.supermedicine/policies/audit.jsonl`, diagnostics, tracebacks,
  shell history, screenshots, or private provider endpoints into Markdown.
- Log/report surfaces should redact authorization headers, bearer tokens,
  key-like URL query values, API-key fields, secret-looking values, and common
  credential carriers before display or persistence.
- Regression coverage should prove sensitive values from structured fields,
  exception/error logs, URL queries, request headers, and persisted log reports
  never appear in rendered or stored log output while ordinary business fields
  remain visible.

## Permission and Full-Access Mode Wording

- Describe `conservative` as the default mode.
- Describe `full` as a high-risk mode that only uses current process/current user
  OS permissions; it does not silently elevate, bypass UAC, or override operating
  system ACLs.
- Keep destructive actions exact-confirmation guarded and audit-logged.
- Keep high-risk adapter tools permission-gated and project-root sandboxed.

## Function Map Hygiene

- Keep `FUNCTION_MAP.md` visible and do not delete it.
- Treat it as static AST analysis, not a complete runtime trace.
- Do not add configuration values, environment values, API keys, tokens, raw logs,
  or private endpoints to the callable inventory.

## External Project Boundary

- External projects may inspire UX or adapter design only after license and safety
  review.
- Do not copy external source, prompts, logs, screenshots, or configuration into
  this repository unless the license and disclosure boundary are approved.
- Do not claim native OpenCode or Claude Code capabilities until the repository
  implements and verifies them.
- External-method experience records must remain user-confirmed summaries only:
  general ideas may enter the shared method layer, while project details stay in
  workspace-local storage and raw conversation/source material is not persisted.

## Markdown Release Review

Before publishing or uploading Markdown, confirm that:

1. links point to visible release files or clearly label ignored local docs;
2. examples use placeholders and temporary paths;
3. medical-use limits are present;
4. optional adapters are not described as core dependencies;
5. no obsolete version, local username, private path, or unsupported feature claim
   remains.
6. root-visible Markdown and adapter documentation contain no realistic plaintext
   example API keys, bearer tokens, cloud access keys, or quoted secret values.

## Final Safety Review Status

The following items capture the final handoff state for this hardening pass. The
verification retry reported that tests/scans passed; the remaining readiness gap
was stale checklist wording and untracked artifacts awaiting the Brain-managed
commit workflow.

| Item | Status | Notes |
| --- | --- | --- |
| Real secrets committed | Completed / evidence-backed | Markdown guidance requires placeholders only. Verification reported that scans passed with no real secret blocker. No real API key, bearer token, cloud key, raw audit log, private endpoint, or local credential should be committed. |
| External project source copied into repository | Completed / no known issue | `EXTERNAL_PROJECT_ANALYSIS.md` records that external projects are inspiration only. Source, prompts, screenshots, logs, and configuration from external projects must not be copied without separate license and disclosure review. |
| Original features and concepts preserved | Completed / no known issue | This hardening pass records documentation, security, adapter, and release boundaries only. Standalone CLI/Kernel/TUI and medical research-support concepts remain the supported baseline. |
| User-requested commands/checklist items | Completed or explicitly bounded | Security/log filtering, full-access wording, function-map hygiene, Markdown release review, and external-project boundary items are captured in this checklist. Runtime test execution and final verification are intentionally delegated to the verification role. |
| Markdown processing | Completed / no known issue | Root-visible Markdown safety requirements are documented here. Release-critical Markdown should remain root-visible or intentionally force-tracked because `docs/` is ignored. |
| Function relationship documentation | Completed | `FUNCTION_MAP.md` is the generated/static callable inventory and documents AST limitations, dynamic-dispatch caveats, and secret-exclusion rules. |
| External project analysis and fusion notes | Completed | `EXTERNAL_PROJECT_ANALYSIS.md` documents allowed inspiration, disallowed copying, adapter boundary limits, and the three-question rule for future external-reference notes. |
| Network/external-project access failures | Not applicable in this pass | No live external-project fetch is required to preserve the current boundary. If a future review requires network access and it fails, record the failed URL/tool output, impacted comparison items, and a local/static-analysis fallback before claiming completion. |
| Tests and regression verification | Completed / evidence-backed | Verification reported tests/regression checks passed and no functionality-change blocker remains. |
| Sensitive-information scan | Completed / evidence-backed | Verification reported sensitive-information scans passed with no true-positive real secret finding blocking commit readiness. |
| Repository ready to commit | Completed / awaiting Brain commit workflow | Verification reported the only readiness issue was untracked intended artifacts and stale pending wording. Intended files are `SECURITY_HARDENING_CHECKLIST.md`, `EXTERNAL_PROJECT_ANALYSIS.md`, `FUNCTION_MAP.md`, and `tests/test_redaction.py`; staging/commit remains intentionally deferred to Brain workflow. |

## Final Release Gate

The repository is release-checklist ready based on the verification result that:

1. the full approved test/regression suite passes;
2. the sensitive-information scan has no true-positive real secret findings;
3. Markdown review finds no unsupported capability claims or private data;
4. `FUNCTION_MAP.md` and `EXTERNAL_PROJECT_ANALYSIS.md` remain present and
   aligned with the boundaries above;
5. any blocked external/network review item has failure evidence, impact, and an
   approved fallback documented.
