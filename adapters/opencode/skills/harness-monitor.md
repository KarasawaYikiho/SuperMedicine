---
name: supermedicine-harness-monitor
description: Agent monitoring, quality assessment, and execution sandbox for medical research workflows
---

# Harness Monitor

Testing, evaluation, and monitoring framework for SuperMedicine agents. Harness
outputs are observability and quality-control aids for prototype/interface
workflows; they do not certify clinical, regulatory, or production readiness and
require human expert review before operational decisions.

## Capabilities

### Integration
- `harness.integration.checkpoint` — Checkpoint-based state verification
- `harness.integration.checkpoint_all` — Verify all checkpointed tasks in a directory

### Monitor
- `harness.monitor.permission_audit` — Audit permission usage and violations
- `harness.monitor.denied_actions` — List denied permission decisions
- `harness.monitor.performance` — Track agent performance metrics
- `harness.monitor.anomaly` — Detect anomalous agent behavior
- `harness.monitor.failure_patterns` — Detect repeated failure patterns

## Usage
```python
from plugins.harness.main import execute

result = execute(
    "harness.monitor.permission_audit",
    {"audit_log_path": ".supermedicine/audit.jsonl"},
)
entries = result["output"]["entries"]
```

## Trigger
Use when quality assurance, reproducibility verification, or agent behavior monitoring is needed.
