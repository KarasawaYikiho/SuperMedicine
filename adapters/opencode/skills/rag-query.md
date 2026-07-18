---
name: supermedicine-rag-query
description: RAG-based medical literature retrieval and context management for evidence-based research
---

# RAG Query

Retrieval-Augmented Generation interface for medical literature search. Current
SuperMedicine RAG output is an interface/prototype retrieval aid only; retrieved
context requires human expert review before research, regulatory, or clinical use.

This optional OpenCode-facing summary keeps provider and safety context local;
the detailed provider contract remains in the plugin reference and code.

OpenCode AI provider metadata is supplied by installer flags, `SM_LLM_*`
environment variables, provider key environment variables, or `.supermedicine/config.yaml`.
The add-on declares OpenAI-compatible, Anthropic-compatible, and OpenRouter
gateway formats, supports custom compatible BaseURL values, redacts secrets as
`<redacted>`, and degrades without an injected orchestrator/runtime bridge. Do not
include plaintext API keys, private endpoints, or raw logs in skill docs.

## Capabilities
- `rag.query` — Search medical literature databases with natural language queries
- `rag.context.store` — Store retrieved documents as context for downstream analysis
- `rag.context.retrieve` — Retrieve stored context by query or document ID

## Provider
The default provider uses TF-IDF based local search (`plugins/rag/local_provider.py`).
Use the executable plugin entrypoint for stable skill examples. Do not instantiate
the abstract `RAGProvider` interface directly.

External-vector examples use the deterministic `MockExternalVectorStoreProvider`
contract backend unless a real provider is explicitly implemented and configured.

## Trigger
Use when the task requires searching medical literature, retrieving evidence,
or managing research context for systematic reviews, meta-analyses, or evidence synthesis.

## Usage
```python
from plugins.rag.main import execute

result = execute(
    "rag.query",
    {
        "query": "efficacy of metformin in type 2 diabetes",
        "provider": "local",
        "documents": [
            {
                "id": "doc-1",
                "title": "Metformin overview",
                "text": "metformin type 2 diabetes glycemic control",
            }
        ],
        "top_k": 1,
    },
)
items = result["output"]["items"]
```

External-vector contract backend example:

```python
from plugins.rag.providers import RAGProviderConfig
from plugins.rag.providers import MockExternalVectorStoreProvider

provider = MockExternalVectorStoreProvider(
    RAGProviderConfig(
        provider_type="external_vector",
        endpoint="mock://vector-store",
        index_name="medical-literature",
        api_key_env="SM_RAG_API_KEY",
    ),
    records=[{"id": "doc-1", "text": "hypertension diabetes cardiovascular risk"}],
)
results = provider.query("hypertension cardiovascular", top_k=1)
```
