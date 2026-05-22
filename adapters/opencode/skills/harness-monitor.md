---
name: supermedicine-harness-monitor
description: Agent monitoring, quality assessment, and execution sandbox for medical research workflows
---

# Harness Monitor

Testing, evaluation, and monitoring framework for SuperMedicine agents.

## Capabilities

### Quality
- `harness.quality.code_check` — Verify generated analysis code correctness
- `harness.quality.text_score` — Score medical writing quality
- `harness.quality.citation_verify` — Verify citation accuracy and format

### Execution
- `harness.execution.sandbox` — Isolated execution environment for untrusted code
- `harness.execution.reproducibility` — Ensure analysis reproducibility

### Integration
- `harness.integration.e2e` — End-to-end workflow testing
- `harness.integration.checkpoint` — Checkpoint-based state verification
- `harness.integration.multi_agent` — Multi-agent collaboration monitoring

### Monitor
- `harness.monitor.permission_audit` — Audit permission usage and violations
- `harness.monitor.performance` — Track agent performance metrics
- `harness.monitor.behavior` — Monitor agent behavioral patterns
- `harness.monitor.anomaly` — Detect anomalous agent behavior

## Trigger
Use when quality assurance, reproducibility verification, or agent behavior monitoring is needed.
