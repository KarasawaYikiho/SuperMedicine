"""Chinese labels and messages for the SuperMedicine TUI."""

from __future__ import annotations


LABELS: dict[str, str] = {
    # Existing
    "app_title": "SuperMedicine 终端工作台",
    "welcome": "欢迎使用 SuperMedicine 中文终端界面",
    "workspace": "工作区",
    "recent_workspace": "最近工作区",
    "no_recent_workspace": "尚未选择最近工作区",
    "permission_required": "需要权限确认",
    "confirmation_required": "高风险操作需要显式确认",
    "permission_denied": "权限策略拒绝该操作",
    "permission_allowed": "权限策略允许该操作",
    "dry_run_status": "TUI 基础组件已就绪（未启动交互界面）",
    "sandbox_notice": "工具执行必须经过权限引擎、适配器沙箱、审计与确认",

    # Navigation
    "nav_chat": "对话",
    "nav_dashboard": "仪表盘",
    "nav_workspace": "工作区管理",
    "nav_paper": "论文管理",
    "nav_experience": "经验学习",
    "nav_tool": "工具管理",
    "nav_dialog": "对话历史",
    "nav_quit": "退出",
    "nav_maximize": "最大化",

    # Dashboard
    "dashboard_title": "仪表盘",
    "dashboard_version": "版本",
    "dashboard_status": "状态",
    "dashboard_plugins": "插件数",
    "dashboard_modules": "模块数",
    "dashboard_workspaces": "工作区数",
    "dashboard_metric": "指标",
    "dashboard_value": "值",
    "dashboard_recent": "最近活动",
    "dashboard_quick_actions": "快捷操作",
    "dashboard_initialized": "已初始化",
    "dashboard_not_initialized": "未初始化",

    # Workspace
    "workspace_title": "工作区管理",
    "workspace_list": "工作区列表",
    "workspace_create": "创建工作区",
    "workspace_select": "选择工作区",
    "workspace_delete": "删除工作区",
    "workspace_id_label": "工作区 ID",
    "workspace_name_label": "显示名称（可选）",
    "workspace_confirm_delete": "输入工作区 ID 确认删除",
    "workspace_no_workspaces": "暂无工作区，请先创建",
    "workspace_created": "工作区已创建",
    "workspace_selected": "已选择工作区",
    "workspace_deleted": "工作区已删除",
    "workspace_path": "路径",
    "workspace_created_at": "创建时间",

    # Paper
    "paper_title": "论文管理",
    "paper_import": "导入论文",
    "paper_list": "论文列表",
    "paper_no_papers": "暂无论文，请先导入",
    "paper_file_path": "论文文件路径",
    "paper_title_label": "论文标题",
    "paper_doi_label": "DOI",
    "paper_pmid_label": "PMID",
    "paper_notes_label": "备注",
    "paper_tags_label": "标签（逗号分隔）",
    "paper_imported": "论文已导入",
    "paper_select_workspace": "请先选择工作区",
    "paper_authors": "作者",
    "paper_format": "格式",
    "paper_imported_at": "导入时间",
    "paper_enrich": "在线补全",
    "paper_enrich_confirm": "确认在线补全？将发起网络请求。",

    # Experience
    "experience_title": "经验学习",
    "experience_suggest": "建议分类",
    "experience_list": "经验列表",
    "experience_no_records": "暂无经验记录",
    "experience_summary_label": "经验摘要",
    "experience_title_label": "经验标题",
    "experience_tags_label": "标签（逗号分隔）",
    "experience_scope_label": "存储范围",
    "experience_scope_general": "通用方法层",
    "experience_scope_workspace": "工作区层",
    "experience_suggested": "分类建议已生成",
    "experience_confirmed": "经验已确认写入",
    "experience_deleted": "经验已删除",
    "experience_export": "导出经验",
    "experience_export_format": "导出格式",
    "experience_confirm_delete": "输入经验 ID 确认删除",

    # Tool
    "tool_title": "工具管理",
    "tool_init": "初始化工具目录",
    "tool_list": "工具列表",
    "tool_add": "添加工具",
    "tool_no_tools": "暂无工具，请先初始化",
    "tool_language": "语言",
    "tool_language_python": "Python",
    "tool_language_r": "R",
    "tool_tool_id": "工具 ID",
    "tool_available": "可用工具：heatmap, umap",
    "tool_initialized": "工具目录已初始化",
    "tool_added": "工具已添加",
    "tool_run": "运行工具",

    # Dialog
    "dialog_title": "对话历史",
    "dialog_no_history": "暂无对话历史",
    "dialog_event": "事件",
    "dialog_summary": "摘要",
    "dialog_time": "时间",

    # Common
    "confirm": "确认",
    "cancel": "取消",
    "back": "返回",
    "save": "保存",
    "delete": "删除",
    "edit": "编辑",
    "create": "创建",
    "import_btn": "导入",
    "refresh": "刷新",
    "loading": "加载中...",
    "error": "错误",
    "success": "成功",
    "warning": "警告",
    "info": "信息",
    "yes": "是",
    "no": "否",
    "input_placeholder": "输入消息...",
    "select_prompt": "请选择...",
    "no_selection": "未选择",
    "status_workspaces": "工作区",
    "status_plugins": "插件",
    "thinking": "正在思考...",
    "chat_help": "在下方输入框输入消息，按 Enter 发送。输入 /help 查看命令。",
    "help_title": "快捷键帮助",
    "help_navigation": "导航：↑↓ 选择 | Enter 确认 | Esc 返回",
    "help_global": "全局：Q 退出 | ? 帮助 | F 最大化 | Tab 切换焦点",
    "help_escape_hint": "按 Esc 可退出最大化",
}


def t(key: str) -> str:
    """Return a Chinese UI label by key, falling back to the key itself."""

    return LABELS.get(key, key)
