#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from core.redaction import redact_sensitive
from core.serialization import json_ready

if TYPE_CHECKING:
    from core.experience import ExperienceScope, ExportFormat

logger = logging.getLogger(__name__)

PERMISSION_RISK_NOTICE = (
    "风险提示：默认保守模式只允许项目内访问；完全访问模式仅使用当前进程/当前用户"
    "已经拥有的系统权限，不会静默提权、不会绕过系统权限。若系统权限不足，请通过"
    "管理员身份运行或操作系统 UAC/安全提示进行显式授权。"
)


def _configure_stdio_errors() -> None:
    """Keep argparse/help output writable on narrow Windows stdio encodings."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, TypeError, ValueError):
            continue


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def _log_json(value: object) -> None:
    """Log JSON output after recursively redacting secret-looking values."""
    logger.info(json.dumps(redact_sensitive(value), ensure_ascii=False, indent=2))


class _RedactingFormatter(logging.Formatter):
    """Formatter that redacts secrets before text reaches CLI streams."""

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.msg
        original_args = record.args
        try:
            record.msg = redact_sensitive(record.getMessage())
            record.args = ()
            return str(redact_sensitive(super().format(record)))
        finally:
            record.msg = original_msg
            record.args = original_args

    def formatException(self, ei) -> str:  # noqa: N802 - logging API name
        return str(redact_sensitive(super().formatException(ei)))


def _configure_cli_logging() -> None:
    """Configure default CLI logging with a secret-redacting formatter."""

    handler = logging.StreamHandler()
    handler.setFormatter(_RedactingFormatter("%(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def _load_release_exe_to_desktop():
    """Lazily load optional Exe release support only when explicitly requested."""

    entrypoint_dir = Path(__file__).resolve().parent
    installer_dir = entrypoint_dir / "installer"
    release_module = installer_dir / "exe_release.py"
    if not installer_dir.is_dir() or not release_module.is_file():
        raise ValueError(
            "桌面 Exe 释放功能不可用: --release-exe requires a complete release package "
            "with installer/exe_release.py. "
            "请重新下载完整发布包，或从包含 installer/ 目录的完整源码/发布目录运行。"
        ) from None

    entrypoint_path = str(entrypoint_dir)
    if entrypoint_path not in sys.path:
        sys.path.insert(0, entrypoint_path)

    try:
        from installer.exe_release import release_exe_to_desktop
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "installer.exe_release"
        raise ValueError(
            "桌面 Exe 释放功能不可用: release package is incomplete "
            f"(missing Python module: {missing_module}). "
            "请重新下载完整发布包，或从包含 installer/ 目录的完整源码/发布目录运行。"
        ) from None
    return release_exe_to_desktop


class CLI:
    """SuperMedicine CLI"""

    def __init__(self) -> None:
        self.kernel = None
        self.orchestrator = None

    def init(
        self,
        project_dir: Path,
        *,
        provider: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        release_exe: Path | None = None,
        desktop_dir: Path | None = None,
        exe_target_name: str | None = None,
        exe_overwrite: bool = False,
        exe_dry_run: bool = False,
    ) -> None:
        """初始化项目"""
        from installer.entrypoint import init_config

        init_config(
            project_dir,
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        logger.info("项目已初始化: %s", project_dir / ".supermedicine")
        if release_exe is not None:
            release_exe_to_desktop = _load_release_exe_to_desktop()
            result = release_exe_to_desktop(
                exe_path=release_exe,
                desktop_dir=desktop_dir,
                target_filename=exe_target_name,
                overwrite=exe_overwrite,
                dry_run=exe_dry_run,
            )
            logger.info(
                "桌面 Exe 释放结果: status=%s target=%s",
                result["status"],
                result["target_path"],
            )

    def status(self) -> None:
        """显示项目状态"""
        logger.info("SuperMedicine Beta0.4.1")
        logger.info("=" * 40)

        # 检查配置
        config_dir = Path.cwd() / ".supermedicine"
        if config_dir.exists():
            from core.config_center import ConfigCenter

            logger.info("[OK] 项目配置已初始化")
            config = ConfigCenter(config_dir / "config.yaml")
            logger.info(
                "[OK] 权限模式: %s (%s)",
                config.get_permission_mode_label(),
                config.get_file_access_config().get("mode"),
            )
            if config.diagnostics().get("load_error"):
                logger.info(
                    "[WARN] 配置读取异常，已使用安全默认值: %s",
                    config.diagnostics().get("load_error"),
                )
        else:
            logger.info("[FAIL] 项目配置未初始化 (运行 'supermedicine init')")

        # 检查插件
        plugins_dir = Path(__file__).parent / "plugins"
        if plugins_dir.exists():
            plugin_count = len(list(plugins_dir.rglob("plugin.yaml")))
            logger.info("[OK] 发现 %s 个插件", plugin_count)

        # 检查测试
        tests_dir = Path(__file__).parent / "tests"
        if tests_dir.exists():
            test_count = len(list(tests_dir.glob("test_*.py")))
            logger.info("[OK] 发现 %s 个测试模块", test_count)

    def test(self) -> None:
        """运行测试"""
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=Path(__file__).parent,
        )
        sys.exit(result.returncode)

    def run(
        self,
        task: str,
        verbose: bool = False,
        plugin: str | None = None,
        action: str | None = None,
        params: dict | None = None,
        workspace: str | None = None,
    ) -> dict:
        """执行任务 — 真实执行用户任务与医疗插件"""
        from core.kernel import Kernel
        from permission.engine import PermissionEngine
        from core.workspace import WorkspaceManager

        # 确定项目根目录
        project_dir = Path.cwd()

        logger.info("SuperMedicine Beta0.4.1 — 任务执行")
        logger.info("任务: %s", redact_sensitive(task))
        logger.info("=" * 50)

        execution_params = params
        if workspace is not None:
            workspace_info = WorkspaceManager(project_dir).get_workspace(workspace)
            workspace_context = {
                "id": workspace_info.id,
                "path": str(workspace_info.path),
                "metadata": workspace_info.metadata.to_dict(),
            }
            execution_params = dict(params or {})
            execution_params["_workspace"] = workspace_context
            logger.info("Workspace: %s", workspace_info.id)

        # 初始化 Kernel（集成 PermissionEngine）
        policies_dir = project_dir / ".supermedicine" / "policies"
        default_policy = policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME
        if not default_policy.exists():
            raise FileNotFoundError(
                f"默认权限策略不存在: {default_policy}. 请先运行 'supermedicine init' "
                "或恢复仓库中的 .supermedicine/policies/default.yaml。"
            )

        kernel = Kernel(
            config_path=project_dir / ".supermedicine" / "config.yaml",
            plugins_dir=project_dir / "plugins",
            policies_dir=policies_dir,
        )

        if verbose:
            logger.info("[OK] Kernel 已初始化")
            logger.info("     Config: %s", kernel._config_path)
            logger.info("     Plugins: %s", kernel._plugins_dir)
            logger.info("     Policies: %s", kernel._policies_dir)
            logger.info("     PermissionEngine: 已激活")
            logger.info("     Checkpoints: %s", kernel.checkpoint_manager.base_dir)

        # 发现插件
        plugins = kernel.plugin_registry.discover()
        logger.info("[OK] 已发现 %d 个插件", len(plugins))
        if verbose:
            for p in plugins:
                logger.info("     - %s (%s)", p.name, p.type)

        result = kernel.execute_task(
            task, plugin_name=plugin, action=action, params=execution_params
        )
        if verbose:
            logger.info(
                "[STATE] agent=%s task=%s plugin=%s action=%s status=%s",
                result.get("agent", "alpha"),
                result.get("task", task),
                result.get("plugin"),
                result.get("action"),
                result.get("status"),
            )
        _log_json(result)
        return result

    def workspace_init(self, workspace_id: str, name: str | None = None) -> dict:
        """Initialize an explicitly named workspace."""
        from core.workspace import WorkspaceManager

        info = WorkspaceManager(Path.cwd()).initialize_workspace(workspace_id)
        if name is not None:
            metadata_path = info.path / "workspace.yaml"
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            metadata["display_name"] = name
            metadata_path.write_text(
                yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            info = WorkspaceManager(Path.cwd()).get_workspace(workspace_id)
        result = _workspace_info_to_dict(info, name=name)
        _log_json(result)
        return result

    def workspace_list(self) -> list[dict]:
        """List initialized workspaces without consulting recent TUI state."""
        from core.workspace import WorkspaceManager

        workspaces = [
            _workspace_info_to_dict(info)
            for info in WorkspaceManager(Path.cwd()).list_workspaces()
        ]
        _log_json(workspaces)
        return workspaces

    def workspace_show(self, workspace_id: str) -> dict:
        """Show one explicitly requested workspace."""
        from core.workspace import WorkspaceManager

        info = WorkspaceManager(Path.cwd()).get_workspace(workspace_id)
        result = _workspace_info_to_dict(info)
        _log_json(result)
        return result

    def workspace_delete(self, workspace_id: str, confirm: str) -> dict:
        """Hard-delete an explicitly confirmed workspace after guard approval."""
        from core.operation_guard import authorize_dangerous_operation
        from core.path_safety import validate_destructive_path
        from core.workspace import WorkspaceManager, validate_workspace_id
        from permission.audit import AuditLogger
        from permission.engine import PermissionEngine

        project_dir = Path.cwd()
        manager = WorkspaceManager(project_dir)
        slug = validate_workspace_id(workspace_id)
        workspace_path = manager.workspace_path(slug)
        audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
        audit_logger = AuditLogger(audit_log)

        if confirm != slug:
            audit_logger.log(
                agent_id="delta",
                action="workspace.delete",
                resource=str(workspace_path),
                result="cancelled",
                reason="confirmation_mismatch",
            )
            raise ValueError("--confirm must exactly match --workspace for deletion")

        manager.get_workspace(slug)
        safe_path = validate_destructive_path(workspace_path, project_dir)

        policies_dir = project_dir / ".supermedicine" / "policies"
        default_policy = policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME
        if not default_policy.exists():
            audit_logger.log(
                agent_id="delta",
                action="workspace.delete",
                resource=str(safe_path),
                result="cancelled",
                reason="missing_default_policy",
            )
            raise FileNotFoundError(
                f"默认权限策略不存在: {default_policy}. 请先运行 'supermedicine init' "
                "或恢复仓库中的 .supermedicine/policies/default.yaml。"
            )

        permission_engine = PermissionEngine(policies_dir, audit_log)
        authorization = authorize_dangerous_operation(
            permission_engine=permission_engine,
            agent_id="delta",
            action="workspace.delete",
            path=safe_path,
            project_root=project_dir,
            context={"workspace_id": slug},
            destructive=True,
            audit_logger=audit_logger,
            operation="workspace_delete",
        )

        if authorization.path.is_dir():
            shutil.rmtree(authorization.path)
        else:
            authorization.path.unlink()

        result = {"status": "deleted", "id": slug, "path": str(authorization.path)}
        _log_json(result)
        return result

    def tool_init(self, workspace_id: str) -> dict:
        """Initialize workspace-local Python/R tool directories."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).initialize_tools(workspace_id)
        _log_json(result)
        return result

    def tool_list(self, workspace_id: str, language: str | None = None) -> dict:
        """List workspace-local tools grouped by language."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).list_tools(
            workspace_id, language=language
        )
        _log_json(result)
        return result

    def tool_scan(self, language: str | None = None) -> dict:
        """Scan Python/R source tool directories for selectable import candidates."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).scan_import_candidates(language)
        _log_json(result)
        return result

    def tool_add(
        self,
        workspace_id: str,
        selections: list[str] | None = None,
        *,
        language: str | None = None,
        overwrite: bool = False,
    ) -> dict:
        """Import scanned Python/R tools selected from the candidate list."""
        from core.workspace_tools import WorkspaceToolService

        service = WorkspaceToolService(Path.cwd())
        if not selections:
            result = {
                "status": "select_required",
                "message": "Select tools from this scanned list with --select; no tool ID knowledge is required.",
                "candidates": service.scan_import_candidates(language),
            }
        else:
            result = service.import_scanned_tools(
                workspace_id, selections, language=language, overwrite=overwrite
            )
            imported_raw: object = result.get("imported")
            imported_items: list[dict[str, Any]] = (
                [cast(dict[str, Any], item) for item in imported_raw if isinstance(item, dict)]
                if isinstance(imported_raw, list)
                else []
            )
            if imported_items:
                from core.config_center import ConfigCenter

                config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
                config.set_runtime_state_value("last_workspace_id", workspace_id)
                config.record_tool_import_state(
                    workspace_id=workspace_id,
                    imported=imported_items,
                    save=True,
                )
        _log_json(result)
        return result

    def tool_show(self, workspace_id: str, language: str, tool_id: str) -> dict:
        """Show one workspace-local tool manifest."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).show_tool(
            workspace_id, language, tool_id
        )
        _log_json(result)
        return result

    def tool_run(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        dry_run: bool = False,
        input_path: str | None = None,
        output_path: str | None = None,
    ) -> dict:
        """Prepare a guarded workspace-local tool invocation without unsafe execution."""
        from core.workspace_tools import WorkspaceToolService

        result = (
            WorkspaceToolService(Path.cwd())
            .prepare_invocation(
                workspace_id,
                language,
                tool_id,
                dry_run=dry_run,
                input_path=input_path,
                output_path=output_path,
            )
            .to_dict()
        )
        _log_json(result)
        return result

    def llm_add(
        self,
        provider: str,
        *,
        api_format: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        headers: dict | None = None,
        set_current: bool = False,
    ) -> dict:
        """Add or update an LLM provider through the shared manager."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager

        values = _llm_provider_values(
            api_format=api_format,
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            model=model,
            timeout=timeout,
            headers=headers,
        )
        manager = LLMConfigManager(
            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
            restore_on_startup=False,
        )
        result = manager.add_provider(provider, values, set_current=set_current)
        _log_json(result)
        return result

    def llm_list(self) -> dict:
        """List configured LLM providers with secret-safe output."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager

        manager = LLMConfigManager(
            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
            restore_on_startup=False,
        )
        config = manager._config
        result = {
            "current_provider": config.get_llm_current_provider_name(),
            "last_provider": config.get_llm_last_provider_name(),
            "providers": manager.list_providers(redacted=True),
        }
        _log_json(result)
        return result

    def llm_show(self, provider: str | None = None) -> dict:
        """Show one LLM provider, defaulting to the current provider, redacted."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager

        manager = LLMConfigManager(
            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
            restore_on_startup=True,
        )
        result = (
            manager.get_provider(provider, redacted=True)
            if provider
            else manager.get_current_provider(redacted=True)
        )
        _log_json(result)
        return result

    def llm_switch(self, provider: str) -> dict:
        """Persistently switch the current LLM provider."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager

        manager = LLMConfigManager(
            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
            restore_on_startup=False,
        )
        result = manager.switch_provider(provider, save=True)
        _log_json(result)
        return result

    def permission_status(self) -> dict[str, Any]:
        """Show current CLI file access mode and authorized external roots."""
        from core.config_center import ConfigCenter

        config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
        file_access = config.get_file_access_config()
        result = _permission_result(file_access, changed=False)
        result["config_load_error"] = config.diagnostics().get("load_error", "")
        _log_json(result)
        return result

    def permission_set_mode(
        self,
        mode: str,
        *,
        confirm_full: bool = False,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Persistently switch CLI file access mode without privilege escalation."""
        from core.config_center import ConfigCenter
        from permission.access_mode import AccessMode, normalize_access_mode

        normalized = normalize_access_mode(mode)
        explicit_confirmation = confirm_full
        if normalized == AccessMode.FULL and not explicit_confirmation and interactive:
            explicit_confirmation = _confirm_full_access_interactively()
        config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
        file_access = config.set_file_access_mode(
            normalized,
            explicit_confirmation=explicit_confirmation,
        )
        config.save()
        result = _permission_result(
            file_access,
            changed=True,
            message="权限模式已切换；后续策略读取会立即使用新的配置。",
        )
        _log_json(result)
        return result

    def permission_authorize(self, path: str | Path) -> dict[str, Any]:
        """Persistently authorize an external directory for conservative mode."""
        from core.config_center import ConfigCenter

        config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
        file_access = config.authorize_external_file_access_directory(path)
        config.save()
        result = _permission_result(
            file_access,
            changed=True,
            message="外部授权目录已添加；后续策略读取会立即使用新的配置。",
        )
        _log_json(result)
        return result

    def permission_revoke(self, path: str | Path) -> dict[str, Any]:
        """Persistently remove an external directory authorization."""
        from core.config_center import ConfigCenter

        config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
        file_access = config.revoke_external_file_access_directory(path)
        config.save()
        result = _permission_result(
            file_access,
            changed=True,
            message="外部授权目录已移除；后续策略读取会立即使用新的配置。",
        )
        _log_json(result)
        return result

    def diagnose(self) -> dict:
        """Print secret-safe diagnostics for config, LLM, install artifacts, and audit log."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager

        project_dir = Path.cwd()
        config = ConfigCenter(project_dir / ".supermedicine" / "config.yaml")
        manager = LLMConfigManager(config, restore_on_startup=False)
        audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
        config_diag: dict[str, Any] = config.diagnostics()
        llm_diag: dict[str, Any] = manager.diagnostics()
        result: dict[str, Any] = {
            "ok": True,
            "stage": "diagnose",
            "project_dir": str(project_dir),
            "config": config_diag,
            "llm": llm_diag,
            "audit": {
                "path": str(audit_log),
                "exists": audit_log.exists(),
                "writable_parent": audit_log.parent.exists(),
            },
            "commands": {
                "init": "set provider API key env var first, then run: supermedicine init --provider <name> --base-url <url> --model <model>",
                "llm_list": "supermedicine llm list",
                "llm_switch": "supermedicine llm switch <provider>",
                "tui_dry_run": "supermedicine tui --dry-run",
                "uninstall_dry_run": "python Uninstall.py --dry-run",
            },
        }
        result["ok"] = bool(config_diag.get("exists")) and bool(llm_diag.get("ok"))
        _log_json(result)
        return result

    def paper_import(
        self,
        workspace_id: str,
        source_path: str | Path,
        metadata: dict | None = None,
        enrich: bool = False,
        confirm_enrich: bool = False,
    ) -> dict:
        """Import a local paper into an explicitly selected workspace."""
        from core.paper_import.enrichment import PaperEnricher
        from core.paper_import.importer import PaperImporter
        from permission.audit import AuditLogger
        from permission.engine import PermissionEngine

        project_dir = Path.cwd()
        importer = PaperImporter(project_dir)
        import_result = importer.import_file(workspace_id, source_path, metadata or {})
        warnings = list(import_result.warnings)

        if enrich:
            audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
            enricher = PaperEnricher(
                PermissionEngine(
                    project_dir / ".supermedicine" / "policies", audit_log
                ),
                AuditLogger(audit_log),
            )
            enrichment_result = enricher.enrich(
                import_result.metadata, confirmed=confirm_enrich
            )
            if enrichment_result.status == "enriched":
                importer.save_paper_metadata(workspace_id, enrichment_result.metadata)
            if enrichment_result.warning:
                warnings.append(enrichment_result.warning)

        result = _paper_import_result_to_dict(import_result, warnings=warnings)
        _log_json(result)
        return result

    def paper_list(self, workspace_id: str) -> list[dict]:
        """List papers from an explicitly selected workspace."""
        from core.paper_import.importer import PaperImporter

        papers = [
            _paper_metadata_to_dict(paper)
            for paper in PaperImporter(Path.cwd()).list_papers(workspace_id)
        ]
        _log_json(papers)
        return papers

    def paper_show(self, workspace_id: str, paper_id: str) -> dict:
        """Show one imported paper from an explicitly selected workspace."""
        from core.paper_import.importer import PaperImporter

        result = _paper_metadata_to_dict(
            PaperImporter(Path.cwd()).get_paper(workspace_id, paper_id)
        )
        _log_json(result)
        return result

    def paper_edit(self, workspace_id: str, paper_id: str, metadata: dict) -> dict:
        """Edit metadata for one imported paper from an explicit workspace."""
        from core.paper_import.importer import PaperImporter

        result = _paper_metadata_to_dict(
            PaperImporter(Path.cwd()).update_paper_metadata(
                workspace_id, paper_id, metadata
            )
        )
        _log_json(result)
        return result

    def paper_enrich(
        self, workspace_id: str, paper_id: str, confirm_enrich: bool
    ) -> dict:
        """Enrich one imported paper after explicit confirmation and permission approval."""
        from core.paper_import.enrichment import PaperEnricher
        from core.paper_import.importer import PaperImporter
        from permission.audit import AuditLogger
        from permission.engine import PermissionEngine

        project_dir = Path.cwd()
        importer = PaperImporter(project_dir)
        metadata = importer.get_paper(workspace_id, paper_id)
        audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
        enrichment_result = PaperEnricher(
            PermissionEngine(project_dir / ".supermedicine" / "policies", audit_log),
            AuditLogger(audit_log),
        ).enrich(metadata, confirmed=confirm_enrich)
        if enrichment_result.status == "enriched":
            importer.save_paper_metadata(workspace_id, enrichment_result.metadata)
        result = {
            "status": enrichment_result.status,
            "warning": enrichment_result.warning,
            "applied_fields": enrichment_result.applied_fields,
            "metadata": _paper_metadata_to_dict(enrichment_result.metadata),
        }
        _log_json(result)
        return result

    def experience_suggest(
        self,
        workspace_id: str,
        summary: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Suggest an experience classification without persisting anything."""
        from core.experience import ExperienceStore

        result = (
            ExperienceStore(Path.cwd())
            .suggest_classification(
                workspace_id=workspace_id,
                title=title,
                summary=summary,
                tags=tags,
            )
            .to_dict()
        )
        result["workspace_id"] = workspace_id
        _log_json(result)
        return result

    def experience_add(
        self,
        workspace_id: str,
        scope: str,
        title: str,
        summary: str,
        tags: list[str] | None = None,
        confirm: bool = False,
    ) -> dict:
        """Persist a user-confirmed experience in the chosen scope."""
        from core.experience import ExperienceStore

        if not confirm:
            raise ValueError("experience add requires explicit --confirm")
        experience_scope = _as_experience_scope(scope)
        record = ExperienceStore(Path.cwd()).confirm_classification(
            workspace_id=workspace_id,
            scope=experience_scope,
            title=title,
            summary=summary,
            tags=tags,
        )
        result = record.to_dict()
        _log_json(result)
        return result

    def experience_list(
        self, workspace_id: str, include_general: bool = False
    ) -> list[dict]:
        """List experiences visible from an explicit workspace context."""
        from core.experience import ExperienceStore

        records = [
            record.to_dict()
            for record in ExperienceStore(Path.cwd()).list_experiences(
                workspace_id,
                include_general=include_general,
            )
        ]
        _log_json(records)
        return records

    def experience_view(
        self, record_id: str, workspace_id: str, scope: str | None = None
    ) -> dict:
        """View one visible experience by id."""
        from core.experience import ExperienceStore

        experience_scope = _as_optional_experience_scope(scope)
        record = ExperienceStore(Path.cwd()).get_experience(
            record_id,
            workspace_id=workspace_id,
            scope=experience_scope,
        )
        result = record.to_dict()
        _log_json(result)
        return result

    def experience_edit(
        self,
        record_id: str,
        workspace_id: str,
        scope: str,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Edit one experience in an explicit scope."""
        from core.experience import ExperienceStore

        experience_scope = _as_experience_scope(scope)
        record = ExperienceStore(Path.cwd()).edit_experience(
            record_id,
            workspace_id=workspace_id,
            scope=experience_scope,
            title=title,
            summary=summary,
            tags=tags,
        )
        result = record.to_dict()
        _log_json(result)
        return result

    def experience_delete(
        self, record_id: str, workspace_id: str, scope: str, confirm: str
    ) -> dict:
        """Delete one experience after exact id confirmation."""
        from core.experience import ExperienceStore

        if confirm != record_id:
            raise ValueError("--confirm must exactly match the experience id")
        experience_scope = _as_experience_scope(scope)
        deleted = ExperienceStore(Path.cwd()).delete_experience(
            record_id,
            workspace_id=workspace_id,
            scope=experience_scope,
        )
        result = {"status": "deleted", "id": deleted.id, "scope": deleted.scope}
        _log_json(result)
        return result

    def experience_export(
        self,
        workspace_id: str,
        format: str,
        include_general: bool = False,
        output: str | None = None,
    ) -> str:
        """Export visible experiences as JSON or Markdown."""
        from core.experience import ExperienceStore

        export_format = _as_export_format(format)
        rendered = ExperienceStore(Path.cwd()).export_experiences(
            workspace_id=workspace_id,
            format=export_format,
            include_general=include_general,
            path=output,
        )
        logger.info("%s", redact_sensitive(rendered))
        return rendered

    def experiment_start(self, protocol: str, session_id: str | None = None) -> dict:
        """Start a standalone experiment guide session and persist it as JSON."""
        from core.config_center import ConfigCenter
        from core.experiment_guide import (
            ExperimentGuide,
            MEDICAL_BOUNDARY,
            append_experiment_log_event,
        )
        from core.log_report import LogReportStore

        session = ExperimentGuide().create_session(protocol, session_id=session_id)
        ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml").set_selected_experiment_protocol(
            session.protocol.protocol_id,
            save=True,
        )
        session_file = (
            Path.cwd() / ".supermedicine" / "experiments" / f"{session.session_id}.json"
        )
        _save_experiment_session(session_file, session.to_dict())
        append_experiment_log_event(
            LogReportStore(Path.cwd()),
            "experiment_started",
            session,
            message="experiment guide session started",
        )
        result = _experiment_response(
            session, session_file=session_file, medical_boundary=MEDICAL_BOUNDARY
        )
        _log_json(result)
        return result

    def experiment_list(self) -> list[dict]:
        """List configured experiment protocols discovered from plugins/experiments."""
        from core.experiment_protocols import list_protocols

        result = [
            {
                "protocol_id": protocol.protocol_id,
                "title": protocol.title,
                "description": protocol.description,
                "version": protocol.version,
                "metadata": protocol.metadata,
                "step_count": len(protocol.steps),
            }
            for protocol in list_protocols()
        ]
        _log_json(result)
        return result

    def experiment_context(self, protocol: str | None = None) -> dict:
        """Show the experiment context and authoring rules injected into LLM chat."""
        from core.config_center import ConfigCenter
        from core.experiment_protocols import build_experiment_llm_context

        result = build_experiment_llm_context(protocol)
        selected = result.get("selected_protocol") if isinstance(result, dict) else None
        if protocol and isinstance(selected, dict) and selected.get("protocol_id"):
            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml").set_selected_experiment_protocol(
                str(selected["protocol_id"]),
                save=True,
            )
            result["runtime_sync"] = {
                "selected_experiment_protocol": selected["protocol_id"],
                "message": "实验配置选择已同步到统一配置；后续 LLM 上下文会读取该协议。",
            }
        _log_json(result)
        return result

    def experiment_add_config(
        self,
        *,
        instruction: str | None = None,
        config_json: str | None = None,
        filename: str | None = None,
        overwrite: bool = False,
    ) -> dict:
        """Draft/validate and save a new experiment config in plugins/experiments."""
        from core.experiment_protocols import (
            create_experiment_config_from_instruction,
            save_experiment_config,
        )

        if bool(instruction and instruction.strip()) == bool(config_json and config_json.strip()):
            raise ValueError("provide exactly one of --instruction or --config-json")
        if config_json and config_json.strip():
            payload = _load_input_json(config_json)
            result = save_experiment_config(
                payload,
                filename=filename,
                overwrite=overwrite,
            )
        else:
            result = create_experiment_config_from_instruction(
                instruction or "",
                filename=filename,
                overwrite=overwrite,
            )
        protocol = result.get("protocol") if isinstance(result, dict) else None
        if isinstance(protocol, dict) and protocol.get("protocol_id"):
            from core.config_center import ConfigCenter

            ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml").set_selected_experiment_protocol(
                str(protocol["protocol_id"]),
                save=True,
            )
            result["runtime_sync"] = {
                "selected_experiment_protocol": protocol["protocol_id"],
                "message": "新增实验配置已同步为后续 LLM 上下文的当前实验。",
            }
        _log_json(result)
        return result

    def experiment_show(self, session_file: str | Path) -> dict:
        """Show a persisted experiment guide session."""
        from core.experiment_guide import ExperimentGuide, MEDICAL_BOUNDARY

        path = Path(session_file)
        session = ExperimentGuide().restore_session(_load_experiment_session(path))
        result = _experiment_response(
            session, session_file=path, medical_boundary=MEDICAL_BOUNDARY
        )
        _log_json(result)
        return result

    def experiment_submit(
        self,
        session_file: str | Path,
        step_id: str,
        input_json: str,
        *,
        calculate: bool = False,
    ) -> dict:
        """Submit data for the current experiment step, optionally running a configured calculation."""
        from core.experiment_guide import (
            CalculationResult,
            ExperimentGuide,
            MEDICAL_BOUNDARY,
            append_experiment_log_event,
        )
        from core.log_report import LogReportStore
        from plugins.tools.experiment_wb import main as wb_plugin

        path = Path(session_file)
        guide = ExperimentGuide()
        session = guide.restore_session(_load_experiment_session(path))
        payload = _load_input_json(input_json)
        user_input = _dict_payload(payload.get("user_input", payload), "user_input")
        outputs = _dict_payload(payload.get("outputs", {}), "outputs")
        calculation_params = _dict_payload(
            payload.get("calculation_params", {}), "calculation_params"
        )
        log_store = LogReportStore(Path.cwd())
        calculation_results: list[CalculationResult | dict[str, Any]] = []
        plugin_request: dict[str, Any] | None = None
        kernel_result: dict[str, Any] | None = None

        if calculate:
            requests = session.build_plugin_requests(
                step_id, calculation_params=calculation_params
            )
            if not requests:
                if session.protocol.protocol_id == "western_blot_basic":
                    raise ValueError(
                        f"step {step_id} has no supported WB calculation request"
                    )
                raise ValueError(
                    f"step {step_id} has no supported experiment calculation request"
                )
            plugin_request = requests[0]
            if plugin_request.get("plugin_name") != "experiment-wb":
                raise ValueError(
                    "CLI --calculate currently supports experiment-wb plugin requests only; "
                    f"got {plugin_request.get('plugin_name')}"
                )
            kernel_result = wb_plugin.execute(
                plugin_request["action"],
                plugin_request["params"],
                plugin_request["metadata"],
            )
            if kernel_result.get("status") != "success":
                raise ValueError(
                    str(kernel_result.get("error") or "WB calculation failed")
                )
            append_experiment_log_event(
                log_store,
                "plugin_result",
                session,
                step_id=step_id,
                plugin_request=plugin_request,
                kernel_result=kernel_result,
            )
            calculation_results.append(
                {
                    "request_id": str(plugin_request["request_id"]),
                    "status": "completed",
                    "value": kernel_result.get("output"),
                    "metadata": {
                        "plugin": kernel_result.get("plugin"),
                        "action": kernel_result.get("action"),
                        "metadata": kernel_result.get("metadata", {}),
                    },
                }
            )

        record = session.submit_step(
            step_id,
            user_input,
            outputs=outputs,
            calculation_results=calculation_results,
        )
        _save_experiment_session(path, session.to_dict())
        append_experiment_log_event(
            log_store,
            "step_input_submitted",
            session,
            step_id=step_id,
            user_input=user_input,
            outputs=outputs,
            record=record.to_dict(),
        )
        append_experiment_log_event(
            log_store,
            "experiment_completed" if session.is_completed else "step_guidance",
            session,
            step_id=step_id,
            record=record.to_dict(),
        )
        result = _experiment_response(
            session,
            session_file=path,
            record=record.to_dict(),
            plugin_request=plugin_request,
            kernel_result=kernel_result,
            medical_boundary=MEDICAL_BOUNDARY,
        )
        _log_json(result)
        return result

    def log_write(self, message: str, session_id: str | None = None) -> dict:
        """Write a redacted log report."""
        from core.log_report import LogReportStore

        result = LogReportStore(Path.cwd()).write(message, session_id=session_id)
        _log_json(result)
        return result

    def log_list(self) -> list[dict]:
        """List redacted log report summaries."""
        from core.log_report import LogReportStore

        result = LogReportStore(Path.cwd()).list()
        _log_json(result)
        return result

    def log_show(self, file_name: str) -> dict:
        """Show a redacted log report."""
        from core.log_report import LogReportStore

        result = LogReportStore(Path.cwd()).show(file_name)
        _log_json(result)
        return result

    def tui(self, dry_run: bool = False):
        """启动中文 TUI 工作台；不会改变 CLI 默认工作区行为。"""
        from core.tui.app import launch_tui

        return launch_tui(dry_run=dry_run, project_root=Path.cwd())


def _workspace_info_to_dict(info, name: str | None = None) -> dict:
    """Return a JSON-serializable workspace representation."""
    metadata = info.metadata.to_dict()
    metadata_path = info.path / "workspace.yaml"
    if metadata_path.is_file():
        raw_metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if (
            isinstance(raw_metadata, dict)
            and raw_metadata.get("display_name") is not None
        ):
            metadata["display_name"] = str(raw_metadata["display_name"])
    data = {
        "id": info.id,
        "path": str(info.path),
        "metadata": metadata,
    }
    if name is not None:
        data["name"] = name
    elif metadata.get("display_name") is not None:
        data["name"] = metadata["display_name"]
    return data


_EXPERIENCE_SCOPE_CHOICES = frozenset({"general", "workspace"})
_EXPORT_FORMAT_CHOICES = frozenset({"json", "md"})


def _as_experience_scope(scope: str) -> ExperienceScope:
    if scope not in _EXPERIENCE_SCOPE_CHOICES:
        raise ValueError("experience scope must be one of: general, workspace")
    return cast("ExperienceScope", scope)


def _as_optional_experience_scope(scope: str | None) -> ExperienceScope | None:
    if scope is None:
        return None
    return _as_experience_scope(scope)


def _as_export_format(format: str) -> ExportFormat:
    if format not in _EXPORT_FORMAT_CHOICES:
        raise ValueError("export format must be one of: json, md")
    return cast("ExportFormat", format)


def _paper_metadata_to_dict(metadata) -> dict:
    return json_ready(metadata)


def _paper_import_result_to_dict(
    import_result, warnings: list[str] | None = None
) -> dict:
    return {
        "metadata": _paper_metadata_to_dict(import_result.metadata),
        "source_path": str(import_result.source_path)
        if import_result.source_path
        else None,
        "warnings": warnings if warnings is not None else list(import_result.warnings),
        "duplicate": import_result.duplicate,
        "duplicate_reason": import_result.duplicate_reason,
    }


def _paper_metadata_options(args) -> dict:
    metadata: dict = {}
    for field in ("title", "doi", "pmid", "notes"):
        value = getattr(args, field, None)
        if value is not None:
            metadata[field] = value
    tags = getattr(args, "tag", None)
    if tags is not None:
        metadata["tags"] = tags
    return metadata


def _load_params_json(raw_json: str) -> dict:
    """Parse structured plugin params from a JSON object string."""
    try:
        params = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--params-json must be valid JSON: {exc.msg}") from exc

    if not isinstance(params, dict):
        raise ValueError("plugin params must be a JSON object")
    return params


def _load_input_json(raw_json: str) -> dict:
    """Parse experiment step input from a JSON object string."""
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--input-json must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("--input-json must be a JSON object")
    return payload


def _dict_payload(value: object, name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _load_experiment_session(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"experiment session file not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"could not read experiment session file {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("experiment session file must contain a JSON object")
    return data


def _save_experiment_session(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_ready(redact_sensitive(data)), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _experiment_response(
    session,
    *,
    session_file: Path,
    medical_boundary: str,
    record: dict | None = None,
    plugin_request: dict | None = None,
    kernel_result: dict | None = None,
) -> dict:
    next_step = session.current_step
    return {
        "status": session.status.value
        if hasattr(session.status, "value")
        else str(session.status),
        "session_file": str(session_file),
        "session": session.to_dict(),
        "current_step": next_step.to_dict() if next_step else None,
        "record": record,
        "plugin_request": plugin_request,
        "kernel_result": kernel_result,
        "progress": session.progress,
        "medical_boundary": medical_boundary,
    }


def _load_params_file(path: str) -> dict:
    """Read structured plugin params from a JSON object file."""
    params_path = Path(path)
    try:
        raw_json = params_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"--params-file could not be read: {exc}") from exc
    try:
        return _load_params_json(raw_json)
    except ValueError as exc:
        raise ValueError(f"--params-file {params_path}: {exc}") from exc


def _resolve_run_params(
    params_json: str | None, params_file: str | None
) -> dict | None:
    """Resolve optional structured params for the run command."""
    if params_json and params_file:
        raise ValueError("--params-json and --params-file cannot be used together")
    if params_json:
        return _load_params_json(params_json)
    if params_file:
        return _load_params_file(params_file)
    return None


def _permission_result(
    file_access: dict[str, Any],
    *,
    changed: bool,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": file_access.get("mode", "conservative"),
        "mode_label": "完全访问" if file_access.get("mode") == "full" else "保守",
        "full_mode_confirmed": bool(file_access.get("full_mode_confirmed")),
        "authorized_external_roots": list(
            file_access.get("authorized_external_roots", [])
        ),
        "changed": changed,
        "runtime_effect": "后续策略读取即时生效；已创建的独立策略对象需重新读取配置。",
        "risk_notice": PERMISSION_RISK_NOTICE,
        "message": message or "当前权限模式配置。",
    }


def _confirm_full_access_interactively() -> bool:
    if not sys.stdin.isatty():
        return False
    logger.warning(PERMISSION_RISK_NOTICE)
    logger.warning("请输入 FULL 确认切换到完全访问模式：")
    try:
        answer = input().strip()
    except EOFError:
        return False
    return answer == "FULL"


def _parse_llm_headers(
    header_items: list[str] | None, headers_json: str | None
) -> dict[str, str]:
    """Resolve LLM headers from repeated key=value args and optional JSON object."""
    headers: dict[str, str] = {}
    if headers_json:
        try:
            parsed = json.loads(headers_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--headers-json must be valid JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("--headers-json must be a JSON object")
        headers.update({str(key): str(value) for key, value in parsed.items()})
    for item in header_items or []:
        if "=" not in item:
            raise ValueError("--header must use KEY=VALUE format")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--header key cannot be empty")
        headers[key] = value
    return headers


def _llm_provider_values(
    *,
    api_format: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    headers: dict | None = None,
) -> dict:
    """Build provider values for LLMConfigManager without duplicating persistence logic."""
    values: dict = {}
    for key, value in {
        "api_format": api_format,
        "base_url": base_url,
        "api_key": api_key,
        "api_key_env": api_key_env,
        "model": model,
        "timeout": timeout,
    }.items():
        if value is not None:
            values[key] = value
    if headers:
        values["headers"] = headers
    return values


def main(argv: list[str] | None = None) -> None:
    _configure_stdio_errors()
    parser = argparse.ArgumentParser(
        prog="supermedicine",
        description="SuperMedicine - 模块化医学科研 Agent 框架",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目；可选释放桌面 Exe")
    init_parser.add_argument("--dir", type=str, default=".", help="项目目录")
    init_parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="LLM provider（openai、anthropic 或自定义 OpenAI-compatible provider）",
    )
    init_parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="LLM provider BaseURL；也可使用 SM_LLM_BASE_URL",
    )
    init_parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="LLM provider API key；也可使用 SM_LLM_API_KEY 或 provider 专用环境变量",
    )
    init_parser.add_argument(
        "--model", type=str, default=None, help="默认 LLM model；也可使用 SM_LLM_MODEL"
    )
    init_parser.add_argument(
        "--release-exe",
        type=Path,
        default=None,
        help="初始化后将指定 Exe 释放到桌面；未提供时不会复制 Exe",
    )
    init_parser.add_argument(
        "--desktop-dir",
        type=Path,
        default=None,
        help="桌面目录覆盖；测试/CI 应使用临时目录或 --exe-dry-run 避免真实桌面写入",
    )
    init_parser.add_argument(
        "--exe-target-name",
        type=str,
        default=None,
        help="桌面 Exe 文件名；默认使用源文件名，自动规范为 .exe",
    )
    init_parser.add_argument(
        "--exe-overwrite",
        action="store_true",
        help="覆盖已存在的桌面 Exe；默认目标存在时跳过",
    )
    init_parser.add_argument(
        "--exe-dry-run", action="store_true", help="仅报告桌面 Exe 释放动作，不复制文件"
    )

    # Status 命令
    subparsers.add_parser("status", help="显示项目状态")

    subparsers.add_parser("diagnose", help="输出可安全分享的配置/LLM/审计诊断信息")

    permission_parser = subparsers.add_parser(
        "permission",
        help="查看/切换 CLI 文件访问权限模式",
        description="查看或切换文件访问权限模式；默认保守，完全访问模式必须显式确认。",
        epilog=PERMISSION_RISK_NOTICE,
    )
    permission_subparsers = permission_parser.add_subparsers(dest="permission_command")
    permission_subparsers.add_parser("status", help="查看当前权限模式与授权目录")
    permission_mode_parser = permission_subparsers.add_parser(
        "mode", help="切换权限模式：conservative 或 full"
    )
    permission_mode_parser.add_argument(
        "mode", choices=["conservative", "sandbox", "safe", "full"], help="目标权限模式"
    )
    permission_mode_parser.add_argument(
        "--confirm-full",
        action="store_true",
        help="显式确认切换到完全访问模式；仅使用当前用户/进程已有权限",
    )
    permission_mode_parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="禁止交互确认；切换 full 时必须提供 --confirm-full",
    )
    permission_authorize_parser = permission_subparsers.add_parser(
        "authorize", help="添加外部授权目录"
    )
    permission_authorize_parser.add_argument("path", type=str, help="要授权的目录路径")
    permission_revoke_parser = permission_subparsers.add_parser(
        "revoke", help="移除外部授权目录"
    )
    permission_revoke_parser.add_argument("path", type=str, help="要移除授权的目录路径")
    permission_subparsers.add_parser("roots", help="列出当前外部授权目录")

    # Test 命令
    subparsers.add_parser("test", help="运行测试")

    # TUI 命令
    tui_parser = subparsers.add_parser(
        "tui",
        help="启动中文 TUI 工作台",
        description="启动中文 TUI 工作台；M 打开菜单/选择视图，P 权限模式，Tab/Shift+Tab 移动焦点，Enter 提交或激活，? 帮助，F 最大化，Q 退出。数字 1-0 是普通输入，不直接切换视图。",
    )
    tui_parser.add_argument(
        "--dry-run", action="store_true", help="输出中文 TUI 就绪状态，不启动交互界面"
    )

    # Run 命令
    run_parser = subparsers.add_parser("run", help="执行任务")
    run_parser.add_argument("task", type=str, help="任务描述")
    run_parser.add_argument("--verbose", action="store_true", help="详细输出")
    run_parser.add_argument("--plugin", type=str, default=None, help="指定插件名称")
    run_parser.add_argument("--action", type=str, default=None, help="指定插件动作")
    run_parser.add_argument(
        "--params-json", type=str, default=None, help="JSON 对象格式的插件参数"
    )
    run_parser.add_argument(
        "--params-file", type=str, default=None, help="包含 JSON 对象插件参数的文件路径"
    )
    run_parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="显式工作区 slug ID（workspaces/<id>；不会读取 TUI 最近状态）",
    )

    experiment_parser = subparsers.add_parser("experiment", help="实验指导器命令")
    experiment_subparsers = experiment_parser.add_subparsers(dest="experiment_command")

    experiment_subparsers.add_parser("list", help="列出可用实验配置")

    experiment_context_parser = experiment_subparsers.add_parser(
        "context", help="显示注入 LLM 的实验配置上下文与编写规范"
    )
    experiment_context_parser.add_argument(
        "--protocol", type=str, default=None, help="可选实验协议 ID 或别名"
    )

    experiment_add_config_parser = experiment_subparsers.add_parser(
        "add-config", help="根据自然语言草稿或 JSON 新增实验配置"
    )
    experiment_add_config_parser.add_argument(
        "--instruction", type=str, default=None, help="用户自然语言实验配置需求"
    )
    experiment_add_config_parser.add_argument(
        "--config-json", type=str, default=None, help="已生成的实验配置 JSON 对象"
    )
    experiment_add_config_parser.add_argument(
        "--filename", type=str, default=None, help="保存到 plugins/experiments/ 的文件名"
    )
    experiment_add_config_parser.add_argument(
        "--overwrite", action="store_true", help="显式确认允许覆盖同名配置文件"
    )

    experiment_start_parser = experiment_subparsers.add_parser(
        "start", help="启动实验指导会话"
    )
    experiment_start_parser.add_argument(
        "--protocol", required=True, help="实验协议 ID 或别名"
    )
    experiment_start_parser.add_argument(
        "--session-id", type=str, default=None, help="可选会话 ID"
    )

    experiment_show_parser = experiment_subparsers.add_parser(
        "show", help="查看实验会话当前步骤/状态"
    )
    experiment_show_parser.add_argument(
        "--session-file", required=True, type=str, help="实验会话 JSON 文件"
    )

    experiment_submit_parser = experiment_subparsers.add_parser(
        "submit", help="提交当前步骤实验数据"
    )
    experiment_submit_parser.add_argument(
        "--session-file", required=True, type=str, help="实验会话 JSON 文件"
    )
    experiment_submit_parser.add_argument(
        "--step", required=True, type=str, help="当前步骤 ID"
    )
    experiment_submit_parser.add_argument(
        "--input-json", required=True, type=str, help="步骤输入 JSON 对象"
    )
    experiment_submit_parser.add_argument(
        "--calculate", action="store_true", help="触发支持的 WB 插件计算"
    )

    log_parser = subparsers.add_parser("log", help="日志报告命令")
    log_subparsers = log_parser.add_subparsers(dest="log_command")

    log_write_parser = log_subparsers.add_parser("write", help="写入日志报告")
    log_write_parser.add_argument("--message", required=True, type=str, help="日志消息")
    log_write_parser.add_argument(
        "--session-id", type=str, default=None, help="可选关联会话 ID"
    )
    log_subparsers.add_parser("list", help="列出日志报告")
    log_show_parser = log_subparsers.add_parser("show", help="查看指定日志报告")
    log_show_parser.add_argument(
        "--file", required=True, type=str, help="日志报告文件名"
    )

    # Workspace 命令
    workspace_parser = subparsers.add_parser(
        "workspace", help="管理 workspaces/<id> 显式 slug 工作区"
    )
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    workspace_init_parser = workspace_subparsers.add_parser("init", help="初始化工作区")
    workspace_init_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    workspace_init_parser.add_argument(
        "--name", type=str, default=None, help="显示名称"
    )

    workspace_subparsers.add_parser("list", help="列出工作区")

    workspace_show_parser = workspace_subparsers.add_parser("show", help="显示工作区")
    workspace_show_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )

    workspace_delete_parser = workspace_subparsers.add_parser(
        "delete",
        help="硬删除工作区（需强确认、权限与审计）",
        description="硬删除指定工作区；执行前会进行权限检查并写入审计记录。",
        epilog="必须提供 --confirm，且其值必须与 --workspace 完全一致。",
    )
    workspace_delete_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    workspace_delete_parser.add_argument(
        "--confirm", required=True, type=str, help="必须与工作区 ID 完全一致"
    )

    # Tool 命令（全部要求显式 --workspace；不会读取 TUI 最近状态）
    tool_parser = subparsers.add_parser("tool", help="管理工作区内 Python/R 模块化工具")
    tool_subparsers = tool_parser.add_subparsers(dest="tool_command")

    tool_init_parser = tool_subparsers.add_parser("init", help="初始化工作区工具目录")
    tool_init_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )

    tool_list_parser = tool_subparsers.add_parser("list", help="列出工作区工具")
    tool_list_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    tool_list_parser.add_argument(
        "--language", choices=["python", "r"], default=None, help="可选语言过滤"
    )

    tool_scan_parser = tool_subparsers.add_parser(
        "scan", help="自动扫描可导入的 Python/R 工具候选列表"
    )
    tool_scan_parser.add_argument(
        "--language", choices=["python", "r"], default=None, help="可选语言过滤"
    )

    tool_add_parser = tool_subparsers.add_parser(
        "add",
        help="从自动扫描候选列表选择导入工具",
        description="先扫描 plugins/tools 下 Python/R 工具目录并展示候选；使用 --select 选择编号或显示的 language/id 导入，不需要输入未知工具 ID。",
    )
    tool_add_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    tool_add_parser.add_argument(
        "--language", choices=["python", "r"], default=None, help="可选语言过滤"
    )
    tool_add_parser.add_argument(
        "--select",
        action="append",
        default=None,
        help="从扫描候选列表选择编号或 language/id；可重复选择多个工具",
    )
    tool_add_parser.add_argument(
        "--overwrite", action="store_true", help="覆盖工作区中同名已导入工具"
    )

    tool_show_parser = tool_subparsers.add_parser("show", help="显示工具清单")
    tool_show_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    tool_show_parser.add_argument(
        "--language", required=True, choices=["python", "r"], help="工具语言"
    )
    tool_show_parser.add_argument("--tool", required=True, type=str, help="工具 ID")

    tool_run_parser = tool_subparsers.add_parser(
        "run", help="准备工具运行命令（安全基础默认不执行脚本）"
    )
    tool_run_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    tool_run_parser.add_argument(
        "--language", required=True, choices=["python", "r"], help="工具语言"
    )
    tool_run_parser.add_argument("--tool", required=True, type=str, help="工具 ID")
    tool_run_parser.add_argument(
        "--dry-run", action="store_true", help="只输出准备好的命令"
    )
    tool_run_parser.add_argument(
        "--input", type=str, default=None, help="工作区内输入路径"
    )
    tool_run_parser.add_argument(
        "--output", type=str, default=None, help="工作区内输出路径"
    )

    # LLM 命令
    llm_parser = subparsers.add_parser("llm", help="管理 LLM API provider")
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command")

    llm_add_parser = llm_subparsers.add_parser(
        "add", help="添加或更新 LLM API provider"
    )
    llm_add_parser.add_argument("provider", type=str, help="Provider 名称")
    llm_add_parser.add_argument(
        "--api-format", type=str, default=None, help="API 格式，如 openai 或 anthropic"
    )
    llm_add_parser.add_argument(
        "--base-url", type=str, default=None, help="Provider Base URL"
    )
    llm_add_parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key；输出默认脱敏。推荐改用 --api-key-env",
    )
    llm_add_parser.add_argument(
        "--api-key-env",
        type=str,
        default=None,
        help="读取 API key 的环境变量名；可避免命令行明文 key",
    )
    llm_add_parser.add_argument("--model", type=str, default=None, help="默认模型")
    llm_add_parser.add_argument(
        "--timeout", type=float, default=None, help="请求超时秒数"
    )
    llm_add_parser.add_argument(
        "--header", action="append", default=None, help="额外请求头 KEY=VALUE；可重复"
    )
    llm_add_parser.add_argument(
        "--headers-json", type=str, default=None, help="额外请求头 JSON 对象"
    )
    llm_add_parser.add_argument(
        "--set-current", action="store_true", help="添加后立即切换为当前默认 provider"
    )

    llm_subparsers.add_parser("list", help="列出 LLM provider（默认脱敏）")

    llm_show_parser = llm_subparsers.add_parser(
        "show", help="显示当前或指定 LLM provider（默认脱敏）"
    )
    llm_show_parser.add_argument(
        "provider",
        nargs="?",
        default=None,
        help="可选 Provider 名称；缺省显示当前默认 provider",
    )

    llm_switch_parser = llm_subparsers.add_parser(
        "switch", help="切换当前默认 LLM provider 并持久化"
    )
    llm_switch_parser.add_argument("provider", type=str, help="Provider 名称")

    # Paper 命令（全部要求显式 --workspace；不会读取 TUI 最近状态）
    paper_parser = subparsers.add_parser("paper", help="管理工作区论文导入与元数据")
    paper_subparsers = paper_parser.add_subparsers(dest="paper_command")

    paper_import_parser = paper_subparsers.add_parser(
        "import",
        help="复制导入本地论文文件（PDF/TeX/BibTeX/RIS/TXT/MD）",
        description="复制导入本地论文文件到显式工作区；支持格式：PDF、TeX、BibTeX、RIS、TXT、MD。",
        epilog="默认不联网；如需在线/外部元数据补全，请同时使用 --enrich 与 --confirm-enrich。",
    )
    paper_import_parser.add_argument("path", type=str, help="本地论文文件路径")
    paper_import_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    paper_import_parser.add_argument("--title", type=str, default=None, help="论文标题")
    paper_import_parser.add_argument("--doi", type=str, default=None, help="DOI")
    paper_import_parser.add_argument("--pmid", type=str, default=None, help="PMID")
    paper_import_parser.add_argument("--notes", type=str, default=None, help="备注")
    paper_import_parser.add_argument(
        "--tag", action="append", default=None, help="标签，可重复"
    )
    paper_import_parser.add_argument(
        "--enrich", action="store_true", help="请求在线/外部元数据补全（默认不联网）"
    )
    paper_import_parser.add_argument(
        "--confirm-enrich",
        action="store_true",
        help="显式确认允许发起补全授权检查、网络/API 限制检查与审计",
    )

    paper_list_parser = paper_subparsers.add_parser("list", help="列出工作区论文")
    paper_list_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )

    paper_show_parser = paper_subparsers.add_parser("show", help="显示论文元数据")
    paper_show_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_show_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )

    paper_edit_parser = paper_subparsers.add_parser("edit", help="编辑论文元数据")
    paper_edit_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_edit_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    paper_edit_parser.add_argument("--title", type=str, default=None, help="论文标题")
    paper_edit_parser.add_argument("--doi", type=str, default=None, help="DOI")
    paper_edit_parser.add_argument("--pmid", type=str, default=None, help="PMID")
    paper_edit_parser.add_argument("--notes", type=str, default=None, help="备注")
    paper_edit_parser.add_argument(
        "--tag", action="append", default=None, help="标签，可重复"
    )

    paper_enrich_parser = paper_subparsers.add_parser(
        "enrich",
        help="补全论文元数据",
        description="通过网络/API 补全论文元数据；执行前会进行授权、网络/API 限制检查并写入审计记录。",
        epilog="必须提供 --confirm-enrich 显式确认允许外部元数据补全。",
    )
    paper_enrich_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_enrich_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    paper_enrich_parser.add_argument(
        "--confirm-enrich",
        action="store_true",
        required=True,
        help="显式确认允许发起补全授权检查、网络/API 限制检查与审计",
    )

    # Experience 命令（全部要求显式 --workspace；建议不会持久化）
    experience_parser = subparsers.add_parser(
        "experience",
        help="管理确认后的经验记录（不存原始对话）",
        description="管理确认后的经验记录；只保存摘要、标签等结构化内容，不存原始对话。",
    )
    experience_subparsers = experience_parser.add_subparsers(dest="experience_command")

    experience_suggest_parser = experience_subparsers.add_parser(
        "suggest", help="建议分类但不写入"
    )
    experience_suggest_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_suggest_parser.add_argument(
        "--title", type=str, default=None, help="经验标题"
    )
    experience_suggest_parser.add_argument(
        "--summary", required=True, type=str, help="经验摘要"
    )
    experience_suggest_parser.add_argument(
        "--tag", action="append", default=None, help="标签，可重复"
    )

    experience_add_parser = experience_subparsers.add_parser(
        "add", help="确认并新增经验"
    )
    experience_add_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_add_parser.add_argument(
        "--scope",
        required=True,
        choices=["general", "workspace"],
        help="确认后的存储范围",
    )
    experience_add_parser.add_argument(
        "--title", required=True, type=str, help="经验标题"
    )
    experience_add_parser.add_argument(
        "--summary", required=True, type=str, help="经验摘要"
    )
    experience_add_parser.add_argument(
        "--tag", action="append", default=None, help="标签，可重复"
    )
    experience_add_parser.add_argument(
        "--confirm", action="store_true", required=True, help="显式确认写入"
    )

    experience_list_parser = experience_subparsers.add_parser("list", help="列出经验")
    experience_list_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_list_parser.add_argument(
        "--include-general", action="store_true", help="包含通用方法层"
    )

    experience_view_parser = experience_subparsers.add_parser("view", help="查看经验")
    experience_view_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_view_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_view_parser.add_argument(
        "--scope", choices=["general", "workspace"], default=None, help="范围过滤"
    )

    experience_edit_parser = experience_subparsers.add_parser("edit", help="编辑经验")
    experience_edit_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_edit_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_edit_parser.add_argument(
        "--scope", required=True, choices=["general", "workspace"], help="经验范围"
    )
    experience_edit_parser.add_argument(
        "--title", type=str, default=None, help="经验标题"
    )
    experience_edit_parser.add_argument(
        "--summary", type=str, default=None, help="经验摘要"
    )
    experience_edit_parser.add_argument(
        "--tag", action="append", default=None, help="标签，可重复；提供后替换原标签"
    )

    experience_delete_parser = experience_subparsers.add_parser(
        "delete", help="删除经验"
    )
    experience_delete_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_delete_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_delete_parser.add_argument(
        "--scope", required=True, choices=["general", "workspace"], help="经验范围"
    )
    experience_delete_parser.add_argument(
        "--confirm", required=True, type=str, help="必须与经验 ID 完全一致"
    )

    experience_export_parser = experience_subparsers.add_parser(
        "export", help="导出经验"
    )
    experience_export_parser.add_argument(
        "--workspace", required=True, type=str, help="工作区 ID"
    )
    experience_export_parser.add_argument(
        "--format", required=True, choices=["json", "md"], help="导出格式"
    )
    experience_export_parser.add_argument(
        "--include-general", action="store_true", help="包含通用方法层"
    )
    experience_export_parser.add_argument(
        "--output", type=str, default=None, help="可选 UTF-8 输出文件"
    )

    args = parser.parse_args(argv)
    if args.command != "tui":
        _configure_cli_logging()
    cli = CLI()

    if args.command == "init":
        from installer.entrypoint import (
            _normalize_provider,
            _resolve_api_key,
            _resolve_install_value,
        )

        provider = _resolve_install_value("provider", args.provider)
        base_url = _resolve_install_value("base_url", args.base_url)
        model = _resolve_install_value("model", args.model)
        normalized_provider = _normalize_provider(provider)
        api_key = _resolve_api_key(normalized_provider, args.api_key)
        try:
            cli.init(
                Path(args.dir),
                provider=normalized_provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
                release_exe=args.release_exe,
                desktop_dir=args.desktop_dir,
                exe_target_name=args.exe_target_name,
                exe_overwrite=args.exe_overwrite,
                exe_dry_run=args.exe_dry_run,
            )
        except (ValueError, FileNotFoundError, OSError) as exc:
            init_parser.error(str(exc))
    elif args.command == "status":
        cli.status()
    elif args.command == "diagnose":
        cli.diagnose()
    elif args.command == "permission":
        try:
            if args.permission_command == "status":
                cli.permission_status()
            elif args.permission_command == "mode":
                cli.permission_set_mode(
                    args.mode,
                    confirm_full=args.confirm_full,
                    interactive=not args.no_interactive,
                )
            elif args.permission_command == "authorize":
                cli.permission_authorize(args.path)
            elif args.permission_command == "revoke":
                cli.permission_revoke(args.path)
            elif args.permission_command == "roots":
                cli.permission_status()
            else:
                permission_parser.print_help()
        except (ValueError, PermissionError) as exc:
            permission_parser.error(str(exc))
    elif args.command == "test":
        cli.test()
    elif args.command == "tui":
        cli.tui(dry_run=args.dry_run)
    elif args.command == "run":
        verbose = getattr(args, "verbose", False)
        try:
            params = _resolve_run_params(args.params_json, args.params_file)
        except ValueError as exc:
            run_parser.error(str(exc))
        cli.run(
            args.task,
            verbose=verbose,
            plugin=args.plugin,
            action=args.action,
            params=params,
            workspace=args.workspace,
        )
    elif args.command == "experiment":
        try:
            if args.experiment_command == "start":
                cli.experiment_start(args.protocol, session_id=args.session_id)
            elif args.experiment_command == "list":
                cli.experiment_list()
            elif args.experiment_command == "context":
                cli.experiment_context(args.protocol)
            elif args.experiment_command == "add-config":
                cli.experiment_add_config(
                    instruction=args.instruction,
                    config_json=args.config_json,
                    filename=args.filename,
                    overwrite=args.overwrite,
                )
            elif args.experiment_command == "show":
                cli.experiment_show(args.session_file)
            elif args.experiment_command == "submit":
                cli.experiment_submit(
                    args.session_file,
                    args.step,
                    args.input_json,
                    calculate=args.calculate,
                )
            else:
                experiment_parser.print_help()
        except (KeyError, ValueError) as exc:
            experiment_parser.error(str(exc))
    elif args.command == "log":
        try:
            if args.log_command == "write":
                cli.log_write(args.message, session_id=args.session_id)
            elif args.log_command == "list":
                cli.log_list()
            elif args.log_command == "show":
                cli.log_show(args.file)
            else:
                log_parser.print_help()
        except ValueError as exc:
            log_parser.error(str(exc))
    elif args.command == "workspace":
        if args.workspace_command == "init":
            cli.workspace_init(args.workspace, name=args.name)
        elif args.workspace_command == "list":
            cli.workspace_list()
        elif args.workspace_command == "show":
            cli.workspace_show(args.workspace)
        elif args.workspace_command == "delete":
            try:
                cli.workspace_delete(args.workspace, args.confirm)
            except ValueError as exc:
                workspace_delete_parser.error(str(exc))
        else:
            workspace_parser.print_help()
    elif args.command == "tool":
        if args.tool_command == "init":
            cli.tool_init(args.workspace)
        elif args.tool_command == "list":
            cli.tool_list(args.workspace, language=args.language)
        elif args.tool_command == "scan":
            cli.tool_scan(language=args.language)
        elif args.tool_command == "add":
            try:
                cli.tool_add(
                    args.workspace,
                    selections=args.select,
                    language=args.language,
                    overwrite=args.overwrite,
                )
            except ValueError as exc:
                tool_add_parser.error(str(exc))
        elif args.tool_command == "show":
            cli.tool_show(args.workspace, args.language, args.tool)
        elif args.tool_command == "run":
            cli.tool_run(
                args.workspace,
                args.language,
                args.tool,
                dry_run=args.dry_run,
                input_path=args.input,
                output_path=args.output,
            )
        else:
            tool_parser.print_help()
    elif args.command == "llm":
        try:
            if args.llm_command == "add":
                headers = _parse_llm_headers(args.header, args.headers_json)
                cli.llm_add(
                    args.provider,
                    api_format=args.api_format,
                    base_url=args.base_url,
                    api_key=args.api_key,
                    api_key_env=args.api_key_env,
                    model=args.model,
                    timeout=args.timeout,
                    headers=headers,
                    set_current=args.set_current,
                )
            elif args.llm_command == "list":
                cli.llm_list()
            elif args.llm_command == "show":
                cli.llm_show(args.provider)
            elif args.llm_command == "switch":
                cli.llm_switch(args.provider)
            else:
                llm_parser.print_help()
        except ValueError as exc:
            llm_parser.error(str(exc))
    elif args.command == "paper":
        if args.paper_command == "import":
            cli.paper_import(
                args.workspace,
                args.path,
                metadata=_paper_metadata_options(args),
                enrich=args.enrich,
                confirm_enrich=args.confirm_enrich,
            )
        elif args.paper_command == "list":
            cli.paper_list(args.workspace)
        elif args.paper_command == "show":
            cli.paper_show(args.workspace, args.paper_id)
        elif args.paper_command == "edit":
            cli.paper_edit(args.workspace, args.paper_id, _paper_metadata_options(args))
        elif args.paper_command == "enrich":
            cli.paper_enrich(args.workspace, args.paper_id, args.confirm_enrich)
        else:
            paper_parser.print_help()
    elif args.command == "experience":
        try:
            if args.experience_command == "suggest":
                cli.experience_suggest(
                    args.workspace, args.summary, title=args.title, tags=args.tag
                )
            elif args.experience_command == "add":
                cli.experience_add(
                    args.workspace,
                    args.scope,
                    args.title,
                    args.summary,
                    tags=args.tag,
                    confirm=args.confirm,
                )
            elif args.experience_command == "list":
                cli.experience_list(
                    args.workspace, include_general=args.include_general
                )
            elif args.experience_command == "view":
                cli.experience_view(args.record_id, args.workspace, scope=args.scope)
            elif args.experience_command == "edit":
                cli.experience_edit(
                    args.record_id,
                    args.workspace,
                    args.scope,
                    title=args.title,
                    summary=args.summary,
                    tags=args.tag,
                )
            elif args.experience_command == "delete":
                cli.experience_delete(
                    args.record_id, args.workspace, args.scope, args.confirm
                )
            elif args.experience_command == "export":
                cli.experience_export(
                    args.workspace,
                    args.format,
                    include_general=args.include_general,
                    output=args.output,
                )
            else:
                experience_parser.print_help()
        except ValueError as exc:
            experience_parser.error(str(exc))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
