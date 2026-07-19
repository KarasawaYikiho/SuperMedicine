#!/usr/bin/env python3
"""Stable installer entrypoint with a dependency-light initialization fallback."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_entrypoint: ModuleType | None
_FALLBACK_ENV_NAMES = {
    "provider": "SM_LLM_PROVIDER",
    "base_url": "SM_LLM_BASE_URL",
    "api_key": "SM_LLM_API_KEY",
    "model": "SM_LLM_MODEL",
}
try:
    from installer import entrypoint as _imported_entrypoint
except ModuleNotFoundError as exc:
    if exc.name != "installer":
        raise
    _entrypoint = None
else:
    _entrypoint = _imported_entrypoint


def _fallback_init_config(
    project_dir: Path,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    """Create a minimal, valid project config when installer extras are absent."""
    supplied = (provider, base_url, api_key, model)
    if any(supplied) and not all(supplied):
        raise ValueError("provider, base URL, API key, and model must be provided together")

    config: dict[str, Any] = {
        "permission": {"mode": "confirm"},
        "runtime": {
            "harness": {"required": True, "enabled": True},
            "rag": {"required": True, "enabled": True},
        },
    }
    if provider:
        config["llm"] = {
            "provider": provider,
            "providers": {
                provider: {
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model,
                }
            },
        }

    config_dir = Path(project_dir) / ".supermedicine"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        os.chmod(config_path, 0o600)
    except OSError:
        pass
    (config_dir / "agents").mkdir(exist_ok=True)
    (config_dir / "plugins").mkdir(exist_ok=True)


def _fallback_resolve_install_value(name: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_name = _FALLBACK_ENV_NAMES.get(name)
    return os.environ.get(env_name) if env_name else None


def _fallback_normalize_provider(provider: str | None) -> str | None:
    normalized = (provider or "").strip().lower()
    return normalized or None


def _fallback_resolve_api_key(
    provider: str | None, explicit: str | None
) -> str | None:
    if explicit:
        return explicit
    normalized = (provider or "").upper().replace("-", "_")
    if normalized:
        provider_key = os.environ.get(f"{normalized}_API_KEY")
        if provider_key:
            return provider_key
    return os.environ.get("SM_LLM_API_KEY")


def _fallback_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SuperMedicine installer fallback for project initialization"
    )
    parser.add_argument("--init", action="store_true", help="initialize configuration")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--provider")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--model")
    parser.add_argument("--release-exe", type=Path)
    parser.add_argument("--desktop-dir", type=Path)
    parser.add_argument("--exe-target-name")
    parser.add_argument("--exe-overwrite", action="store_true")
    parser.add_argument("--exe-dry-run", action="store_true")
    return parser


def _fallback_interactive() -> None:
    project_text = input("Project directory [current]: ").strip()
    project_dir = Path(project_text) if project_text else Path.cwd()
    input("Extract full payload [no]: ")
    initialize = input("Initialize configuration [yes]: ").strip().lower() not in {
        "n",
        "no",
    }
    provider = input("Provider: ").strip()
    base_url = input("Base URL: ").strip()
    model = input("Model: ").strip()
    api_key = input("API key: ").strip()
    input("Create shortcut [no]: ")
    input("Add to PATH [no]: ")
    input("Release desktop executable [no]: ")
    confirmed = input("Proceed [yes]: ").strip().lower() not in {"n", "no"}
    if confirmed and initialize:
        _fallback_init_config(
            project_dir,
            provider=provider or None,
            base_url=base_url or None,
            api_key=api_key or None,
            model=model or None,
        )
        print(f"SuperMedicine initialized: {project_dir / '.supermedicine'}")


def _fallback_main(argv: list[str] | None = None) -> None:
    parser = _fallback_parser()
    args = parser.parse_args(argv)
    if (argv is None and len(sys.argv) == 1) or args.interactive:
        _fallback_interactive()
        return
    if args.init:
        _fallback_init_config(
            args.project_dir,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
        )
        print(f"Initialized: {args.project_dir / '.supermedicine'}")
    if args.release_exe is not None:
        source = args.release_exe.expanduser().resolve()
        if not source.is_file():
            parser.error(f"--release-exe source does not exist: {source}")
        destination_dir = args.desktop_dir or (Path.home() / "Desktop")
        destination = destination_dir / (args.exe_target_name or source.name)
        if args.exe_dry_run:
            print(f"Release dry-run: {source} -> {destination}")
        else:
            destination_dir.mkdir(parents=True, exist_ok=True)
            if destination.exists() and not args.exe_overwrite:
                parser.error(f"release target already exists: {destination}")
            shutil.copy2(source, destination)
            print(f"Released: {destination}")


if _entrypoint is not None:
    globals().update(
        {
            name: getattr(_entrypoint, name)
            for name in dir(_entrypoint)
            if not (name.startswith("__") and name.endswith("__"))
        }
    )


def init_config(
    project_dir: Path,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    if _entrypoint is not None:
        _entrypoint.init_config(
            project_dir,
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        return
    _fallback_init_config(
        project_dir,
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


def _normalize_provider(provider: str | None) -> str | None:
    if _entrypoint is not None:
        return _entrypoint._normalize_provider(provider)
    return _fallback_normalize_provider(provider)


def _resolve_api_key(provider: str | None, explicit: str | None) -> str | None:
    if _entrypoint is not None:
        return _entrypoint._resolve_api_key(provider, explicit)
    return _fallback_resolve_api_key(provider, explicit)


def _resolve_install_value(name: str, explicit: str | None) -> str | None:
    if _entrypoint is not None:
        return _entrypoint._resolve_install_value(name, explicit)
    return _fallback_resolve_install_value(name, explicit)


def main(argv: list[str] | None = None) -> None:
    if _entrypoint is not None:
        _entrypoint.main(argv)
        return
    _fallback_main(argv)

__all__ = [
    name for name in globals() if not (name.startswith("__") and name.endswith("__"))
]

if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
