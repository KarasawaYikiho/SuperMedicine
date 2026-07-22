"""Stable application-service result contract shared by every interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any, Generic, TypeVar
from uuid import uuid4

from core.redaction import redact_sensitive


T = TypeVar("T")


def _service_meta(service: str, operation: str) -> dict[str, str]:
    return {"service": service, "operation": operation}


def _safe_internal_message(exc: Exception, fallback: str) -> str:
    return str(redact_sensitive(str(exc))) or fallback


def _require_data(
    default_message: str,
    error_map: Mapping[str, type[Exception]],
    result: ServiceResult[Any],
) -> Any:
    """Restore legacy exceptions at compatibility interfaces."""
    if result.ok:
        return result.data
    error = result.error
    message = error.message if error else default_message
    exception_type = error_map.get(error.code if error else "", ValueError)
    raise exception_type(message)


@dataclass(frozen=True, slots=True)
class ServiceError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ServiceResult(Generic[T]):
    ok: bool
    data: T | None
    error: ServiceError | None
    request_id: str
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        data: T,
        *,
        request_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ServiceResult[T]:
        return cls(
            ok=True,
            data=data,
            error=None,
            request_id=request_id or uuid4().hex,
            meta=dict(meta or {}),
        )

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        *,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ServiceResult[Any]:
        return cls(
            ok=False,
            data=None,
            error=ServiceError(code, message, dict(details or {})),
            request_id=request_id or uuid4().hex,
            meta=dict(meta or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "request_id": self.request_id,
            "meta": dict(self.meta),
        }
