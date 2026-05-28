# Security Policy

This policy records SuperMedicine's security, privacy, and medical-use
boundaries. Operational setup is covered in [INSTALL.md](INSTALL.md), and the
architecture-level permission model is described in [ARCHITECTURE.md](ARCHITECTURE.md#layer-2-permission-system-permission).

## Security Model

SuperMedicine uses a **runtime permission engine plus prompt-context guidance** (P0 priority) to manage security:

1. **Code Layer** (`permission/policy.py`) — Hard enforcement via fnmatch-based rules with deny-override-allow logic
2. **Prompt Context Layer** (`permission/prompt_generator.py`) — Advisory, context-aware soft constraints injected into agent context

Only the code-layer `PermissionEngine.check()` path performs runtime allow/deny decisions and writes audit records. The prompt context layer does **not** currently run inside `Kernel` as an additional runtime veto; it generates safety text and rejection templates for agent context.

## Permission Configuration

Policies are defined in YAML files under `.supermedicine/policies/`. Each policy specifies:

```yaml
- agent_id: "alpha"
  role: "analyst"
  security_level: "standard"
  permissions:
    allowed:
      - action: "read"
        scope: "*"
      - action: "execute"
        scope: "*"
    denied:
      - action: "write"
        scope: "*.yaml"
      - action: "publish"
        scope: "*"
    hard_limits:
      max_files_per_session: 100
      max_tool_calls_per_minute: 30
```

### Fields

| Field | Description |
|-------|-------------|
| `agent_id` | Unique agent identifier |
| `role` | Agent role (analyst, reviewer, writer, orchestrator) |
| `security_level` | Security tier (standard, elevated, admin) |
| `allowed` | Actions the agent is permitted to perform |
| `denied` | Explicitly forbidden actions (takes precedence over allowed) |
| `hard_limits` | Quantitative limits (rate limiting, resource caps) |

## Principle Of Least Privilege

Configure agents with the minimum permissions needed:

- **alpha** (analyst): read-only access to data and tools
- **beta** (reviewer): read access + write to code files only
- **gamma** (writer): read/write access to content files
- **delta** (orchestrator): full access (admin)

## Audit Logging

All permission checks are logged to `.supermedicine/policies/audit.jsonl` in JSONL format with UTC timestamps:

```json
{"agent_id": "alpha", "action": "read", "resource": "file.txt", "result": "ALLOWED", "reason": "whitelist_match", "timestamp": "2026-05-22T00:00:00Z"}
```

Use `plugins/harness/monitor.py` to analyze audit logs for anomalies.

## Workspace, Paper, And Experience Boundaries

- Workspace ids are slug-only identifiers and resolve to project-local
  `workspaces/<id>` paths. Workspace-scoped CLI commands require explicit
  `--workspace`; CLI execution must not silently reuse TUI recent workspace
  state.
- Workspace deletion is a hard delete and must pass exact `--confirm <id>`
  matching, destructive path validation, PermissionEngine authorization, and
  audit logging. Failed confirmation, missing policy, permission denial, and
  successful deletion are auditable events.
- Paper import is copy-only and workspace-local. It supports common local paper
  formats (`.pdf`, `.tex`, `.bib`, `.ris`, `.txt`, `.md`), calculates SHA-256,
  deduplicates by SHA-256 and normalized DOI/PMID, and keeps imported metadata
  editable without moving or uploading source files.
- Paper metadata enrichment is never silent network behavior. It requires user
  confirmation (`--confirm-enrich`), PermissionEngine approval, network and
  external API hard-limit checks, and audit logging before any provider fetch.
- Experience learning is enabled by default, but raw conversations are rejected.
  Only user-confirmed summaries/experience records may be stored. General method
  experiences are kept in an OS tempdir method layer and must not contain
  workspace/project details; workspace-specific experiences remain under the
  selected workspace and can be viewed, edited, deleted, or exported by the user.

## Safety, Privacy, And Medical-Use Boundaries

SuperMedicine is a research-assistance framework, not a clinical decision system.
Plugin outputs, RAG results, paper metadata, writing checklists, citation
formatting, and prototype statistics outputs require qualified expert review.
Do not use generated outputs as diagnosis, treatment, regulatory, or clinical
decision-support advice. Keep secrets in environment variables or local private
configuration, avoid committing private endpoints or audit logs with sensitive
paths, and treat all external network/API access as permission-gated behavior.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SM_CONFIG` | Override config file path |
| `SM_<KEY>` | Override any config key (uppercase, `_` for `-`) |
| `SM_LLM_PROVIDER` | Installer-time LLM provider override: `openai` or `anthropic` |
| `SM_LLM_BASE_URL` | Installer-time custom compatible provider BaseURL |
| `SM_LLM_API_KEY` | Installer-time generic API key injection; may be written to local config, so avoid committing it |
| `SM_LLM_MODEL` | Installer-time default model override |
| `OPENAI_API_KEY` | Runtime/installer key for OpenAI-compatible provider configuration |
| `ANTHROPIC_API_KEY` | Runtime/installer key for Anthropic-compatible provider configuration |
| `OPENROUTER_API_KEY` | Optional key for legacy OpenRouter provider integration |

## LLM Secret Handling

- Use environment variables or local private `.supermedicine/config.yaml` values
  for real API keys. Do not commit real OpenAI, Anthropic, OpenRouter, gateway, or
  platform credentials.
- Prefer storing `api_key_env` (for example `OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY`) in `.supermedicine/config.yaml` instead of storing an
  `api_key` value. The environment variable value should be set in a private
  shell, profile, secret manager, or CI secret store outside the repository.
- Documentation and tests must use non-realistic placeholders only, for example
  `<OPENAI_API_KEY>`, `<ANTHROPIC_API_KEY>`, or `<redacted>`.
- `Install.py --api-key` and `SM_LLM_API_KEY` can write the supplied key to local
  project config. Prefer `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for real keys
  when possible.
- `supermedicine llm add --api-key` has the same persistence and command-history
  risk as installer-time plaintext key injection. Prefer
  `supermedicine llm add --api-key-env <ENV_VAR_NAME>` for real credentials.
- `supermedicine llm list`, `supermedicine llm show`, capability reports, and
  error messages must use redacted output. Do not paste unredacted local YAML,
  terminal history, screenshots, audit logs, or traceback payloads into issues.
- Switching providers persists both the current runtime provider and
  `last_provider` for startup restore. Those fields are provider names, not
  secrets, but custom provider names or private BaseURLs may still reveal internal
  infrastructure; avoid committing private endpoint details.
- LLM provider config snapshots intended for logs or capability reporting must use
  redacted paths such as `get_llm_provider_config(redacted=True)` or provider
  `safe_dict()` output.
- OpenCode and Claude Code adapter manifests expose provider metadata only. They
  must not contain plaintext credentials, and missing optional platform runtimes
  degrade to unavailable/degraded states rather than bypassing the core security
  model.

## Reporting A Vulnerability

Please report security vulnerabilities by opening a GitHub Issue with the label `security`. Do not disclose vulnerabilities publicly until they have been addressed.

We aim to respond to security reports within 72 hours and provide a fix within 7 days for critical issues.
