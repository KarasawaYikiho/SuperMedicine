# SuperMedicine Examples

Practical examples for using SuperMedicine's CLI, TUI, Web API, and plugin system.

## CLI Usage Examples

### Project Setup

```bash
# Initialize a research project
supermedicine workspace init --workspace cardiac-study --name "Cardiac Study"

# Import papers
supermedicine paper import ./literature/review.pdf \
  --workspace cardiac-study \
  --title "Cardiac Biomarkers Review"

supermedicine paper import ./literature/trial.pdf \
  --workspace cardiac-study \
  --title "Phase III Trial Results"

# List imported papers
supermedicine paper list --workspace cardiac-study
```

### Experience Recording

```bash
# Record a research insight
supermedicine experience suggest \
  --workspace cardiac-study \
  --summary "Troponin I shows higher specificity than CK-MB for acute MI"

# Record methodology note
supermedicine experience suggest \
  --workspace cardiac-study \
  --scope methodology \
  --title "Sample Size Calculation" \
  --summary "Used G*Power for sample size, n=120 per group at 80% power"

# View experiences
supermedicine experience list --workspace cardiac-study
```

### Tool Management

```bash
# Scan for Python tools
supermedicine tool scan --language python

# Scan for R tools
supermedicine tool scan --language r

# Add a specific tool
supermedicine tool add --workspace cardiac-study --select 2

# List workspace tools
supermedicine tool list --workspace cardiac-study
```

### Experiment Workflow

```bash
# List available experiment protocols
supermedicine experiment list

# Start a Western Blot experiment
supermedicine experiment start \
  --protocol western_blot_basic \
  --session-id wb-cardiac-001

# Follow experiment progress
supermedicine log follow \
  --session-id wb-cardiac-001 \
  --interval 1 \
  --max-entries 20
```

### LLM Provider Management

```bash
# List configured providers
supermedicine llm list

# Add DeepSeek as a provider
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current

# Switch provider
supermedicine llm switch openai

# Show provider details
supermedicine llm show deepseek
```

### Diagnostics

```bash
# Full diagnostics check
supermedicine diagnose

# Check log location
supermedicine log location

# Follow session logs
supermedicine log follow --session-id wb-cardiac-001 --once
```

## TUI Usage Examples

### Starting the TUI

```bash
# Launch interactive TUI
supermedicine tui

# Check readiness without starting
supermedicine tui --dry-run
```

### Navigation Workflow

1. Launch TUI: `supermedicine tui`
2. Press `M` to open the main menu
3. Select a screen (Chat, Workspace, Paper, etc.)
4. Use `Tab`/`Shift+Tab` to navigate controls
5. Press `Enter` to submit/confirm
6. Press `P` to check permission mode
7. Press `Q` to quit

### Chat in TUI

The chat screen connects to the configured LLM provider. Type your message
in the input field and press `Enter` to send. The status bar shows
`Chat Processing` during active requests.

## Web API Examples

### Starting the Server

```bash
# Start web interface
supermedicine web

# Or programmatically
python -c "from core.web.server import start_server; start_server()"
```

### REST API with curl

```bash
# Check status
curl http://127.0.0.1:8000/api/v1/status

# Create a workspace
curl -X POST http://127.0.0.1:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"id": "api-test", "name": "API Test Workspace"}'

# List workspaces
curl http://127.0.0.1:8000/api/v1/workspaces

# Send a chat message
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the key cardiac biomarkers?"}'

# List LLM providers
curl http://127.0.0.1:8000/api/v1/llm/providers

# Check permissions
curl http://127.0.0.1:8000/api/v1/permissions
```

### WebSocket Chat

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://127.0.0.1:8000/ws/chat"
    async with websockets.connect(uri) as ws:
        # Send message
        await ws.send(json.dumps({"message": "Hello!"}))

        # Receive responses
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print(f"[{data['type']}]: {data.get('data', data.get('content', ''))}")
            if data['type'] in ('result', 'error'):
                break

asyncio.run(chat())
```

### Python Client

```python
import requests

base = "http://127.0.0.1:8000/api/v1"

# Create workspace
r = requests.post(f"{base}/workspaces", json={
    "id": "python-test",
    "name": "Python Test"
})
print(r.json())

# Import paper
r = requests.post(f"{base}/workspaces/python-test/papers", json={
    "source_path": "./paper.pdf",
    "metadata": {"title": "Test Paper"}
})
print(r.json())

# Chat
r = requests.post(f"{base}/chat", json={
    "message": "Summarize the imported papers"
})
print(r.json())
```

## Plugin Development Examples

### Basic Plugin Structure

```
plugins/
  my_analysis/
    plugin.yaml
    __init__.py
    analysis.py
```

### plugin.yaml

```yaml
name: my_analysis
version: "1.0"
description: "Custom analysis plugin"
author: "Researcher"
actions:
  - name: analyze_csv
    description: "Analyze CSV data files"
  - name: generate_report
    description: "Generate analysis report"
```

### Plugin Implementation

```python
# plugins/my_analysis/__init__.py
from plugins.base_plugin import BasePlugin, plugin_result
from pathlib import Path
import csv

class MyAnalysisPlugin(BasePlugin):
    """Custom analysis plugin for research data."""

    def execute(self, action: str, params: dict, context: dict = None) -> dict:
        if action == "analyze_csv":
            return self._analyze_csv(params)
        elif action == "generate_report":
            return self._generate_report(params)
        return plugin_result(
            status="error",
            plugin="my_analysis",
            action=action,
            error=f"Unknown action: {action}",
        )

    def _analyze_csv(self, params: dict) -> dict:
        file_path = params.get("file_path")
        if not file_path:
            return plugin_result(
                status="error",
                plugin="my_analysis",
                action="analyze_csv",
                error="file_path is required",
            )

        try:
            with open(file_path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            return plugin_result(
                status="success",
                plugin="my_analysis",
                action="analyze_csv",
                output={
                    "row_count": len(rows),
                    "columns": list(rows[0].keys()) if rows else [],
                    "sample": rows[:3] if rows else [],
                },
            )
        except Exception as e:
            return plugin_result(
                status="error",
                plugin="my_analysis",
                action="analyze_csv",
                error=str(e),
            )

    def _generate_report(self, params: dict) -> dict:
        # Implementation
        return plugin_result(
            status="success",
            plugin="my_analysis",
            action="generate_report",
            output={"report_path": "reports/analysis.md"},
        )
```

### Using the Plugin

```bash
# The plugin is auto-discovered from its plugin.yaml
supermedicine plugin list

# Execute via kernel (in Python)
from core.kernel import Kernel
kernel = Kernel()
result = kernel.plugin_registry.execute(
    "my_analysis",
    "analyze_csv",
    {"file_path": "data/experiment.csv"},
)
```

## Research Workflow Example

A complete workflow combining multiple features:

```bash
# 1. Setup
supermedicine workspace init --workspace meta-analysis --name "Meta-Analysis Study"

# 2. Import literature
supermedicine paper import ./papers/study1.pdf --workspace meta-analysis --title "Study 1"
supermedicine paper import ./papers/study2.pdf --workspace meta-analysis --title "Study 2"
supermedicine paper import ./papers/study3.pdf --workspace meta-analysis --title "Study 3"

# 3. Record methodology decisions
supermedicine experience suggest \
  --workspace meta-analysis \
  --scope methodology \
  --title "Inclusion Criteria" \
  --summary "RCTs only, n>50, published after 2015"

# 4. Add analysis tools
supermedicine tool scan --language python
supermedicine tool add --workspace meta-analysis --select 1

# 5. Run diagnostics
supermedicine diagnose

# 6. Start experiment
supermedicine experiment start --protocol statistical_analysis --session-id sa-meta-001

# 7. Follow progress
supermedicine log follow --session-id sa-meta-001 --interval 2
```
