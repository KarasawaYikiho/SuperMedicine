# Getting Started

This guide is the short path from a clean checkout to a usable local
SuperMedicine workspace. For installer details, see [INSTALL.md](INSTALL.md).

## 1. Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
npm ci
python install.py
```

Check the install:

```bash
supermedicine status
supermedicine diagnose
```

## 2. Configure an LLM Provider

Prefer environment variables for keys:

```bash
set OPENAI_API_KEY=<OPENAI_API_KEY>
```

Add or switch providers with the CLI:

```bash
supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current

supermedicine llm list
```

## 3. Create a Workspace

```bash
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine workspace list
supermedicine workspace show --workspace demo
```

Workspace commands use explicit ids. SuperMedicine does not silently reuse a
recent TUI workspace for CLI operations.

## 4. Import a Paper

```bash
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine paper list --workspace demo
```

Paper import is copy-only. External enrichment requires explicit confirmation
where implemented.

## 5. Record Experience

```bash
supermedicine experience suggest --workspace demo --summary "Keep prompts short"
supermedicine experience add \
  --workspace demo \
  --scope workspace \
  --title "Prompt note" \
  --summary "Keep prompts short" \
  --confirm
```

Experience records store confirmed summaries, not raw conversations.

## 6. Use Tools

```bash
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
supermedicine tool list --workspace demo
```

Tools are imported into the workspace before use.

## 7. Run the TUI

```bash
supermedicine tui --dry-run
supermedicine tui
```

The interactive TUI requires Bun and the locked npm dependency installed by
`npm ci`.

## Common Checks

```bash
supermedicine permission status
supermedicine log location
supermedicine experiment list
```

## Next Reading

- [Installation guide](INSTALL.md)
- [Architecture guide](architecture.md)
- [API reference](../api/README.md)
- [Examples](../examples/README.md)
