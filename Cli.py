#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from core.serialization import json_ready

if TYPE_CHECKING:
    from core.experience import ExperienceScope, ExportFormat

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))



class CLI:
    """SuperMedicine CLI"""

    def __init__(self) -> None:
        self.kernel = None
        self.orchestrator = None

    def init(self, project_dir: Path) -> None:
        """初始化项目"""
        from permission.policy import ensure_default_policy
        from Install import _default_config_text

        config_dir = project_dir / ".supermedicine"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.yaml").write_text(
            _default_config_text(),
            encoding="utf-8",
        )
        (config_dir / "agents").mkdir(exist_ok=True)
        (config_dir / "plugins").mkdir(exist_ok=True)
        ensure_default_policy(project_dir, Path(__file__).parent)
        logger.info("项目已初始化: %s", config_dir)

    def status(self) -> None:
        """显示项目状态"""
        logger.info("SuperMedicine Beta0.3.0")
        logger.info("=" * 40)

        # 检查配置
        config_dir = Path.cwd() / ".supermedicine"
        if config_dir.exists():
            logger.info("[OK] 项目配置已初始化")
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

        logger.info("SuperMedicine Beta0.3.0 — 任务执行")
        logger.info("任务: %s", task)
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

        result = kernel.execute_task(task, plugin_name=plugin, action=action, params=execution_params)
        if verbose:
            logger.info(
                "[STATE] agent=%s task=%s plugin=%s action=%s status=%s",
                result.get("agent", "alpha"),
                result.get("task", task),
                result.get("plugin"),
                result.get("action"),
                result.get("status"),
            )
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def workspace_list(self) -> list[dict]:
        """List initialized workspaces without consulting recent TUI state."""
        from core.workspace import WorkspaceManager

        workspaces = [
            _workspace_info_to_dict(info)
            for info in WorkspaceManager(Path.cwd()).list_workspaces()
        ]
        logger.info(json.dumps(workspaces, ensure_ascii=False, indent=2))
        return workspaces

    def workspace_show(self, workspace_id: str) -> dict:
        """Show one explicitly requested workspace."""
        from core.workspace import WorkspaceManager

        info = WorkspaceManager(Path.cwd()).get_workspace(workspace_id)
        result = _workspace_info_to_dict(info)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def tool_init(self, workspace_id: str) -> dict:
        """Initialize workspace-local Python/R tool directories."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).initialize_tools(workspace_id)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def tool_list(self, workspace_id: str, language: str | None = None) -> dict:
        """List workspace-local tools grouped by language."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).list_tools(workspace_id, language=language)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def tool_add(self, workspace_id: str, language: str, tool_id: str) -> dict:
        """Scaffold a built-in workspace-local tool."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).add_builtin_tool(workspace_id, language, tool_id)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def tool_show(self, workspace_id: str, language: str, tool_id: str) -> dict:
        """Show one workspace-local tool manifest."""
        from core.workspace_tools import WorkspaceToolService

        result = WorkspaceToolService(Path.cwd()).show_tool(workspace_id, language, tool_id)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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

        result = WorkspaceToolService(Path.cwd()).prepare_invocation(
            workspace_id,
            language,
            tool_id,
            dry_run=dry_run,
            input_path=input_path,
            output_path=output_path,
        ).to_dict()
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
                PermissionEngine(project_dir / ".supermedicine" / "policies", audit_log),
                AuditLogger(audit_log),
            )
            enrichment_result = enricher.enrich(import_result.metadata, confirmed=confirm_enrich)
            if enrichment_result.status == "enriched":
                importer.save_paper_metadata(workspace_id, enrichment_result.metadata)
            if enrichment_result.warning:
                warnings.append(enrichment_result.warning)

        result = _paper_import_result_to_dict(import_result, warnings=warnings)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def paper_list(self, workspace_id: str) -> list[dict]:
        """List papers from an explicitly selected workspace."""
        from core.paper_import.importer import PaperImporter

        papers = [_paper_metadata_to_dict(paper) for paper in PaperImporter(Path.cwd()).list_papers(workspace_id)]
        logger.info(json.dumps(papers, ensure_ascii=False, indent=2))
        return papers

    def paper_show(self, workspace_id: str, paper_id: str) -> dict:
        """Show one imported paper from an explicitly selected workspace."""
        from core.paper_import.importer import PaperImporter

        result = _paper_metadata_to_dict(PaperImporter(Path.cwd()).get_paper(workspace_id, paper_id))
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def paper_edit(self, workspace_id: str, paper_id: str, metadata: dict) -> dict:
        """Edit metadata for one imported paper from an explicit workspace."""
        from core.paper_import.importer import PaperImporter

        result = _paper_metadata_to_dict(
            PaperImporter(Path.cwd()).update_paper_metadata(workspace_id, paper_id, metadata)
        )
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def paper_enrich(self, workspace_id: str, paper_id: str, confirm_enrich: bool) -> dict:
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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

        result = ExperienceStore(Path.cwd()).suggest_classification(
            workspace_id=workspace_id,
            title=title,
            summary=summary,
            tags=tags,
        ).to_dict()
        result["workspace_id"] = workspace_id
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def experience_list(self, workspace_id: str, include_general: bool = False) -> list[dict]:
        """List experiences visible from an explicit workspace context."""
        from core.experience import ExperienceStore

        records = [record.to_dict() for record in ExperienceStore(Path.cwd()).list_experiences(
            workspace_id,
            include_general=include_general,
        )]
        logger.info(json.dumps(records, ensure_ascii=False, indent=2))
        return records

    def experience_view(self, record_id: str, workspace_id: str, scope: str | None = None) -> dict:
        """View one visible experience by id."""
        from core.experience import ExperienceStore

        experience_scope = _as_optional_experience_scope(scope)
        record = ExperienceStore(Path.cwd()).get_experience(
            record_id,
            workspace_id=workspace_id,
            scope=experience_scope,
        )
        result = record.to_dict()
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def experience_delete(self, record_id: str, workspace_id: str, scope: str, confirm: str) -> dict:
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
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
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
        logger.info(rendered)
        return rendered

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
        if isinstance(raw_metadata, dict) and raw_metadata.get("display_name") is not None:
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


def _paper_import_result_to_dict(import_result, warnings: list[str] | None = None) -> dict:
    return {
        "metadata": _paper_metadata_to_dict(import_result.metadata),
        "source_path": str(import_result.source_path) if import_result.source_path else None,
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


def _resolve_run_params(params_json: str | None, params_file: str | None) -> dict | None:
    """Resolve optional structured params for the run command."""
    if params_json and params_file:
        raise ValueError("--params-json and --params-file cannot be used together")
    if params_json:
        return _load_params_json(params_json)
    if params_file:
        return _load_params_file(params_file)
    return None


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(
        prog="supermedicine",
        description="SuperMedicine - 模块化医学科研 Agent 框架",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.add_argument("--dir", type=str, default=".", help="项目目录")

    # Status 命令
    subparsers.add_parser("status", help="显示项目状态")

    # Test 命令
    subparsers.add_parser("test", help="运行测试")

    # TUI 命令
    tui_parser = subparsers.add_parser(
        "tui",
        help="启动中文 TUI 工作台",
        description="启动中文 TUI 工作台",
    )
    tui_parser.add_argument("--dry-run", action="store_true", help="输出中文 TUI 就绪状态，不启动交互界面")

    # Run 命令
    run_parser = subparsers.add_parser("run", help="执行任务")
    run_parser.add_argument("task", type=str, help="任务描述")
    run_parser.add_argument("--verbose", action="store_true", help="详细输出")
    run_parser.add_argument("--plugin", type=str, default=None, help="指定插件名称")
    run_parser.add_argument("--action", type=str, default=None, help="指定插件动作")
    run_parser.add_argument("--params-json", type=str, default=None, help="JSON 对象格式的插件参数")
    run_parser.add_argument("--params-file", type=str, default=None, help="包含 JSON 对象插件参数的文件路径")
    run_parser.add_argument("--workspace", type=str, default=None, help="显式工作区 slug ID（workspaces/<id>；不会读取 TUI 最近状态）")

    # Workspace 命令
    workspace_parser = subparsers.add_parser("workspace", help="管理 workspaces/<id> 显式 slug 工作区")
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    workspace_init_parser = workspace_subparsers.add_parser("init", help="初始化工作区")
    workspace_init_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    workspace_init_parser.add_argument("--name", type=str, default=None, help="显示名称")

    workspace_subparsers.add_parser("list", help="列出工作区")

    workspace_show_parser = workspace_subparsers.add_parser("show", help="显示工作区")
    workspace_show_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")

    workspace_delete_parser = workspace_subparsers.add_parser(
        "delete",
        help="硬删除工作区（需强确认、权限与审计）",
        description="硬删除指定工作区；执行前会进行权限检查并写入审计记录。",
        epilog="必须提供 --confirm，且其值必须与 --workspace 完全一致。",
    )
    workspace_delete_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    workspace_delete_parser.add_argument("--confirm", required=True, type=str, help="必须与工作区 ID 完全一致")

    # Tool 命令（全部要求显式 --workspace；不会读取 TUI 最近状态）
    tool_parser = subparsers.add_parser("tool", help="管理工作区内 Python/R 模块化工具")
    tool_subparsers = tool_parser.add_subparsers(dest="tool_command")

    tool_init_parser = tool_subparsers.add_parser("init", help="初始化工作区工具目录")
    tool_init_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")

    tool_list_parser = tool_subparsers.add_parser("list", help="列出工作区工具")
    tool_list_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    tool_list_parser.add_argument("--language", choices=["python", "r"], default=None, help="可选语言过滤")

    tool_add_parser = tool_subparsers.add_parser("add", help="添加内置工具模板")
    tool_add_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    tool_add_parser.add_argument("--language", required=True, choices=["python", "r"], help="工具语言")
    tool_add_parser.add_argument("--tool", required=True, choices=["heatmap", "umap"], help="内置工具 ID")

    tool_show_parser = tool_subparsers.add_parser("show", help="显示工具清单")
    tool_show_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    tool_show_parser.add_argument("--language", required=True, choices=["python", "r"], help="工具语言")
    tool_show_parser.add_argument("--tool", required=True, type=str, help="工具 ID")

    tool_run_parser = tool_subparsers.add_parser("run", help="准备工具运行命令（安全基础默认不执行脚本）")
    tool_run_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    tool_run_parser.add_argument("--language", required=True, choices=["python", "r"], help="工具语言")
    tool_run_parser.add_argument("--tool", required=True, type=str, help="工具 ID")
    tool_run_parser.add_argument("--dry-run", action="store_true", help="只输出准备好的命令")
    tool_run_parser.add_argument("--input", type=str, default=None, help="工作区内输入路径")
    tool_run_parser.add_argument("--output", type=str, default=None, help="工作区内输出路径")

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
    paper_import_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    paper_import_parser.add_argument("--title", type=str, default=None, help="论文标题")
    paper_import_parser.add_argument("--doi", type=str, default=None, help="DOI")
    paper_import_parser.add_argument("--pmid", type=str, default=None, help="PMID")
    paper_import_parser.add_argument("--notes", type=str, default=None, help="备注")
    paper_import_parser.add_argument("--tag", action="append", default=None, help="标签，可重复")
    paper_import_parser.add_argument("--enrich", action="store_true", help="请求在线/外部元数据补全（默认不联网）")
    paper_import_parser.add_argument("--confirm-enrich", action="store_true", help="显式确认允许发起补全授权检查、网络/API 限制检查与审计")

    paper_list_parser = paper_subparsers.add_parser("list", help="列出工作区论文")
    paper_list_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")

    paper_show_parser = paper_subparsers.add_parser("show", help="显示论文元数据")
    paper_show_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_show_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")

    paper_edit_parser = paper_subparsers.add_parser("edit", help="编辑论文元数据")
    paper_edit_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_edit_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    paper_edit_parser.add_argument("--title", type=str, default=None, help="论文标题")
    paper_edit_parser.add_argument("--doi", type=str, default=None, help="DOI")
    paper_edit_parser.add_argument("--pmid", type=str, default=None, help="PMID")
    paper_edit_parser.add_argument("--notes", type=str, default=None, help="备注")
    paper_edit_parser.add_argument("--tag", action="append", default=None, help="标签，可重复")

    paper_enrich_parser = paper_subparsers.add_parser(
        "enrich",
        help="补全论文元数据",
        description="通过网络/API 补全论文元数据；执行前会进行授权、网络/API 限制检查并写入审计记录。",
        epilog="必须提供 --confirm-enrich 显式确认允许外部元数据补全。",
    )
    paper_enrich_parser.add_argument("paper_id", type=str, help="论文 ID")
    paper_enrich_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    paper_enrich_parser.add_argument("--confirm-enrich", action="store_true", required=True, help="显式确认允许发起补全授权检查、网络/API 限制检查与审计")

    # Experience 命令（全部要求显式 --workspace；建议不会持久化）
    experience_parser = subparsers.add_parser(
        "experience",
        help="管理确认后的经验记录（不存原始对话）",
        description="管理确认后的经验记录；只保存摘要、标签等结构化内容，不存原始对话。",
    )
    experience_subparsers = experience_parser.add_subparsers(dest="experience_command")

    experience_suggest_parser = experience_subparsers.add_parser("suggest", help="建议分类但不写入")
    experience_suggest_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_suggest_parser.add_argument("--title", type=str, default=None, help="经验标题")
    experience_suggest_parser.add_argument("--summary", required=True, type=str, help="经验摘要")
    experience_suggest_parser.add_argument("--tag", action="append", default=None, help="标签，可重复")

    experience_add_parser = experience_subparsers.add_parser("add", help="确认并新增经验")
    experience_add_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_add_parser.add_argument("--scope", required=True, choices=["general", "workspace"], help="确认后的存储范围")
    experience_add_parser.add_argument("--title", required=True, type=str, help="经验标题")
    experience_add_parser.add_argument("--summary", required=True, type=str, help="经验摘要")
    experience_add_parser.add_argument("--tag", action="append", default=None, help="标签，可重复")
    experience_add_parser.add_argument("--confirm", action="store_true", required=True, help="显式确认写入")

    experience_list_parser = experience_subparsers.add_parser("list", help="列出经验")
    experience_list_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_list_parser.add_argument("--include-general", action="store_true", help="包含通用方法层")

    experience_view_parser = experience_subparsers.add_parser("view", help="查看经验")
    experience_view_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_view_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_view_parser.add_argument("--scope", choices=["general", "workspace"], default=None, help="范围过滤")

    experience_edit_parser = experience_subparsers.add_parser("edit", help="编辑经验")
    experience_edit_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_edit_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_edit_parser.add_argument("--scope", required=True, choices=["general", "workspace"], help="经验范围")
    experience_edit_parser.add_argument("--title", type=str, default=None, help="经验标题")
    experience_edit_parser.add_argument("--summary", type=str, default=None, help="经验摘要")
    experience_edit_parser.add_argument("--tag", action="append", default=None, help="标签，可重复；提供后替换原标签")

    experience_delete_parser = experience_subparsers.add_parser("delete", help="删除经验")
    experience_delete_parser.add_argument("record_id", type=str, help="经验 ID")
    experience_delete_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_delete_parser.add_argument("--scope", required=True, choices=["general", "workspace"], help="经验范围")
    experience_delete_parser.add_argument("--confirm", required=True, type=str, help="必须与经验 ID 完全一致")

    experience_export_parser = experience_subparsers.add_parser("export", help="导出经验")
    experience_export_parser.add_argument("--workspace", required=True, type=str, help="工作区 ID")
    experience_export_parser.add_argument("--format", required=True, choices=["json", "md"], help="导出格式")
    experience_export_parser.add_argument("--include-general", action="store_true", help="包含通用方法层")
    experience_export_parser.add_argument("--output", type=str, default=None, help="可选 UTF-8 输出文件")

    args = parser.parse_args(argv)
    cli = CLI()

    if args.command == "init":
        cli.init(Path(args.dir))
    elif args.command == "status":
        cli.status()
    elif args.command == "test":
        cli.test()
    elif args.command == "tui":
        cli.tui(dry_run=args.dry_run)
    elif args.command == "run":
        verbose = getattr(args, 'verbose', False)
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
        elif args.tool_command == "add":
            cli.tool_add(args.workspace, args.language, args.tool)
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
                cli.experience_suggest(args.workspace, args.summary, title=args.title, tags=args.tag)
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
                cli.experience_list(args.workspace, include_general=args.include_general)
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
                cli.experience_delete(args.record_id, args.workspace, args.scope, args.confirm)
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
