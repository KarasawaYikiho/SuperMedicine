#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from core.redaction import redact_sensitive

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from cli.logging_setup import (  # noqa: E402
    _log_json,
)


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
        logger.info("SuperMedicine Beta0.4.2")
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
        from permission.policy import ensure_default_policy
        from core.workspace import WorkspaceManager

        # 确定项目根目录
        project_dir = Path.cwd()

        logger.info("SuperMedicine Beta0.4.2 — 任务执行")
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
        ensure_default_policy(project_dir)

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
        from cli.commands.workspace import workspace_init

        return workspace_init(self, workspace_id, name=name)

    def workspace_list(self) -> list[dict]:
        """List initialized workspaces without consulting recent TUI state."""
        from cli.commands.workspace import workspace_list

        return workspace_list(self)

    def workspace_show(self, workspace_id: str) -> dict:
        """Show one explicitly requested workspace."""
        from cli.commands.workspace import workspace_show

        return workspace_show(self, workspace_id)

    def workspace_delete(self, workspace_id: str, confirm: str) -> dict:
        """Hard-delete an explicitly confirmed workspace after guard approval."""
        from cli.commands.workspace import workspace_delete

        return workspace_delete(self, workspace_id, confirm)

    def tool_init(self, workspace_id: str) -> dict:
        """Initialize workspace-local Python/R tool directories."""
        from cli.commands.tool import tool_init

        return tool_init(self, workspace_id)

    def tool_list(self, workspace_id: str, language: str | None = None) -> dict:
        """List workspace-local tools grouped by language."""
        from cli.commands.tool import tool_list

        return tool_list(self, workspace_id, language=language)

    def tool_scan(self, language: str | None = None) -> dict:
        """Scan Python/R source tool directories for selectable import candidates."""
        from cli.commands.tool import tool_scan

        return tool_scan(self, language=language)

    def tool_add(
        self,
        workspace_id: str,
        selections: list[str] | None = None,
        *,
        language: str | None = None,
        overwrite: bool = False,
    ) -> dict:
        """Import scanned Python/R tools selected from the candidate list."""
        from cli.commands.tool import tool_add

        return tool_add(self, workspace_id, selections, language=language, overwrite=overwrite)

    def tool_show(self, workspace_id: str, language: str, tool_id: str) -> dict:
        """Show one workspace-local tool manifest."""
        from cli.commands.tool import tool_show

        return tool_show(self, workspace_id, language, tool_id)

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
        from cli.commands.tool import tool_run

        return tool_run(self, workspace_id, language, tool_id, dry_run=dry_run, input_path=input_path, output_path=output_path)

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
        from cli.commands.llm import llm_add

        return llm_add(self, provider, api_format=api_format, base_url=base_url, api_key=api_key, api_key_env=api_key_env, model=model, timeout=timeout, headers=headers, set_current=set_current)

    def llm_list(self) -> dict:
        """List configured LLM providers with secret-safe output."""
        from cli.commands.llm import llm_list

        return llm_list(self)

    def llm_show(self, provider: str | None = None) -> dict:
        """Show one LLM provider, defaulting to the current provider, redacted."""
        from cli.commands.llm import llm_show

        return llm_show(self, provider)

    def llm_switch(self, provider: str) -> dict:
        """Persistently switch the current LLM provider."""
        from cli.commands.llm import llm_switch

        return llm_switch(self, provider)

    def permission_status(self) -> dict[str, Any]:
        """Show current CLI file access mode and authorized external roots."""
        from cli.commands.permission import permission_status

        return permission_status(self)

    def permission_set_mode(
        self,
        mode: str,
        *,
        confirm_full: bool = False,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Persistently switch CLI file access mode without privilege escalation."""
        from cli.commands.permission import permission_set_mode

        return permission_set_mode(self, mode, confirm_full=confirm_full, interactive=interactive)

    def permission_authorize(self, path: str | Path) -> dict[str, Any]:
        """Persistently authorize an external directory for conservative mode."""
        from cli.commands.permission import permission_authorize

        return permission_authorize(self, path)

    def permission_revoke(self, path: str | Path) -> dict[str, Any]:
        """Persistently remove an external directory authorization."""
        from cli.commands.permission import permission_revoke

        return permission_revoke(self, path)

    def self_evolve(
        self,
        *,
        instruction: str,
        artifact_type: str,
        output: str | Path,
        access_mode: str = "sandbox",
        experience_source: str | None = None,
        workspace: str | None = None,
        preview: bool = True,
        confirm_write: bool = False,
        overwrite: bool = False,
        confirm_full_access: bool = False,
        acknowledge_risk: bool = False,
    ) -> dict[str, Any]:
        """Generate a self-evolution preview or confirmed artifact write."""
        from cli.commands.self_evolve import self_evolve

        return self_evolve(
            self,
            instruction=instruction,
            artifact_type=artifact_type,
            output=output,
            access_mode=access_mode,
            experience_source=experience_source,
            workspace=workspace,
            preview=preview,
            confirm_write=confirm_write,
            overwrite=overwrite,
            confirm_full_access=confirm_full_access,
            acknowledge_risk=acknowledge_risk,
        )

    def diagnose(self) -> dict:
        """Print secret-safe diagnostics for config, LLM, install artifacts, and audit log."""
        from core.config_center import ConfigCenter
        from core.llm_manager import LLMConfigManager
        from core.log_report import resolve_log_storage_locations

        project_dir = Path.cwd()
        config = ConfigCenter(project_dir / ".supermedicine" / "config.yaml")
        manager = LLMConfigManager(config, restore_on_startup=False)
        storage_locations = resolve_log_storage_locations(project_dir)
        audit_log = storage_locations.audit_file
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
            "log_storage": storage_locations.to_dict(),
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
        from cli.commands.paper import paper_import

        return paper_import(self, workspace_id, source_path, metadata=metadata, enrich=enrich, confirm_enrich=confirm_enrich)

    def paper_list(self, workspace_id: str) -> list[dict]:
        """List papers from an explicitly selected workspace."""
        from cli.commands.paper import paper_list

        return paper_list(self, workspace_id)

    def paper_show(self, workspace_id: str, paper_id: str) -> dict:
        """Show one imported paper from an explicitly selected workspace."""
        from cli.commands.paper import paper_show

        return paper_show(self, workspace_id, paper_id)

    def paper_edit(self, workspace_id: str, paper_id: str, metadata: dict) -> dict:
        """Edit metadata for one imported paper from an explicit workspace."""
        from cli.commands.paper import paper_edit

        return paper_edit(self, workspace_id, paper_id, metadata)

    def paper_enrich(
        self, workspace_id: str, paper_id: str, confirm_enrich: bool
    ) -> dict:
        """Enrich one imported paper after explicit confirmation and permission approval."""
        from cli.commands.paper import paper_enrich

        return paper_enrich(self, workspace_id, paper_id, confirm_enrich)

    def experience_suggest(
        self,
        workspace_id: str,
        summary: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Suggest an experience classification without persisting anything."""
        from cli.commands.experience import experience_suggest

        return experience_suggest(self, workspace_id, summary, title=title, tags=tags)

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
        from cli.commands.experience import experience_add

        return experience_add(self, workspace_id, scope, title, summary, tags=tags, confirm=confirm)

    def experience_list(
        self, workspace_id: str, include_general: bool = False
    ) -> list[dict]:
        """List experiences visible from an explicit workspace context."""
        from cli.commands.experience import experience_list

        return experience_list(self, workspace_id, include_general=include_general)

    def experience_view(
        self, record_id: str, workspace_id: str, scope: str | None = None
    ) -> dict:
        """View one visible experience by id."""
        from cli.commands.experience import experience_view

        return experience_view(self, record_id, workspace_id, scope=scope)

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
        from cli.commands.experience import experience_edit

        return experience_edit(self, record_id, workspace_id, scope, title=title, summary=summary, tags=tags)

    def experience_delete(
        self, record_id: str, workspace_id: str, scope: str, confirm: str
    ) -> dict:
        """Delete one experience after exact id confirmation."""
        from cli.commands.experience import experience_delete

        return experience_delete(self, record_id, workspace_id, scope, confirm)

    def experience_export(
        self,
        workspace_id: str,
        format: str,
        include_general: bool = False,
        output: str | None = None,
    ) -> str:
        """Export visible experiences as JSON or Markdown."""
        from cli.commands.experience import experience_export

        return experience_export(self, workspace_id, format, include_general=include_general, output=output)

    def experiment_start(self, protocol: str, session_id: str | None = None) -> dict:
        """Start a standalone experiment guide session and persist it as JSON."""
        from cli.commands.experiment import experiment_start

        return experiment_start(self, protocol, session_id=session_id)

    def experiment_list(self) -> list[dict]:
        """List configured experiment protocols discovered from plugins/experiments."""
        from cli.commands.experiment import experiment_list

        return experiment_list(self)

    def experiment_context(self, protocol: str | None = None) -> dict:
        """Show the experiment context and authoring rules injected into LLM chat."""
        from cli.commands.experiment import experiment_context

        return experiment_context(self, protocol)

    def experiment_add_config(
        self,
        *,
        instruction: str | None = None,
        config_json: str | None = None,
        filename: str | None = None,
        overwrite: bool = False,
    ) -> dict:
        """Draft/validate and save a new experiment config in plugins/experiments."""
        from cli.commands.experiment import experiment_add_config

        return experiment_add_config(self, instruction=instruction, config_json=config_json, filename=filename, overwrite=overwrite)

    def experiment_show(self, session_file: str | Path) -> dict:
        """Show a persisted experiment guide session."""
        from cli.commands.experiment import experiment_show

        return experiment_show(self, session_file)

    def experiment_submit(
        self,
        session_file: str | Path,
        step_id: str,
        input_json: str,
        *,
        calculate: bool = False,
    ) -> dict:
        """Submit data for the current experiment step, optionally running a configured calculation."""
        from cli.commands.experiment import experiment_submit

        return experiment_submit(self, session_file, step_id, input_json, calculate=calculate)

    def log_write(self, message: str, session_id: str | None = None) -> dict:
        """Write a redacted log report."""
        from cli.commands.log import log_write

        return log_write(self, message, session_id=session_id)

    def log_list(self) -> list[dict]:
        """List redacted log report summaries."""
        from cli.commands.log import log_list

        return log_list(self)

    def log_show(self, file_name: str) -> dict:
        """Show a redacted log report."""
        from cli.commands.log import log_show

        return log_show(self, file_name)

    def log_location(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> dict:
        """Show redacted log/report/audit storage locations."""
        from cli.commands.log import log_location

        return log_location(self, file_name=file_name, session_id=session_id)

    def log_follow(
        self,
        *,
        file_name: str | None = None,
        session_id: str | None = None,
        interval: float = 1.0,
        max_entries: int = 50,
        max_lines: int | None = None,
        iterations: int | None = None,
        once: bool = False,
        no_clear: bool = False,
    ) -> dict:
        """Show a realtime/tail-style redacted log view with test-safe exit controls."""
        from cli.commands.log import log_follow

        return log_follow(
            self,
            file_name=file_name,
            session_id=session_id,
            interval=interval,
            max_entries=max_entries,
            max_lines=max_lines,
            iterations=iterations,
            once=once,
            no_clear=no_clear,
        )

    def tui(self, dry_run: bool = False):
        """启动中文 TUI 工作台；不会改变 CLI 默认工作区行为。"""
        from core.tui.app import launch_tui

        # In frozen mode, let launch_tui resolve the project root by
        # checking the executable's directory first (for .supermedicine
        # config), falling back to cwd.  In development mode, always use cwd.
        if getattr(sys, "frozen", False):
            return launch_tui(dry_run=dry_run)
        return launch_tui(dry_run=dry_run, project_root=Path.cwd())

    def web(self, host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
        """Start web interface.

        Requires optional web dependencies: ``pip install supermedicine[web]``
        """
        from core.web.server import start_server

        start_server(host, port, reload=reload)


from cli.parser import main  # noqa: E402

if __name__ == "__main__":
    main()
