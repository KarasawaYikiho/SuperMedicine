#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""

from __future__ import annotations

import logging
import sys
from importlib import import_module
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


_FORWARDED_COMMAND_GROUPS = {
    "cli.commands.workspace": ("workspace_init", "workspace_list", "workspace_show", "workspace_delete"),
    "cli.commands.tool": ("tool_init", "tool_list", "tool_scan", "tool_add", "tool_show", "tool_run"),
    "cli.commands.llm": ("llm_add", "llm_list", "llm_show", "llm_switch"),
    "cli.commands.permission": ("permission_status", "permission_set_mode", "permission_authorize", "permission_revoke"),
    "cli.commands.self_evolve": ("self_evolve",),
    "cli.commands.paper": ("paper_import", "paper_list", "paper_show", "paper_edit", "paper_enrich"),
    "cli.commands.experience": ("experience_suggest", "experience_add", "experience_list", "experience_view", "experience_edit", "experience_delete", "experience_export"),
    "cli.commands.experiment": ("experiment_start", "experiment_list", "experiment_context", "experiment_add_config", "experiment_show", "experiment_submit"),
    "cli.commands.log": ("log_write", "log_list", "log_show", "log_location", "log_follow"),
}

_FORWARDED_COMMANDS = {
    command: (module, command)
    for module, commands in _FORWARDED_COMMAND_GROUPS.items()
    for command in commands
}


class CLI:
    """SuperMedicine CLI"""

    def __getattr__(self, name: str):
        try:
            module_name, function_name = _FORWARDED_COMMANDS[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

        def forwarded(*args, **kwargs):
            return getattr(import_module(module_name), function_name)(
                self, *args, **kwargs
            )

        return forwarded

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
