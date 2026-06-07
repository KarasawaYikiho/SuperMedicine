from __future__ import annotations

import os

import pytest

from core.path_safety import (
    DangerousOverwriteError,
    PathOutsideProjectRootError,
    ProtectedPathError,
    SandboxFileTypeError,
    SandboxWriteScopeError,
    SensitiveContentError,
    UnsafePathValueError,
    is_protected_path,
    reject_sensitive_content,
    resolve_project_root,
    validate_destructive_path,
    validate_path_in_project_root,
    validate_sandbox_write_path,
)


def test_resolve_project_root_returns_canonical_path(tmp_path):
    assert resolve_project_root(tmp_path) == tmp_path.resolve()


def test_path_inside_project_root_is_accepted(tmp_path):
    target = tmp_path / "data" / "notes.txt"
    target.parent.mkdir()
    target.write_text("safe", encoding="utf-8")

    assert validate_path_in_project_root("data/notes.txt", tmp_path) == target.resolve()


def test_parent_traversal_outside_project_root_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    traversal = os.path.relpath(outside, tmp_path)

    with pytest.raises(PathOutsideProjectRootError):
        validate_path_in_project_root(traversal, tmp_path)


def test_absolute_path_outside_project_root_is_rejected(tmp_path):
    outside_dir = tmp_path.parent / f"{tmp_path.name}_outside"
    outside_dir.mkdir()
    outside = outside_dir / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(PathOutsideProjectRootError):
        validate_path_in_project_root(outside, tmp_path)


def test_symlink_target_outside_project_root_is_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink not supported on this platform")

    outside_dir = tmp_path.parent / f"{tmp_path.name}_external_target"
    outside_dir.mkdir()
    outside = outside_dir / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "link_to_secret.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(PathOutsideProjectRootError):
        validate_path_in_project_root(link, tmp_path)


def test_protected_directories_are_rejected_for_destructive_operations(tmp_path):
    protected = tmp_path / ".supermedicine" / "policies"
    protected.mkdir(parents=True)
    target = protected / "default.yaml"
    target.write_text("policy", encoding="utf-8")

    assert is_protected_path(target, tmp_path)
    with pytest.raises(ProtectedPathError):
        validate_destructive_path(target, tmp_path)


def test_project_root_is_rejected_for_destructive_operations(tmp_path):
    with pytest.raises(ProtectedPathError):
        validate_destructive_path(tmp_path, tmp_path)


def test_control_character_path_value_is_rejected_before_resolution(tmp_path):
    with pytest.raises(UnsafePathValueError):
        validate_path_in_project_root("safe\x00truncated.txt", tmp_path)


def test_sandbox_write_path_allows_generated_markdown_and_python(tmp_path):
    assert (
        validate_sandbox_write_path("generated/notes.md", tmp_path)
        == (tmp_path / "generated" / "notes.md").resolve()
    )
    assert (
        validate_sandbox_write_path("tools/generated/tool.py", tmp_path)
        == (tmp_path / "tools" / "generated" / "tool.py").resolve()
    )


def test_sandbox_write_path_rejects_traversal_scope_type_and_overwrite(tmp_path):
    existing = tmp_path / "generated" / "notes.md"
    existing.parent.mkdir()
    existing.write_text("existing", encoding="utf-8")

    with pytest.raises(PathOutsideProjectRootError):
        validate_sandbox_write_path("generated/../../escape.md", tmp_path)
    with pytest.raises(SandboxWriteScopeError):
        validate_sandbox_write_path("src/tool.py", tmp_path)
    with pytest.raises(SandboxFileTypeError):
        validate_sandbox_write_path("generated/policy.yaml", tmp_path)
    with pytest.raises(DangerousOverwriteError):
        validate_sandbox_write_path(existing, tmp_path)


def test_generated_content_with_secret_like_values_is_rejected():
    with pytest.raises(SensitiveContentError):
        reject_sensitive_content("api_key=sk-sensitive-content-secret")
    with pytest.raises(SensitiveContentError):
        reject_sensitive_content("token sk-test")
    with pytest.raises(SensitiveContentError):
        reject_sensitive_content("credential sk-abcdef")
