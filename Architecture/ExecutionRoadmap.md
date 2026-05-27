# Execution Roadmap

This document records the current SuperMedicine architecture and the completed execution roadmap state requested by the user. The implementation roadmap is complete at Step 13/13 with final verification passed; Steps 1-13 are historical completion markers, not pending work.

## Current Architecture

```mermaid
flowchart LR
    subgraph cli["CLI and Install"]
        install["Install Package"]
        command["CLI Entry Points"]
    end

    subgraph kernel["Core Kernel"]
        core["Execution Kernel"]
        config["Configuration Loader"]
        lifecycle["Runtime Lifecycle"]
    end

    subgraph governance["Governance Layer"]
        permissions["Permission Engine"]
        registry["Plugin Registry"]
    end

    subgraph workspace["Workspace Experience and TUI"]
        workspaceManager["Workspace Manager"]
        paper["Workspace Paper Import"]
        experience["Experience Learning"]
        tui["Chinese TUI Workbench"]
    end

    subgraph extensions["Plugins Adapters and Agents"]
        rag["RAG Plugin"]
        harness["Harness Plugin"]
        writing["Medical Writing and Citation Plugin"]
        pystats["Python Stats Adapter"]
        rsurvival["R Survival Adapter"]
        agents["Agent Workflows"]
    end

    subgraph platform["Optional Platform Add-ons"]
        opencode["OpenCode Adapter Metadata and Tools"]
        claude["Minimal Claude Code CLI Adapter"]
    end

    subgraph quality["Tests and CI Hygiene"]
        tests["Test Coverage"]
        ci["CI Checks"]
        hygiene["Repository Hygiene"]
    end

    install --> command --> core
    core --> config
    core --> lifecycle
    core --> permissions
    core --> registry
    permissions --> rag
    permissions --> harness
    permissions --> writing
    registry --> rag
    registry --> harness
    registry --> writing
    registry --> pystats
    registry --> rsurvival
    registry --> agents
    core -. independent core does not require .-> opencode
    core -. independent core does not require .-> claude
    core --> workspaceManager
    permissions --> paper
    permissions --> experience
    workspaceManager --> paper
    workspaceManager --> experience
    workspaceManager --> tui
    tests -.-> cli
    tests -.-> kernel
    tests -.-> governance
    tests -.-> extensions
    ci -.-> cli
    ci -.-> kernel
    ci -.-> governance
    ci -.-> extensions
    hygiene -.-> cli
    hygiene -.-> kernel
    hygiene -.-> governance
    hygiene -.-> extensions
```

## Completed Roadmap Flow

```mermaid
flowchart TD
    completed1["Completed Step 1: Foundation reviewed"] --> completed2["Completed Step 2: CLI and install path handled"]
    completed2 --> completed3["Completed Step 3: Core kernel path handled"]
    completed3 --> completed4["Completed Step 4: Permission engine handled"]
    completed4 --> completed5["Completed Step 5: Plugin registry handled"]
    completed5 --> completed6["Completed Step 6: RAG and harness plugins handled"]
    completed6 --> completed7["Completed Step 7: Medical writing and citation handled"]
    completed7 --> completed8["Completed Step 8: Python stats and R survival adapters handled"]
    completed8 --> completed9["Completed Step 9: Tests and CI hygiene handled"]
    completed9 --> completed10["Completed Step 10: Workspace foundation handled"]
    completed10 --> completed11["Completed Step 11: Paper import path handled"]
    completed11 --> completed12["Completed Step 12: Experience learning handled"]
    completed12 --> completed13["Completed Step 13: Chinese TUI workbench handled"]
    completed13 --> verified["Final verification passed"]
    verified --> docs["Documentation saved"]
    docs --> hold["No commit or push unless explicitly requested"]
```

## Project Rule: Planning vs Push Gate

- Plan-stage work does not need strict project-standard verification.
- Optimization and standardization are required before Push/finalization, not during early planning.
- Before any Push, finalization, tag, release, publish, or upload, preserve the final verification requirement: run the project-approved quality gate, perform repository hygiene checks, and resolve required standardization/optimization issues.
- This rule relaxes Plan-phase overhead only; it does not relax the Push-before-finalization gate.

## Release Candidate State

- Release-ready label: `Beta0.3.0`.
- Python package metadata: `0.3.0b0` is the selected PEP 440 fallback because
  packaging validation rejects `Beta0.3.0` as `project.version`.
- R/rpy2 backend: formal support is represented through the optional `r` extra
  and the local `plugins.tools.r_survival` adapter path; it requires a local R
  installation with the R `survival` package available.
- OpencodeR: read-only reference only. No external OpencodeR data or source has
  been copied into this repository, and `D:\GIT\2025\OpencodeR` is not modified.
- CI release gate: Windows, macOS, and Linux must pass before release.
- Release gate checks: `ruff`, `pytest`, wheel/sdist smoke, and repository
  hygiene. The gate intentionally excludes mypy, pyright, and coverage
  fail-under requirements.
- Built artifacts are validation/local release candidates only. They are not
  committed, uploaded, or published.
- No tag, GitHub Release, publish action, PyPI upload, or TestPyPI upload has
  been performed.
- `Planning/NextSteps.md` remains local-only and ignored.
- Documentation model: SuperMedicine is an independent Python medical research
  agent framework. OpenCode and Claude Code are optional add-ons and are not
  prerequisites for core installation, initialization, or CLI/Kernel execution.
- OpenCode status: optional adapter surface with declared tools, plugin metadata,
  skills, and agent role documents; no standalone native OpenCode subagent
  runtime bridge is claimed without an injected SuperMedicine orchestrator.
- Claude Code status: minimal optional adapter for capabilities, runtime status,
  and permission-checked local `claude --print` invocation; no native Claude Code
  skill loading or native subagent dispatch is claimed.

## Remaining Actions

- Documentation is saved in Markdown files and reflects completed Step 13/13 status.
- No commit or push should be performed unless the user explicitly instructs it later.
- No tag, release, publish, or upload should be performed unless the user
  explicitly instructs it later.
- No additional roadmap implementation step is pending in the confirmed scope.
