"""Chinese labels and messages for the SuperMedicine TUI."""

from __future__ import annotations


LABELS: dict[str, str] = {
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
}


def t(key: str) -> str:
    """Return a Chinese UI label by key, falling back to the key itself."""

    return LABELS.get(key, key)
