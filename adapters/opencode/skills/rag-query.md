---
name: supermedicine-rag-query
description: RAG-based medical literature retrieval and context management for evidence-based research
---

# RAG Query

Retrieval-Augmented Generation interface for medical literature search.

## Capabilities
- `rag.query` — Search medical literature databases with natural language queries
- `rag.context.store` — Store retrieved documents as context for downstream analysis
- `rag.context.retrieve` — Retrieve stored context by query or document ID

## Provider
The default provider uses TF-IDF based local search (`plugins/rag/local_provider.py`).
To use an external API, configure the provider in `plugins/rag/plugin.yaml`.

## Trigger
Use when the task requires searching medical literature, retrieving evidence,
or managing research context for systematic reviews, meta-analyses, or evidence synthesis.

## Usage
```python
from plugins.rag.interface import RAGProvider
provider = RAGProvider()
results = provider.query("efficacy of metformin in type 2 diabetes")
```
