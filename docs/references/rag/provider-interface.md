# RAG Provider Interface

This page describes the minimum RAG provider contract used by SuperMedicine.
Source files remain authoritative:

- `plugins/rag/interface.py`
- `plugins/rag/local_provider.py`
- `plugins/rag/pubmed_provider.py`

RAG output is research-support context. It is not clinical advice, regulatory
evidence, or a conclusion about evidence quality.

## Methods

Implement the `RAGProvider` interface:

```python
query(query: str, scope: str) -> dict
store_context(key: str, value: Any) -> None
retrieve_context(key: str) -> Any | None
```

Scopes should be explicit, for example:

- `literature`
- `knowledge_base`
- `project_context`

## Result Shape

Providers should return stable structured fields:

- `status`
- `provider`
- `items`
- `errors`
- metadata needed for diagnosis

Do not include API keys, private endpoints, raw request payloads, or unredacted
logs.

## Safety

- Local providers should label local resources.
- External providers should label external resources.
- Network/API access should use timeouts, redaction, and permission-aware call
  paths.
- Missing configuration and external failures should return structured errors.
