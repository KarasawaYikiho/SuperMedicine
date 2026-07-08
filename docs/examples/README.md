# Examples

These examples use placeholders and local paths. Do not paste real API keys,
patient identifiers, private endpoints, or unredacted logs into commands or
issues.

## Create a Workspace

```bash
supermedicine workspace init --workspace cardiac-study --name "Cardiac Study"
supermedicine workspace show --workspace cardiac-study
```

## Import Papers

```bash
supermedicine paper import ./literature/review.pdf \
  --workspace cardiac-study \
  --title "Cardiac Biomarkers Review"

supermedicine paper list --workspace cardiac-study
```

## Record a Confirmed Experience

```bash
supermedicine experience suggest \
  --workspace cardiac-study \
  --summary "Use short prompts and record inclusion criteria before extraction."

supermedicine experience add \
  --workspace cardiac-study \
  --scope workspace \
  --title "Extraction prompt note" \
  --summary "Use short prompts and record inclusion criteria before extraction." \
  --confirm
```

## Manage Tools

```bash
supermedicine tool scan --language python
supermedicine tool add --workspace cardiac-study --select 1
supermedicine tool list --workspace cardiac-study
```

## Configure a Provider

```bash
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current

supermedicine llm list
```

## Run an Experiment Flow

```bash
supermedicine experiment list
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
```

## Launch the TUI

```bash
npm ci
supermedicine tui --dry-run
supermedicine tui
```

## Start the Web Surface

```bash
python -m pip install -e ".[web]"
supermedicine web
```

Then open:

```text
http://127.0.0.1:8000
```
