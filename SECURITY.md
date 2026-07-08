# Security Policy

SuperMedicine is local-first research-support software. It is not a clinical
decision system, a regulated medical device, or a replacement for qualified human
review.

This policy applies to **Beta0.4.2**.

## Supported Boundary

The supported default path is the standalone Python runtime: CLI, Kernel,
permission engine, plugins, workspaces, installer, and TUI launcher. OpenCode and
Claude Code files under `adapters/` are optional integration surfaces and must
not be treated as proof of native platform runtime support unless code and tests
show that support.

## Permission Model

Runtime enforcement lives in `permission/` and uses `PermissionEngine.check()`.
Prompt text can explain policy, but prompt text is not the enforcement boundary.

Permission decisions can be audited to:

```text
.supermedicine/policies/audit.jsonl
```

The tracked default policy is:

```text
.supermedicine/policies/default.yaml
```

Denied rules take precedence over allowed rules. Full access only relaxes
SuperMedicine's own checks after explicit confirmation; it does not elevate OS
privileges, bypass UAC, bypass ACLs, or grant administrator rights.

## Secrets

Use environment variables, private local config, secret managers, or CI secrets
for real credentials.

Preferred key sources:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`
- custom variables referenced through `api_key_env`

Do not put real keys in:

- Markdown files
- tests
- manifests
- screenshots
- issue comments
- command history examples
- `.supermedicine/config.yaml` snippets shared publicly
- audit logs or raw diagnostic output

Shared examples must use placeholders such as `<OPENAI_API_KEY>` or
`<redacted>`.

## Data and Workspace Boundaries

- Workspace ids resolve to project-local `workspaces/<id>` paths.
- Workspace commands require explicit `--workspace`.
- Paper import is copy-only and does not upload source files by default.
- Paper enrichment and external metadata lookups require explicit confirmation
  where implemented.
- Experience learning stores confirmed summaries and structured records, not raw
  conversations.
- Logs and reports are local runtime artifacts and should be redacted before
  sharing.
- Self-evolution is preview-first and writes files only after explicit
  confirmation and path/permission checks.

## Medical-Use Boundary

Outputs from RAG, LLM calls, citation helpers, medical writing checklists,
statistics prototypes, experiment helpers, and figure tools require qualified
human review. Do not use them as diagnosis, treatment, regulatory, or clinical
decision-support advice.

## Documentation Safety

Before publishing docs, check that they:

- use placeholders rather than real credentials;
- avoid private absolute paths;
- describe full-access mode as current-user permission only;
- describe self-evolution as preview-first and confirmation-gated;
- do not claim clinical validation;
- do not claim native OpenCode or Claude Code runtime features unless tested;
- do not link to ignored local archives as release evidence.

## Reporting

Open a GitHub issue for security concerns and label it `security`. Include a
minimal reproduction and affected version. Do not include real secrets, patient
data, private endpoints, or unredacted logs.

Maintainers aim to acknowledge reports within 72 hours and prioritize critical
fixes within 7 days.
