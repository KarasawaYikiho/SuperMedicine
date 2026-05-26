# Workspace, TUI, Paper Import, and Experience Guide

This guide documents the user-facing workspace/TUI/RAG-adjacent workflows added
for the current phase. It is documentation only: no tag, release, publish,
package upload, paper upload, or external artifact upload is part of this work.

## Workspaces

SuperMedicine stores project workspaces under `workspaces/<id>`. The workspace
id is a slug: lowercase letters, digits, and hyphens only. It cannot contain path
separators, traversal segments, leading/trailing hyphens, or arbitrary Unicode.

```bash
supermedicine workspace init --workspace hypertension-review
supermedicine workspace list
supermedicine workspace show --workspace hypertension-review
```

Workspace initialization creates workspace-local directories for configuration,
sessions, checkpoints, local RAG data, papers, notes, and outputs. CLI commands
do not silently infer a workspace from the TUI. Use `--workspace <id>` whenever a
command operates on workspace-local state.

## CLI and Chinese TUI

`supermedicine tui` launches the Chinese terminal UI workbench. TUI recent
selection is saved as workspace/session state for the TUI experience only; it is
not a CLI default. CLI paths such as `run`, `paper`, and `experience` require or
accept an explicit `--workspace` argument so automation is reproducible.

```bash
supermedicine run "query local context" --workspace hypertension-review
supermedicine tui
```

## Hard Delete Semantics

Workspace deletion is destructive and irreversible from the CLI perspective:

```bash
supermedicine workspace delete --workspace hypertension-review --confirm hypertension-review
```

The confirmation value must exactly match the workspace id. The delete path must
stay inside the project root, pass destructive-path validation, receive
PermissionEngine approval for `workspace.delete`, and emit audit records. A
failed confirmation, missing policy, permission denial, or successful deletion is
recorded for review.

## Paper Import and Metadata

## Workspace-local Python/R Tools

Workspaces can carry reusable analysis tool folders without changing global
plugin/API semantics. The layout is explicit and workspace-local:

- `workspaces/<id>/tools/python/<tool-id>/...`
- `workspaces/<id>/tools/r/<tool-id>/...`

Tool ids use the same safe slug style as workspace ids. Supported languages are
`python` and `r`. Each tool folder contains a `tool.yaml` manifest with `id`,
`language`, `name`, `description`, `entrypoint`, `dependencies`, `inputs`,
`outputs`, and `version` fields.

```bash
supermedicine tool init --workspace hypertension-review
supermedicine tool add --workspace hypertension-review --language python --tool heatmap
supermedicine tool add --workspace hypertension-review --language r --tool umap
supermedicine tool list --workspace hypertension-review
supermedicine tool show --workspace hypertension-review --language python --tool heatmap
supermedicine tool run --workspace hypertension-review --language python --tool heatmap --dry-run --input data/matrix.csv --output outputs/heatmap.png
```

Built-in templates are available for Python heatmap, Python UMAP, R heatmap, and
R UMAP. They are scaffolds: heavyweight visualization dependencies such as
`matplotlib`, `seaborn`, `umap-learn`, `ggplot2`, `pheatmap`, and R `umap` remain
optional and are reported by the runner scripts with friendly messages instead
of becoming global SuperMedicine dependencies.

`tool run` currently prepares a guarded command foundation rather than executing
workspace scripts directly. Preparation validates the workspace, language, tool
slug, manifest, entrypoint, and optional input/output paths; paths must remain
inside the selected workspace/tool folder as appropriate. The operation is
checked through PermissionEngine using `tool.run` and audit events are written
for allowed or denied decisions. CLI tool commands require explicit
`--workspace` and do not read TUI recent selection.

## Paper Import and Metadata

Paper import is copy-only. SuperMedicine reads the local source file and copies
it into the selected workspace; it does not move the source, publish it, upload
it, or call the network during normal import.

Supported formats are common local research-paper formats:

- PDF (`.pdf`)
- TeX (`.tex`)
- BibTeX (`.bib`)
- RIS (`.ris`)
- text (`.txt`)
- Markdown (`.md`)

Imports compute SHA-256 for the stored original. Duplicate detection uses the
SHA-256 and, when supplied, normalized DOI and PMID metadata. Editable metadata
fields include title, authors, DOI, PMID, notes, and tags.

```bash
supermedicine paper import ./trial.pdf --workspace hypertension-review --doi 10.1000/example
supermedicine paper list --workspace hypertension-review
supermedicine paper edit <paper-id> --workspace hypertension-review --title "Updated title"
```

## Online Metadata Enrichment

Online or external paper metadata enrichment is opt-in only. It requires:

1. explicit user confirmation with `--confirm-enrich`,
2. PermissionEngine approval for the enrichment action,
3. network and external API hard-limit context checks, and
4. audit logging before and after the provider decision.

No paper import performs silent network access.

```bash
supermedicine paper enrich <paper-id> --workspace hypertension-review --confirm-enrich
```

## Experience Learning

Experience learning is enabled by default, but it stores only user-confirmed
summaries/experience records. Raw conversations, transcripts, or message logs
are rejected.

Two storage scopes are used:

- **general** — reusable method-level experience in an OS tempdir method layer;
  this scope must not include workspace ids, paper paths, paper ids, or other
  project-specific details.
- **workspace** — project-local details stored under the selected workspace.

Users can suggest a scope without writing, explicitly add confirmed records,
list/view records, edit/delete records, and export visible records as JSON or
Markdown.

```bash
supermedicine experience suggest --workspace hypertension-review --summary "Use concise extraction prompts"
supermedicine experience add --workspace hypertension-review --scope general --title "Prompt style" --summary "Use concise extraction prompts" --confirm
supermedicine experience list --workspace hypertension-review --include-general
supermedicine experience export --workspace hypertension-review --format md --include-general
```

## Safety, Privacy, and Medical Boundary

SuperMedicine is for medical research assistance, not clinical decision support.
RAG results, paper metadata, writing checklist output, citation formatting, and
prototype statistics outputs require qualified expert review. Do not treat any
output as diagnosis, treatment, regulatory approval, or clinical advice.

Security-sensitive behavior remains permission-gated. Keep secrets in
environment variables or local private configuration, avoid committing sensitive
audit logs or private endpoints, and review every external-resource permission
before enabling network/API access.
