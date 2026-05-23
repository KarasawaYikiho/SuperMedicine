---
name: supermedicine
description: Modular medical research Agent framework with RAG, Harness, statistical analysis tools, medical writing standards (CONSORT/STROBE/PRISMA/STARD), and citation formatting (AMA/Vancouver). Multi-Agent orchestration with P0 dual-layer permission engine.
---

# SuperMedicine

Modular medical research Agent framework for automated evidence synthesis, statistical analysis, manuscript preparation, and compliance checking.

## When to Use

- Conducting systematic reviews or meta-analyses requiring literature search and evidence synthesis
- Performing statistical analysis on clinical trial or observational study data
- Drafting medical research manuscripts with proper reporting guideline compliance
- Checking manuscripts against CONSORT, STROBE, PRISMA, or STARD checklists
- Formatting citations in AMA or Vancouver style
- Running survival analysis (Kaplan-Meier, log-rank, Cox proportional hazards)
- Monitoring multi-agent research workflows with permission auditing

## Architecture

SuperMedicine uses a microkernel + multi-agent orchestration pattern:

- **Kernel** — Microkernel integrating ConfigCenter, EventBus, PluginRegistry, SessionManager, and P0 PermissionEngine
- **Permission Engine** — Dual-layer (code + prompt) constraints with one-vote veto mechanism and JSONL audit logging
- **Agent Orchestrator** — δ-Orchestrator coordinates α-Analyst (planning), β-Reviewer (verification), and γ-Writer (execution) through state-machine-driven workflows with checkpoint persistence
- **Plugin System** — 6 plugins: RAG retrieval, Harness monitoring, Python statistics, R survival analysis, medical writing standards, medical citation formatting

## Capabilities

### Literature Retrieval (RAG)
- TF-IDF based local search with Chinese/English tokenization
- Pluggable external API provider interface
- Context store/retrieve for multi-step research workflows

### Statistical Analysis
- **Python**: Descriptive statistics, Student's t-test, one-way ANOVA, linear regression
- **R**: Kaplan-Meier survival curves, log-rank test, Cox proportional hazards model

### Medical Writing Standards
- CONSORT 2010 (23 items) — Randomized controlled trials
- STROBE 2007 (22 items) — Observational studies
- PRISMA 2020 (27 items) — Systematic reviews and meta-analyses
- STARD 2015 (27 items) — Diagnostic accuracy studies

### Citation Formatting
- AMA style (superscript numeric)
- Vancouver style (bracketed numeric)

### Quality Assurance (Harness)
- Permission audit tracking
- Agent behavior monitoring
- Anomaly detection with configurable thresholds
- Code quality and reproducibility checks

## Sub-Agent Configuration

| Agent | Role | OpenCode Mapping |
|-------|------|-----------------|
| α-Analyst | Research analysis and planning | Brain → Planner |
| β-Reviewer | Quality review and compliance verification | Coder → Tester |
| γ-Writer | Manuscript composition and formatting | Coder |
| δ-Orchestrator | Workflow coordination and dispatch | Brain |

## Installation

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python Install.py --init
python Cli.py status
```

## Quick Start

```bash
# Check project status
python Cli.py status

# Run a research task
python Cli.py run "analyze clinical trial data with survival analysis"

# Run all tests
python Cli.py test
```

## Permissions

SuperMedicine enforces a P0 dual-layer permission system. All agent actions are checked against:
1. Code-layer policy rules (fnmatch-based deny-override-allow)
2. Prompt-layer constraint templates (injected into agent context)

Both layers must approve; any single denial blocks the action. All decisions are logged to JSONL audit files with UTC timestamps.

## License

MIT — see [LICENSE](https://github.com/KarasawaYikiho/SuperMedicine/blob/master/LICENSE)
