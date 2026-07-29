# RAG Provider Interface

This reference summarizes the maintained RAG provider boundary. The following
source files are authoritative:

- `plugins/rag/providers.py`
- `plugins/rag/pubmed_provider.py`
- `core/services/rag.py`

RAG output is research-support context. It is not clinical advice, regulatory
evidence, or a conclusion about evidence quality.

## Provider Operations

Provider implementations extend `RAGProvider` and expose the applicable
operations:

```python
connect() -> dict[str, Any]
query(query_text: str, top_k: int = 5) -> dict[str, Any]
store_context(key: str, data: Any) -> None
retrieve_context(key: str) -> Any | None
```

Callers should provide an explicit storage directory or workspace context.
The application service classifies tasks before retrieval and records whether
RAG was required, used, or skipped.

- `knowledge_generation`
- `deterministic_plugin`
- `control`

## Result Shape

Providers return structured mappings with the fields required by the action,
including:

- `status`
- `provider`
- `items`
- `errors` when the operation cannot complete
- diagnostic metadata that does not expose secrets

Do not include API keys, private endpoints, raw request payloads, or unredacted
logs.

## Safety

- Local providers should label local resources.
- External providers should label external resources.
- Network/API access should use timeouts, redaction, and permission-aware call
  paths.
- Missing configuration and external failures must return structured errors.
