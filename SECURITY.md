# Security Policy

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

## Principle of Least Privilege

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

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SM_CONFIG` | Override config file path |
| `SM_<KEY>` | Override any config key (uppercase, `_` for `-`) |
| `OPENROUTER_API_KEY` | API key for LLM integration |

## Reporting a Vulnerability

Please report security vulnerabilities by opening a GitHub Issue with the label `security`. Do not disclose vulnerabilities publicly until they have been addressed.

We aim to respond to security reports within 72 hours and provide a fix within 7 days for critical issues.
