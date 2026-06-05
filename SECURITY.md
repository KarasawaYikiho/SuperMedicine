# Security Policy

This policy summarizes SuperMedicine security, privacy, and medical-use
boundaries for **Beta0.4.1**. Operational setup is in [INSTALL.md](INSTALL.md),
and architecture boundaries are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Security Model

SuperMedicine uses a runtime permission engine plus advisory prompt-context
guidance:

1. **Code Layer** — `PermissionEngine.check()` performs runtime allow/deny
   decisions with deny-overrides-allow rules, hard-limit checks where supplied,
   and JSONL audit logging.
2. **Prompt Context Layer** — prompt helpers generate safety text and rejection
   templates for agent context. They are advisory and are not a Kernel runtime
   veto path.

Runtime permission checks are the enforcement boundary.

## Permission Configuration

Policies are YAML files under `.supermedicine/policies/`. Each policy can define
agent id, role, security level, allowed actions, denied actions, and hard limits:

```yaml
- agent_id: "alpha"
  role: "analyst"
  security_level: "standard"
  permissions:
    allowed:
      - action: "read"
        scope: "*"
    denied:
      - action: "publish"
        scope: "*"
    hard_limits:
      max_files_per_session: 100
      max_tool_calls_per_minute: 30
```

Configure agents with least privilege. Denied rules take precedence over allowed
rules.

## Audit Logging and Redaction

Permission decisions are logged to `.supermedicine/policies/audit.jsonl` with UTC
timestamps. Diagnostics and log/report surfaces redact known secret carriers such
as API keys, authorization headers, bearer tokens, key-like URL query values, and
secret-looking fields.

Shareable outputs may still include agent ids, actions, resource paths, provider
names, model names, BaseURLs, missing-field names, timestamps, and structured
error categories needed for repair.

Redaction is a safety layer, not permission to share raw logs. Before copying any
diagnostic output into an issue, README, changelog, function map, prompt, or
external ticket, remove private paths, project-specific patient/research data,
authorization values, API keys, tokens, session identifiers, and private gateway
URLs. Prefer summarized error categories over full traces.

On Windows, POSIX file mode bits are not treated as proof of owner-only ACL
protection. Windows permission checks are platform-capability-aware.

## LLM Secret Handling

- Use environment variables, private local config, secret managers, or CI secrets
  for real API keys.
- Prefer `api_key_env` in `.supermedicine/config.yaml` over plaintext `api_key`.
- Documentation, tests, manifests, and examples must use placeholders such as
  `<OPENAI_API_KEY>`, `<ANTHROPIC_API_KEY>`, `<OPENROUTER_API_KEY>`, or
  `<redacted>`.
- `Install.py --api-key`, `SM_LLM_API_KEY`, and `supermedicine llm add --api-key`
  can persist plaintext keys locally or expose them in shell history. Prefer
  provider-specific environment variables and `--api-key-env`.
- Do not paste unredacted local YAML, terminal history, screenshots, audit logs,
  tracebacks, or private endpoints into public issues.
- Optional OpenCode and Claude Code adapter files contain metadata only and must
  not contain plaintext credentials.

Relevant environment variables:

| Variable | Purpose |
|----------|---------|
| `SM_CONFIG` | Override config file path |
| `SM_<KEY>` | Override config keys using uppercase and `_` for `-` |
| `SM_LLM_PROVIDER` | Installer-time provider override |
| `SM_LLM_BASE_URL` | Installer-time custom BaseURL |
| `SM_LLM_API_KEY` | Installer-time generic key injection; may be written to local config |
| `SM_LLM_MODEL` | Installer-time model override |
| `OPENAI_API_KEY` | OpenAI-compatible provider key |
| `ANTHROPIC_API_KEY` | Anthropic-compatible provider key |
| `OPENROUTER_API_KEY` | OpenRouter provider key |

## Workspace, Paper, Experience, Experiment, and Log Boundaries

- Workspace ids are slug-only identifiers that resolve to project-local
  `workspaces/<id>` paths.
- Workspace-scoped CLI commands require explicit `--workspace`; they do not reuse
  TUI recent workspace state.
- Workspace deletion requires exact confirmation, path validation,
  PermissionEngine approval, and audit logging.
- Paper import is copy-only and workspace-local. Source files are not moved or
  uploaded by default.
- Paper enrichment requires explicit confirmation, permission approval,
  network/external API hard-limit checks, and audit logging before provider
  access.
- Experience learning stores only user-confirmed summaries and records, never raw
  conversations.
- Experiment guide and Log report surfaces write local JSON records under
  `.supermedicine/logs/` by default and use redaction for sensitive fields.
- The built-in `experiment-wb` actions perform deterministic arithmetic and input
  validation only. They do not perform network requests, call external APIs, or
  validate laboratory SOPs.

## Medical-Use Boundary

SuperMedicine is a research-assistance framework, not a clinical decision system.
Plugin outputs, RAG results, paper metadata, writing checklists, citation
formatting, and prototype statistics outputs require qualified expert review. Do
not use generated outputs as diagnosis, treatment, regulatory, or clinical
decision-support advice.

## Optional Platform Adapter Boundary

The standalone Python core is the default supported path. OpenCode and Claude
Code add-ons are optional. Missing platform runtimes should degrade to explicit
unavailable/degraded states rather than bypassing the core permission model.

External project references must stay source-clean and license-aware. Do not copy
third-party code, prompts, screenshots, logs, or configuration into this repository
unless the license and disclosure boundary have been reviewed. Optional adapter
documentation must not claim native OpenCode or Claude Code capabilities that are
not implemented and tested.

## Release Documentation Safety Checklist

Before publishing Markdown, verify that it:

- uses placeholders such as `<OPENAI_API_KEY>` rather than real credentials;
- avoids user-specific absolute paths except generic examples such as
  `C:\Users\<you>\...`;
- describes full-access mode as using only current OS/user privileges and never
  as silent privilege escalation;
- preserves medical-use limits and human-review requirements;
- links to visible/trackable release documents or clearly labels ignored local
  docs as non-release references;
- keeps function maps and audit inventories free of raw logs, private endpoints,
  and environment values.

## Reporting a Vulnerability

Open a GitHub Issue with the label `security`. Do not disclose vulnerabilities
publicly until they have been addressed. Maintainers aim to respond within 72
hours and to fix critical issues within 7 days.
