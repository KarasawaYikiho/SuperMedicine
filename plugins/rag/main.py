"""Executable entrypoint for the rag-interface manifest plugin."""
from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from typing import Any

from plugins.base_plugin import plugin_result
from plugins.rag.interface import RAGProviderConfig
from plugins.rag.local_provider import LocalRAGProvider, MockExternalVectorStoreProvider
from plugins.rag.pubmed_provider import PubmedRAGProvider


PLUGIN_NAME = "rag-interface"

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "rag.query": {
        "required_params": {"query": "str"},
        "optional_params": {"top_k": "int", "provider": "local|mock_external|pubmed", "documents": "list[dict|str]"},
        "output_fields": ["items", "results", "relevance_scores", "source_metadata", "errors", "metadata"],
    },
    "rag.context.store": {
        "required_params": {"key": "str", "data": "any"},
        "output_fields": ["key", "stored"],
    },
    "rag.context.retrieve": {
        "required_params": {"key": "str"},
        "output_fields": ["key", "data", "found"],
    },
}

DEFAULT_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "rag-default-1",
        "title": "Hypertension and diabetes risk",
        "source": "rag-interface-default-local-index",
        "text": "hypertension diabetes cardiovascular risk prevention",
        "metadata": {"fixture": True, "topic": "cardiovascular"},
    },
    {
        "id": "rag-default-2",
        "title": "Oncology immunotherapy overview",
        "source": "rag-interface-default-local-index",
        "text": "oncology cancer immunotherapy checkpoint treatment",
        "metadata": {"fixture": True, "topic": "oncology"},
    },
]


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute supported RAG actions using the existing provider contract."""
    params = params or {}
    context = context or {}
    metadata = _base_metadata(context)

    try:
        if action == "rag.query":
            output = _execute_query(params)
        elif action == "rag.context.store":
            output = _execute_context_store(params)
        elif action == "rag.context.retrieve":
            output = _execute_context_retrieve(params)
        else:
            return plugin_result(
                status="plugin_error",
                plugin=PLUGIN_NAME,
                action=action,
                error=f"Unsupported rag-interface action: {action}",
                metadata=metadata,
            )
    except (TypeError, ValueError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Invalid rag-interface input: {exc}",
            metadata=metadata,
        )

    if isinstance(output, dict) and output.get("status") in {"error", "denied"}:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            output=output,
            error=_first_error_message(output) or "RAG provider returned an error status.",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin=PLUGIN_NAME,
        action=action,
        output=output,
        metadata=metadata,
    )


def _execute_query(params: dict[str, Any]) -> dict[str, Any]:
    query = _required_str(params, "query")
    top_k = _top_k(params.get("top_k", 5))
    provider_name = str(params.get("provider") or params.get("provider_type") or "local").lower()

    if provider_name in {"local", "local-tfidf"}:
        provider = LocalRAGProvider(_storage_dir(params))
        documents = params.get("documents", DEFAULT_DOCUMENTS)
        _seed_local_documents(provider, documents)
        return provider.query(query, top_k=top_k, scope=str(params.get("scope", "literature")))

    if provider_name in {"mock", "mock_external", "mock-external-vector-store", "external_vector"}:
        config = _provider_config(params)
        records = _records_from_params(params)
        provider = MockExternalVectorStoreProvider(config, records=records)
        return provider.query(query, top_k=top_k)

    if provider_name == "pubmed":
        provider = PubmedRAGProvider(timeout_seconds=float(params.get("timeout_seconds", 10.0)))
        return provider.query(query, top_k=top_k)

    raise ValueError(f"provider must be one of local, mock_external, or pubmed; got {provider_name!r}")


def _execute_context_store(params: dict[str, Any]) -> dict[str, Any]:
    key = _required_str(params, "key")
    if "data" not in params:
        raise ValueError("data is required")
    provider = LocalRAGProvider(_storage_dir(params))
    provider.store_context(key, params["data"])
    return {"key": key, "stored": True, "provider": provider.provider_name}


def _execute_context_retrieve(params: dict[str, Any]) -> dict[str, Any]:
    key = _required_str(params, "key")
    provider = LocalRAGProvider(_storage_dir(params))
    data = provider.retrieve_context(key)
    return {"key": key, "data": data, "found": data is not None, "provider": provider.provider_name}


def _base_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource": {"kind": "rag", "plugin": PLUGIN_NAME},
        "security": {"permission_entrypoint": "kernel", "permission_checked": bool(context)},
        "contract": {"actions": ACTION_CONTRACTS, "provider_contract": "RAGProvider"},
        "audit": {"context_keys": sorted(context.keys())},
    }


def _storage_dir(params: dict[str, Any]) -> Path:
    storage_dir = params.get("storage_dir")
    if storage_dir is None:
        return Path(gettempdir()) / "supermedicine-rag-interface"
    if not isinstance(storage_dir, (str, Path)):
        raise ValueError("storage_dir must be a path string")
    return Path(storage_dir)


def _seed_local_documents(provider: LocalRAGProvider, documents: Any) -> None:
    if documents is None:
        return
    if not isinstance(documents, list):
        raise ValueError("documents must be a list")
    for document in documents:
        if isinstance(document, str):
            provider.add_document(document, {})
            continue
        if not isinstance(document, dict):
            raise ValueError("documents entries must be strings or dictionaries")
        text = document.get("text") or document.get("snippet")
        if not isinstance(text, str) or not text:
            raise ValueError("document text must be a non-empty string")
        metadata = {key: value for key, value in document.items() if key not in {"text", "snippet"}}
        provider.add_document(text, metadata)


def _provider_config(params: dict[str, Any]) -> RAGProviderConfig:
    return RAGProviderConfig(
        provider_type="external_vector",
        endpoint=str(params.get("endpoint") or "mock://vector-store"),
        index_name=str(params.get("index_name") or "rag-interface-default"),
        namespace=params.get("namespace"),
        api_key_env=params.get("api_key_env"),
        timeout_seconds=float(params.get("timeout_seconds", 10.0)),
        metadata=params.get("provider_metadata") if isinstance(params.get("provider_metadata"), dict) else {},
    )


def _records_from_params(params: dict[str, Any]) -> list[dict[str, Any]]:
    records = params.get("records", params.get("documents", DEFAULT_DOCUMENTS))
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    normalized: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record, str):
            normalized.append({"text": record})
        elif isinstance(record, dict):
            normalized.append(record)
        else:
            raise ValueError("records entries must be strings or dictionaries")
    return normalized


def _required_str(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _top_k(value: Any) -> int:
    top_k = int(value)
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    return top_k


def _first_error_message(output: dict[str, Any]) -> str | None:
    errors = output.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("message") or first.get("code") or "")
    return None
