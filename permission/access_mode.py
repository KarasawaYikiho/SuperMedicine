"""Runtime file access mode policy service.

This module centralizes file access decisions for future CLI/TUI/file-entry
points.  It intentionally models user/system authorization decisions; it never
attempts privilege escalation, UAC bypass, or administrator elevation itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


class AccessMode(str, Enum):
    """User-selectable file access modes."""

    CONSERVATIVE = "conservative"
    SANDBOX = "sandbox"
    FULL = "full"


class FileAccessOperation(str, Enum):
    """Filesystem operation classes understood by the access-mode policy."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


class AccessDecisionStatus(str, Enum):
    """Structured access-mode decision outcomes."""

    ALLOWED = "allowed"
    DENIED = "denied"
    PROMPT_REQUIRED = "prompt_required"


class AccessModeError(ValueError):
    """Base exception for access-mode configuration errors."""


class FullAccessConfirmationRequired(AccessModeError):
    """Raised when full access mode is requested without explicit consent."""


class UnsupportedAccessMode(AccessModeError):
    """Raised when an unknown access mode is supplied."""


@dataclass(frozen=True)
class AccessDecision:
    """Decision returned by :class:`AccessModePolicy` for a path operation."""

    status: AccessDecisionStatus
    path: Path
    operation: FileAccessOperation
    mode: AccessMode
    reason: str
    prompt: str = ""
    helper: str = ""

    @property
    def allowed(self) -> bool:
        """Return whether the requested operation may proceed immediately."""

        return self.status == AccessDecisionStatus.ALLOWED

    @property
    def requires_prompt(self) -> bool:
        """Return whether user authorization is required before proceeding."""

        return self.status == AccessDecisionStatus.PROMPT_REQUIRED


@dataclass(init=False)
class AccessModePolicy:
    """Central path access policy for conservative and full access modes.

    Conservative mode is the default: project-root paths are allowed, external
    read access returns a prompt-required decision, and external write/delete/
    execute access is denied unless the user has authorized the containing
    directory.  Full mode is available only when the caller constructs or
    switches the policy with an explicit confirmation flag/API.
    """

    project_root: Path
    mode: AccessMode
    authorized_external_roots: tuple[Path, ...]
    sandbox_writable_roots: tuple[Path, ...]
    sandbox_allowed_extensions: tuple[str, ...]
    full_mode_confirmed: bool = False

    def __init__(
        self,
        project_root: Path | str,
        mode: AccessMode | str = AccessMode.CONSERVATIVE,
        authorized_external_roots: Iterable[Path | str] = (),
        sandbox_writable_roots: Iterable[Path | str] = (),
        sandbox_allowed_extensions: Iterable[str] = (".md", ".py", ".txt"),
        full_mode_confirmed: bool = False,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.mode = normalize_access_mode(mode)
        self.full_mode_confirmed = full_mode_confirmed
        if self.mode == AccessMode.FULL and not self.full_mode_confirmed:
            raise FullAccessConfirmationRequired(
                "Full file access mode requires explicit user/system confirmation."
            )
        self.authorized_external_roots = tuple(
            Path(root).expanduser().resolve() for root in authorized_external_roots
        )
        configured_sandbox_roots = tuple(sandbox_writable_roots) or (
            "self_evolution",
            "generated",
            "tools/generated",
        )
        self.sandbox_writable_roots = tuple(
            (self.project_root / root).expanduser().resolve()
            if not Path(root).expanduser().is_absolute()
            else Path(root).expanduser().resolve()
            for root in configured_sandbox_roots
        )
        self.sandbox_allowed_extensions = tuple(
            str(extension).lower()
            if str(extension).startswith(".")
            else f".{str(extension).lower()}"
            for extension in sandbox_allowed_extensions
        )

    @classmethod
    def conservative(
        cls,
        project_root: Path | str,
        *,
        authorized_external_roots: Iterable[Path | str] = (),
    ) -> "AccessModePolicy":
        """Create the default conservative access policy."""

        return cls(
            project_root=project_root,
            mode=AccessMode.CONSERVATIVE,
            authorized_external_roots=authorized_external_roots,
        )

    @classmethod
    def sandbox(
        cls,
        project_root: Path | str,
        *,
        sandbox_writable_roots: Iterable[Path | str] = (),
        sandbox_allowed_extensions: Iterable[str] = (".md", ".py", ".txt"),
    ) -> "AccessModePolicy":
        """Create a sandbox access policy for self-evolution style writes."""

        return cls(
            project_root=project_root,
            mode=AccessMode.SANDBOX,
            sandbox_writable_roots=sandbox_writable_roots,
            sandbox_allowed_extensions=sandbox_allowed_extensions,
        )

    @classmethod
    def full(
        cls,
        project_root: Path | str,
        *,
        explicit_confirmation: bool,
    ) -> "AccessModePolicy":
        """Create full access policy only after explicit confirmation."""

        return cls(
            project_root=project_root,
            mode=AccessMode.FULL,
            full_mode_confirmed=explicit_confirmation,
        )

    def switch_mode(
        self,
        mode: AccessMode | str,
        *,
        explicit_confirmation: bool = False,
    ) -> None:
        """Switch runtime mode without restarting the process."""

        next_mode = normalize_access_mode(mode)
        if next_mode == AccessMode.FULL and not explicit_confirmation:
            raise FullAccessConfirmationRequired(
                "Switching to full file access mode requires explicit confirmation."
            )
        self.mode = next_mode
        self.full_mode_confirmed = next_mode == AccessMode.FULL

    def authorize_external_directory(self, path: Path | str) -> Path:
        """Authorize an external directory for full access in conservative mode."""

        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise AccessModeError(
                f"Authorized external path must be a directory: {root}"
            )
        if self._is_relative_to(root, self.project_root):
            return root
        roots = list(self.authorized_external_roots)
        if not any(existing == root for existing in roots):
            roots.append(root)
        self.authorized_external_roots = tuple(roots)
        return root

    def decide(
        self,
        path: Path | str,
        operation: FileAccessOperation | str,
    ) -> AccessDecision:
        """Return the access decision for *path* and *operation*."""

        resolved_path = Path(path).expanduser().resolve()
        op = normalize_file_operation(operation)

        if self.mode == AccessMode.FULL:
            return AccessDecision(
                status=AccessDecisionStatus.ALLOWED,
                path=resolved_path,
                operation=op,
                mode=self.mode,
                reason="full_mode_explicitly_confirmed_current_user_access",
                helper=insufficient_permission_helper(resolved_path),
            )

        if self.mode == AccessMode.SANDBOX:
            if not self._is_relative_to(resolved_path, self.project_root):
                return AccessDecision(
                    status=AccessDecisionStatus.DENIED,
                    path=resolved_path,
                    operation=op,
                    mode=self.mode,
                    reason="sandbox_path_must_remain_inside_project_root",
                    prompt="Sandbox mode blocks paths outside the project root.",
                )
            if op == FileAccessOperation.READ:
                return AccessDecision(
                    status=AccessDecisionStatus.ALLOWED,
                    path=resolved_path,
                    operation=op,
                    mode=self.mode,
                    reason="sandbox_project_read_allowed",
                )
            if op in {FileAccessOperation.DELETE, FileAccessOperation.EXECUTE}:
                return AccessDecision(
                    status=AccessDecisionStatus.DENIED,
                    path=resolved_path,
                    operation=op,
                    mode=self.mode,
                    reason="sandbox_blocks_delete_and_execute_operations",
                    prompt="Sandbox mode permits only controlled file generation writes.",
                )
            if resolved_path.suffix.lower() not in self.sandbox_allowed_extensions:
                return AccessDecision(
                    status=AccessDecisionStatus.DENIED,
                    path=resolved_path,
                    operation=op,
                    mode=self.mode,
                    reason="sandbox_file_type_not_allowed",
                    prompt="Sandbox mode only writes approved Markdown/text/tool source files.",
                )
            if not any(
                self._is_relative_to(resolved_path, root)
                for root in self.sandbox_writable_roots
            ):
                return AccessDecision(
                    status=AccessDecisionStatus.DENIED,
                    path=resolved_path,
                    operation=op,
                    mode=self.mode,
                    reason="sandbox_write_scope_not_allowed",
                    prompt="Sandbox writes must target an explicitly allowed generation directory.",
                )
            return AccessDecision(
                status=AccessDecisionStatus.ALLOWED,
                path=resolved_path,
                operation=op,
                mode=self.mode,
                reason="sandbox_write_scope_and_file_type_allowed",
            )

        if self._is_relative_to(resolved_path, self.project_root):
            return AccessDecision(
                status=AccessDecisionStatus.ALLOWED,
                path=resolved_path,
                operation=op,
                mode=self.mode,
                reason="project_path_allowed_in_conservative_mode",
            )

        if any(
            self._is_relative_to(resolved_path, root)
            for root in self.authorized_external_roots
        ):
            return AccessDecision(
                status=AccessDecisionStatus.ALLOWED,
                path=resolved_path,
                operation=op,
                mode=self.mode,
                reason="external_directory_explicitly_authorized",
            )

        if op == FileAccessOperation.READ:
            return AccessDecision(
                status=AccessDecisionStatus.PROMPT_REQUIRED,
                path=resolved_path,
                operation=op,
                mode=self.mode,
                reason="external_read_requires_user_authorization",
                prompt=(
                    "The requested file is outside the project directory. "
                    "Confirm read-only access or authorize its containing directory."
                ),
            )

        return AccessDecision(
            status=AccessDecisionStatus.DENIED,
            path=resolved_path,
            operation=op,
            mode=self.mode,
            reason="external_write_requires_authorized_directory",
            prompt=(
                "External write/delete/execute access is blocked in conservative "
                "mode until the user explicitly authorizes the external directory."
            ),
        )

    def require_allowed(
        self,
        path: Path | str,
        operation: FileAccessOperation | str,
    ) -> AccessDecision:
        """Return an allowed decision or raise PermissionError with prompt text."""

        decision = self.decide(path, operation)
        if not decision.allowed:
            message = decision.prompt or decision.reason
            raise PermissionError(message)
        return decision

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True


def normalize_access_mode(mode: AccessMode | str) -> AccessMode:
    """Normalize external mode strings to :class:`AccessMode`."""

    if isinstance(mode, AccessMode):
        return mode
    value = str(mode or "").strip().lower().replace("-", "_")
    aliases = {
        "conservative": AccessMode.CONSERVATIVE,
        "sandbox": AccessMode.SANDBOX,
        "safe": AccessMode.SANDBOX,
        "full": AccessMode.FULL,
        "complete": AccessMode.FULL,
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise UnsupportedAccessMode(f"Unsupported file access mode: {mode}") from exc


def normalize_file_operation(
    operation: FileAccessOperation | str,
) -> FileAccessOperation:
    """Normalize operation strings to :class:`FileAccessOperation`."""

    if isinstance(operation, FileAccessOperation):
        return operation
    value = str(operation or "").strip().lower()
    aliases = {
        "read": FileAccessOperation.READ,
        "list": FileAccessOperation.READ,
        "write": FileAccessOperation.WRITE,
        "create": FileAccessOperation.WRITE,
        "update": FileAccessOperation.WRITE,
        "delete": FileAccessOperation.DELETE,
        "remove": FileAccessOperation.DELETE,
        "execute": FileAccessOperation.EXECUTE,
        "exec": FileAccessOperation.EXECUTE,
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise AccessModeError(
            f"Unsupported file access operation: {operation}"
        ) from exc


def insufficient_permission_helper(path: Path | str) -> str:
    """Return a user-facing helper for OS permission failures.

    The helper is descriptive only and deliberately does not elevate, bypass, or
    modify process permissions.
    """

    return (
        f"If the current user/process cannot access {Path(path).expanduser()}, "
        "rerun SuperMedicine as an administrator or approve access through the "
        "operating system UAC/security prompt. SuperMedicine will not silently "
        "escalate privileges or bypass system permissions."
    )


__all__ = [
    "AccessDecision",
    "AccessDecisionStatus",
    "AccessMode",
    "AccessModeError",
    "AccessModePolicy",
    "FileAccessOperation",
    "FullAccessConfirmationRequired",
    "UnsupportedAccessMode",
    "insufficient_permission_helper",
    "normalize_access_mode",
    "normalize_file_operation",
]
