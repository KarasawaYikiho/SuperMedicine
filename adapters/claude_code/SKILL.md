---
name: supermedicine
description: SuperMedicine is the single user-facing Claude Code skill/agent surface for the modular medical research assistant framework with RAG, Harness, statistical analysis tools, medical writing standards (CONSORT/STROBE/PRISMA/STARD), citation formatting (AMA/Vancouver), internal role-context orchestration, and P0 dual-layer permission engine.
---

# SuperMedicine Claude Code Optional Adapter Skill

This file describes the minimal optional Claude Code add-on for SuperMedicine.
It is not required for the standalone SuperMedicine core runtime. The adapter can
report capabilities, probe a local Claude Code CLI, and invoke `claude --print`
through SuperMedicine's canonical permission chain when the local runtime is
available. If no local `claude` command exists, the adapter reports a structured
optional-adapter-unavailable state rather than a core runtime failure.

SuperMedicine itself remains a modular medical research assistant framework for
prototype/interface-only evidence synthesis, statistical analysis, manuscript
preparation, and compliance checking. SuperMedicine does not provide clinical advice,
production-grade statistics, or regulatory/clinical certification; all outputs
require human expert review.

Use this skill document for Claude Code-facing capability context only. General
installation details remain in the repository [README](../../README.md) and
[INSTALL](../../INSTALL.md) documents; the adapter limitations below are kept
local so this optional skill remains self-contained.

## Installation Manifest Entry

`install.json` registers this optional Claude Code surface as:

- platform key: `claude-code`
- entry file: `adapters/claude_code/SKILL.md`
- adapter module: `adapters/claude_code/adapter.py`
- optional add-on: yes
- core runtime required: no
- user-facing Agent/surface: exactly one, `SuperMedicine`
- internal role contexts: `alpha`, `beta`, `gamma`, and `delta` as
  non-user-facing workflow context only
- AI provider formats: OpenAI-compatible and Anthropic-compatible
- provider configuration source: installer/runtime/project configuration only,
  including `Install.py --provider openai|anthropic --base-url <url>
  --api-key <placeholder-or-secret> --model <model>`, `SM_LLM_*` variables,
  `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, and `.supermedicine/config.yaml`
- secret handling: API keys must be redacted from logs, manifests, adapter
  responses, and documentation; this skill document intentionally contains no
  real plaintext API key examples

## When To Use

- Conducting systematic reviews or meta-analyses requiring literature search and evidence synthesis
- Performing statistical analysis on clinical trial or observational study data
- Drafting medical research manuscripts with proper reporting guideline compliance
- Checking manuscripts against CONSORT, STROBE, PRISMA, or STARD checklists
- Formatting citations in AMA or Vancouver style
- Running survival analysis (Kaplan-Meier, log-rank, Cox proportional hazards)
- Monitoring multi-role research workflows with permission auditing

## Architecture

SuperMedicine uses a microkernel + internal role-context orchestration pattern.
For Claude Code and similar platforms, the only user-facing Agent/surface is
`SuperMedicine`; α-Analyst, β-Reviewer, γ-Writer, and δ-Orchestrator are
non-user-facing workflow role contexts/capabilities, not separate platform Agents.

- **Kernel** — Microkernel integrating ConfigCenter, EventBus, PluginRegistry, SessionManager, and P0 PermissionEngine
- **Permission Engine** — Dual-layer (code + prompt) constraints with one-vote veto mechanism and JSONL audit logging
- **Role Orchestrator** — δ-Orchestrator coordinates α-Analyst (analysis and planning), β-Reviewer (quality verification), and γ-Writer (manuscript execution) through state-machine-driven workflows with checkpoint persistence
- **Plugin System** — 6 plugins: RAG retrieval, Harness monitoring, Python statistics, R survival analysis, medical writing standards, medical citation formatting

## Capabilities

### Claude Code Optional Adapter Boundary
- Registration/discovery metadata for `ClaudeCodeAdapter`
- Capability reporting via `claude.capabilities`
- Runtime probing via `claude.runtime_status`
- Permission-checked local CLI invocation via `claude.invoke`
- Timeout, runtime-unavailable, runtime-error, invalid-input, permission-denied,
  and unsupported-tool structured responses
- Secret redaction for prompt/runtime data before returning adapter responses
- Single user-facing Agent/surface declaration: `SuperMedicine`
- Internal role contexts are represented as capabilities/role context only
- Supported adapter tool IDs are limited to `claude.capabilities`,
  `claude.runtime_status`, and `claude.invoke`
- `claude.invoke` requires the local `claude` command and a successful
  SuperMedicine PermissionEngine decision before subprocess execution
- OpenAI/Anthropic provider configuration discovery through the same
  installer-injected SuperMedicine configuration model used by other optional
  platform surfaces
- Custom provider BaseURL metadata for OpenAI-compatible and
  Anthropic-compatible endpoints, with secret redaction required

### AI Provider Configuration Boundary

Claude Code remains an optional platform surface around the standalone
SuperMedicine core. When a Claude Code invocation path needs LLM provider
metadata, it must use configuration supplied during SuperMedicine installation
or runtime setup rather than embedding credentials in adapter files. Supported
sources are:

- `Install.py --provider openai|anthropic --base-url <url> --api-key <placeholder-or-secret>
  --model <model>`
- `SM_LLM_PROVIDER`, `SM_LLM_BASE_URL`, `SM_LLM_API_KEY`, and `SM_LLM_MODEL`
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `.supermedicine/config.yaml` entries under `llm.provider` and
  `llm.providers.*`

Supported API formats are OpenAI-compatible and Anthropic-compatible. Custom
BaseURL values are allowed for compatible endpoints. Adapter capability/status
metadata may report that these formats and configuration sources are supported,
but it must not echo plaintext API keys.

Example placeholders, not real credentials:

```bash
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --api-key <OPENAI_API_KEY_PLACEHOLDER> \
  --model gpt-4o-mini
```

### Explicit Limitations
- No native Claude Code subagent dispatch is implemented.
- No native Claude Code skill loading is implemented.
- No α-Analyst, β-Reviewer, γ-Writer, or δ-Orchestrator platform Agent is declared.
- The local Claude Code CLI is optional and only required for `claude.invoke`.
- Missing `claude` on PATH is an adapter-unavailable state, not a SuperMedicine core failure.
- OpenAI/Anthropic provider configuration support does not make Claude Code a
  required platform dependency for SuperMedicine core runtime.
- Core CLI/API/plugin/action IDs and permission semantics are not changed by this
  add-on.

### Literature Retrieval (RAG)
- TF-IDF based local search with Chinese/English tokenization
- Pluggable external API provider interface
- Context store/retrieve for multi-step research workflows

### Statistical Analysis
- **Python**: Descriptive statistics, Student's t-test, one-way ANOVA, linear regression
- **R**: Kaplan-Meier survival curves, log-rank test, Cox proportional hazards model

### Medical Writing Standards
- CONSORT 2010 (25 items) — Randomized controlled trials
- STROBE 2007 (22 items) — Observational studies
- PRISMA 2020 (27 items) — Systematic reviews and meta-analyses
- STARD 2015 (27 items) — Diagnostic accuracy studies

### Citation Formatting
- AMA style (superscript numeric)
- Vancouver style (bracketed numeric)

### Quality Assurance (Harness)
- Permission audit tracking
- Role behavior monitoring
- Anomaly detection with configurable thresholds
- Code quality and reproducibility checks

## Internal SuperMedicine Role Contexts

The roles below are SuperMedicine workflow concepts only. They do not represent
implemented native Claude Code subagents in this adapter and are explicitly not
user-facing platform Agents. The only user-facing Agent/surface is
`SuperMedicine`.

| Internal Role Context | Position | Platform Agent Status |
|-------|------|-----------------------|
| α-Analyst | Research analysis and planning | Non-user-facing role context; not a Claude Code Agent |
| β-Reviewer | Quality review and compliance verification | Non-user-facing role context; not a Claude Code Agent |
| γ-Writer | Manuscript composition and formatting | Non-user-facing role context; not a Claude Code Agent |
| δ-Orchestrator | Workflow coordination and dispatch | Non-user-facing role context; not a Claude Code Agent |

## Installation

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python Install.py --init
python Cli.py status
```

For Anthropic-compatible configuration, use `--provider anthropic` with
`ANTHROPIC_API_KEY` or a fake placeholder such as
`<ANTHROPIC_API_KEY_PLACEHOLDER>` in examples. Never commit real keys.

## Quick Start

```bash
# Check project status
python Cli.py status

# Run a research task
python Cli.py run "analyze clinical trial data with survival analysis"

# Run all tests
python Cli.py test
```

## Stable Python API Examples

RAG queries should use a concrete provider or the executable plugin entrypoint,
not the abstract `RAGProvider` interface:

```python
from plugins.rag.main import execute

result = execute("rag.query", {"query": "hypertension diabetes", "provider": "local"})
items = result["output"]["items"]
```

Citation formatting should pass structured source metadata or construct a shared
`JournalArticle`/`Book` model:

```python
from plugins.standards.medical_citation.ama_format import AMAFormatter, JournalArticle

citation = AMAFormatter().format_journal(JournalArticle(
    authors=["John Smith"],
    title="Cardiovascular Risk Factors",
    journal="JAMA",
    year=2024,
    volume="331",
))
```

## Permissions

SuperMedicine enforces a P0 dual-layer permission system. All role actions are checked against:
1. Code-layer policy rules (fnmatch-based deny-override-allow)
2. Prompt-layer constraint templates (injected into SuperMedicine execution context)

Both layers must approve; any single denial blocks the action. All decisions are logged to JSONL audit files with UTC timestamps.

## License

MIT — see [LICENSE](https://github.com/KarasawaYikiho/SuperMedicine/blob/master/LICENSE)
