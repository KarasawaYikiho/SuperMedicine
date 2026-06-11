#!/usr/bin/env python3
"""CLI argument parser and command dispatch (extracted from Cli.py)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from cli.helpers import (
    PERMISSION_RISK_NOTICE,
    _paper_metadata_options,
    _parse_llm_headers,
    _resolve_run_params,
)
from cli.logging_setup import (
    _configure_cli_logging,
    _configure_stdio_errors,
)

if TYPE_CHECKING:
    pass


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
        "mode", help="切换权限模式：sandbox、conservative 或 full"
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

    sandbox_parser = subparsers.add_parser(
        "sandbox",
        help="说明 sandbox 权限模式与自进化安全写入入口",
        description=(
            "Sandbox 是 SuperMedicine 的受限文件访问模式：读取限于项目内，写入限于 "
            "self_evolution/generated/tools/generated 等受控生成目录，并限制文件类型。"
        ),
        epilog=(
            "切换权限模式：supermedicine permission mode sandbox；"
            "生成自进化预览/产物：supermedicine self-evolve --access-mode sandbox "
            "--instruction <目标> --output generated/example.md。"
        ),
    )

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

    # Web 命令
    web_parser = subparsers.add_parser(
        "web",
        help="启动 Web 可视化界面",
        description="启动基于 FastAPI 的 Web 界面；需要安装可选依赖：pip install supermedicine[web]",
    )
    web_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="绑定地址（默认 127.0.0.1，仅本机访问）",
    )
    web_parser.add_argument(
        "--port", type=int, default=8000, help="端口号（默认 8000）"
    )
    web_parser.add_argument(
        "--reload", action="store_true", help="启用自动重载（开发模式）"
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

    self_evolve_parser = subparsers.add_parser(
        "self-evolve",
        aliases=["self-evolution"],
        help="生成自进化预览或在显式确认后写入安全产物",
        description=(
            "自进化入口：根据用户指令生成 Markdown/Python/R 产物。默认 --preview，"
            "不会写文件；写入必须显式 --confirm-write 且目标通过权限/路径检查。"
        ),
        epilog=(
            "sandbox 仅允许项目内 self_evolution/generated/tools/generated 等安全目录；"
            "full 模式必须同时提供 --confirm-full-access 与 --acknowledge-risk，"
            "且只使用当前用户/进程已有权限，不静默提权。"
        ),
    )
    self_evolve_parser.add_argument(
        "--instruction", required=True, type=str, help="用户自进化指令/目标"
    )
    self_evolve_parser.add_argument(
        "--experience-source",
        type=str,
        default=None,
        help="可选经验记录 ID；使用记录 ID 时需同时指定 --workspace",
    )
    self_evolve_parser.add_argument(
        "--target-type",
        choices=["markdown", "python_tool", "r_tool"],
        default="markdown",
        help="目标产物类型",
    )
    self_evolve_parser.add_argument(
        "--output", required=True, type=str, help="输出文件或目录路径"
    )
    self_evolve_parser.add_argument(
        "--access-mode",
        choices=["sandbox", "conservative", "full"],
        default="sandbox",
        help="权限/访问模式",
    )
    self_evolve_parser.add_argument(
        "--workspace", type=str, default=None, help="经验来源所需的显式工作区 ID"
    )
    self_evolve_parser.add_argument(
        "--preview",
        action="store_true",
        default=True,
        help="仅预览，不写入文件（默认）",
    )
    self_evolve_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="显式确认写入；必须与 --no-preview 一起使用才会写文件",
    )
    self_evolve_parser.add_argument(
        "--no-preview",
        dest="preview",
        action="store_false",
        help="关闭预览；只有同时提供 --confirm-write 才会写入",
    )
    self_evolve_parser.add_argument(
        "--overwrite", action="store_true", help="显式允许覆盖已存在的目标文件"
    )
    self_evolve_parser.add_argument(
        "--confirm-full-access",
        action="store_true",
        help="显式确认 full 访问模式；仅使用当前用户/进程已有权限",
    )
    self_evolve_parser.add_argument(
        "--acknowledge-risk",
        action="store_true",
        help="确认已理解 full 模式风险、OS 权限/UAC 语义与不静默提权限制",
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
        "--filename",
        type=str,
        default=None,
        help="保存到 plugins/experiments/ 的文件名",
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
    log_location_parser = log_subparsers.add_parser(
        "location", help="显示当前日志/报告/审计文件存储位置"
    )
    log_location_group = log_location_parser.add_mutually_exclusive_group()
    log_location_group.add_argument(
        "--file", type=str, default=None, help="解析指定日志报告文件位置"
    )
    log_location_group.add_argument(
        "--session-id", type=str, default=None, help="解析指定会话日志报告位置"
    )
    log_follow_parser = log_subparsers.add_parser(
        "follow", help="实时刷新并滚动显示最近日志内容"
    )
    log_follow_group = log_follow_parser.add_mutually_exclusive_group()
    log_follow_group.add_argument(
        "--file", type=str, default=None, help="跟随指定日志报告文件"
    )
    log_follow_group.add_argument(
        "--session-id", type=str, default=None, help="跟随指定会话日志报告"
    )
    log_follow_parser.add_argument(
        "--interval", type=float, default=1.0, help="刷新间隔秒数；测试可设为 0"
    )
    log_follow_parser.add_argument(
        "--max-entries", type=int, default=50, help="每次显示的最大最近日志条目数"
    )
    log_follow_parser.add_argument(
        "--max-lines", type=int, default=None, help="每次显示的最大最近文本行数"
    )
    log_follow_parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="刷新次数；用于非交互/测试安全退出",
    )
    log_follow_parser.add_argument(
        "--once", action="store_true", help="只刷新一次后退出（等同 --iterations 1）"
    )
    log_follow_parser.add_argument(
        "--no-clear", action="store_true", help="刷新间不清屏/分隔，便于测试捕获"
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

    # Lazy import to avoid circular dependency
    from Cli import CLI

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
    elif args.command == "sandbox":
        sandbox_parser.print_help()
    elif args.command == "test":
        cli.test()
    elif args.command == "tui":
        cli.tui(dry_run=args.dry_run)
    elif args.command == "web":
        try:
            cli.web(host=args.host, port=args.port, reload=args.reload)
        except ImportError as exc:
            web_parser.error(str(exc))
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
    elif args.command in {"self-evolve", "self-evolution"}:
        cli.self_evolve(
            instruction=args.instruction,
            artifact_type=args.target_type,
            output=args.output,
            access_mode=args.access_mode,
            experience_source=args.experience_source,
            workspace=args.workspace,
            preview=args.preview,
            confirm_write=args.confirm_write,
            overwrite=args.overwrite,
            confirm_full_access=args.confirm_full_access,
            acknowledge_risk=args.acknowledge_risk,
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
            elif args.log_command == "location":
                cli.log_location(file_name=args.file, session_id=args.session_id)
            elif args.log_command == "follow":
                cli.log_follow(
                    file_name=args.file,
                    session_id=args.session_id,
                    interval=args.interval,
                    max_entries=args.max_entries,
                    max_lines=args.max_lines,
                    iterations=args.iterations,
                    once=args.once,
                    no_clear=args.no_clear,
                )
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
