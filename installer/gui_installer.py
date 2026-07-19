"""Graphical installation interface for SuperMedicine.

Provides a tkinter-based GUI installer that allows users to:
- Select an installation directory via a text entry and "Browse..." button
- Choose which components to install via checkboxes
- Monitor installation progress
- View a result summary upon completion

When tkinter is unavailable (headless / no GUI environment), importing this
module succeeds but calling :func:`launch_gui_installer` raises a clear
:exc:`RuntimeError` guiding the user to the CLI installer.

Usage::

    from installer.gui_installer import launch_gui_installer

    launch_gui_installer()  # blocks until the window is closed

Or from the command line::

    python -m installer.gui_installer
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful tkinter import
# ---------------------------------------------------------------------------

_tkinter_available: bool
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    _tkinter_available = True
except ImportError:
    _tkinter_available = False

# Local imports — always safe because component_installer has no GUI deps.
from installer.component_installer import (  # noqa: E402
    ComponentDef,
    ComponentError,
    InstallService,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WINDOW_TITLE = "SuperMedicine 安装向导"
_DEFAULT_WINDOW_SIZE = "620x520"
_MIN_WINDOW_WIDTH = 580
_MIN_WINDOW_HEIGHT = 480
_PADDING = 10
_INSTALL_JSON_CANDIDATES = (
    Path(__file__).resolve().parents[1] / "install.json",
    Path.cwd() / "install.json",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_install_json() -> Path | None:
    """Return the first existing *install.json* path or ``None``."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    bundle_candidates = (Path(bundle_root) / "install.json",) if bundle_root else ()
    for candidate in (*bundle_candidates, *_INSTALL_JSON_CANDIDATES):
        if candidate.is_file():
            return candidate
    return None


def _default_install_path() -> str:
    """Return a sensible default install directory."""
    return str(Path.cwd())


# ---------------------------------------------------------------------------
# Main GUI class
# ---------------------------------------------------------------------------


class _InstallerGUI:
    """Encapsulates the full tkinter installer window."""

    # ---- lifecycle --------------------------------------------------------

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._root.title(_WINDOW_TITLE)
        self._root.geometry(_DEFAULT_WINDOW_SIZE)
        self._root.minsize(_MIN_WINDOW_WIDTH, _MIN_WINDOW_HEIGHT)

        # State
        self._components: dict[str, ComponentDef] = {}
        self._install_service: InstallService | None = None
        self._check_vars: dict[str, tk.BooleanVar] = {}
        self._installing = False

        # Load component definitions
        self._load_component_defs()

        # Build UI
        self._build_ui()

    # ---- data loading -----------------------------------------------------

    def _load_component_defs(self) -> None:
        config_path = _find_install_json()
        if config_path is None:
            logger.warning("install.json 未找到，组件选择不可用")
            return
        try:
            self._install_service = InstallService.from_manifest(
                config_path, source_root=config_path.parent
            )
            self._components = self._install_service.components
        except (FileNotFoundError, KeyError, ComponentError) as exc:
            logger.warning("加载组件定义失败: %s", exc)

    # ---- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        root = self._root

        # --- Install path section ---
        path_frame = ttk.LabelFrame(root, text="安装路径", padding=_PADDING)
        path_frame.pack(fill=tk.X, padx=_PADDING, pady=(10, 5))

        self._path_var = tk.StringVar(value=_default_install_path())
        path_entry = ttk.Entry(path_frame, textvariable=self._path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(
            path_frame, text="浏览...", command=self._browse_install_path
        )
        browse_btn.pack(side=tk.RIGHT)

        # --- Component selection section ---
        comp_frame = ttk.LabelFrame(root, text="安装组件", padding=_PADDING)
        comp_frame.pack(fill=tk.BOTH, expand=True, padx=_PADDING, pady=5)

        if not self._components:
            ttk.Label(comp_frame, text="(未找到组件定义文件 install.json)").pack(
                anchor=tk.W
            )
        else:
            for name in sorted(self._components):
                comp = self._components[name]
                default_selected = comp.default or comp.required
                var = tk.BooleanVar(value=default_selected)
                self._check_vars[name] = var

                label_text = f"{name} — {comp.description}"
                if comp.required:
                    label_text += "  (必选)"

                cb = ttk.Checkbutton(
                    comp_frame, text=label_text, variable=var
                )
                cb.pack(anchor=tk.W, pady=2)

                # Disable required components so they cannot be unchecked
                if comp.required:
                    cb.state(["disabled"])

        # --- Action buttons ---
        btn_frame = ttk.Frame(root, padding=_PADDING)
        btn_frame.pack(fill=tk.X, padx=_PADDING, pady=5)

        self._install_btn = ttk.Button(
            btn_frame, text="开始安装", command=self._on_install
        )
        self._install_btn.pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = ttk.Button(
            btn_frame, text="取消", command=self._on_cancel
        )
        cancel_btn.pack(side=tk.LEFT)

        # --- Progress section ---
        progress_frame = ttk.LabelFrame(root, text="安装进度", padding=_PADDING)
        progress_frame.pack(fill=tk.X, padx=_PADDING, pady=5)

        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self._progress_var,
            maximum=100,
            mode="determinate",
        )
        self._progress_bar.pack(fill=tk.X)

        self._status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            progress_frame, textvariable=self._status_var, anchor=tk.W
        )
        status_label.pack(fill=tk.X, pady=(4, 0))

        # --- Result summary section ---
        result_frame = ttk.LabelFrame(root, text="结果摘要", padding=_PADDING)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=_PADDING, pady=(5, 10))

        self._result_text = tk.Text(
            result_frame, height=5, state=tk.DISABLED, wrap=tk.WORD
        )
        self._result_text.pack(fill=tk.BOTH, expand=True)

    # ---- callbacks --------------------------------------------------------

    def _browse_install_path(self) -> None:
        directory = filedialog.askdirectory(
            parent=self._root, title="选择安装目录"
        )
        if directory:
            self._path_var.set(directory)

    def _get_selected_components(self) -> list[str]:
        return sorted(
            name for name, var in self._check_vars.items() if var.get()
        )

    def _set_ui_state(self, installing: bool) -> None:
        """Enable/disable interactive widgets during installation."""
        self._installing = installing
        state = "disabled" if installing else "normal"
        self._install_btn.configure(state=state)

    def _append_result(self, text: str) -> None:
        self._result_text.configure(state=tk.NORMAL)
        self._result_text.insert(tk.END, text + "\n")
        self._result_text.see(tk.END)
        self._result_text.configure(state=tk.DISABLED)

    def _clear_result(self) -> None:
        self._result_text.configure(state=tk.NORMAL)
        self._result_text.delete("1.0", tk.END)
        self._result_text.configure(state=tk.DISABLED)

    def _on_install(self) -> None:
        if self._installing:
            return

        install_path = self._path_var.get().strip()
        if not install_path:
            messagebox.showwarning("提示", "请指定安装路径。", parent=self._root)
            return

        selected = self._get_selected_components()
        if not selected:
            messagebox.showwarning(
                "提示", "请至少选择一个安装组件。", parent=self._root
            )
            return

        # Validate selection
        if self._install_service:
            try:
                self._install_service.validate(selected)
            except ComponentError as exc:
                messagebox.showerror("组件选择无效", str(exc), parent=self._root)
                return

        # Confirm
        if not messagebox.askyesno(
            "确认安装",
            f"即将安装以下组件到:\n{install_path}\n\n"
            f"组件: {', '.join(selected)}\n\n确认开始？",
            parent=self._root,
        ):
            return

        self._set_ui_state(installing=True)
        self._clear_result()
        self._progress_var.set(0)
        self._status_var.set("正在安装...")

        # Run installation in a background thread to keep the UI responsive
        thread = threading.Thread(
            target=self._run_installation,
            args=(selected, install_path),
            daemon=True,
        )
        thread.start()

    def _run_installation(
        self, selected: list[str], install_path: str
    ) -> None:
        """Execute the actual installation (runs in a worker thread)."""
        try:
            # Simulate progress stages
            self._update_progress(10, "正在验证组件...")
            if self._install_service:
                self._install_service.validate(selected)

            self._update_progress(30, "正在复制文件...")

            result: dict[str, Any] = {}
            if self._install_service:
                result = self._install_service.install(
                    selected,
                    install_path,
                    overwrite=False,
                )
            else:
                result = {
                    "status": "skipped",
                    "reason": "no-components-defined",
                }

            self._update_progress(100, "安装完成")

            # Schedule UI update on the main thread
            self._root.after(0, self._on_install_success, result, selected)

        except Exception as exc:
            self._root.after(0, self._on_install_failure, exc)

    def _update_progress(self, value: float, status: str) -> None:
        """Thread-safe progress update via ``after``."""
        self._root.after(0, self._progress_var.set, value)
        self._root.after(0, self._status_var.set, status)

    def _on_install_success(
        self, result: dict[str, Any], selected: list[str]
    ) -> None:
        """Handle successful installation on the main thread."""
        self._set_ui_state(installing=False)

        status = result.get("status", "unknown")
        file_count = result.get("file_count", 0)
        target_dir = result.get("target_dir", "")
        reason = result.get("reason", "")

        summary_lines = [
            f"状态: {status}",
            f"目标目录: {target_dir}",
            f"已选组件: {', '.join(selected)}",
            f"文件数量: {file_count}",
        ]
        if reason:
            summary_lines.append(f"原因: {reason}")

        summary = "\n".join(summary_lines)
        self._append_result(summary)

        if status == "copied":
            messagebox.showinfo(
                "安装成功",
                f"安装完成！共安装 {file_count} 个文件到:\n{target_dir}",
                parent=self._root,
            )
        elif status == "skipped":
            messagebox.showwarning(
                "安装跳过",
                f"安装被跳过: {reason}",
                parent=self._root,
            )
        else:
            messagebox.showinfo(
                "安装结果",
                f"状态: {status}\n{reason}",
                parent=self._root,
            )

    def _on_install_failure(self, exc: Exception) -> None:
        """Handle installation failure on the main thread."""
        self._set_ui_state(installing=False)
        self._status_var.set("安装失败")
        self._append_result(f"错误: {exc}")
        messagebox.showerror(
            "安装失败", f"安装过程中发生错误:\n{exc}", parent=self._root
        )

    def _on_cancel(self) -> None:
        if self._installing:
            if messagebox.askyesno(
                "确认取消",
                "安装正在进行中，确定要取消吗？",
                parent=self._root,
            ):
                # Cannot safely abort mid-copy; just close the window.
                self._root.destroy()
        else:
            self._root.destroy()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def launch_gui_installer() -> None:
    """Launch the GUI installer window.

    This function blocks until the window is closed.

    Raises:
        RuntimeError: If tkinter is not available in the current environment.
    """
    if not _tkinter_available:
        raise RuntimeError(
            "tkinter 不可用，无法启动图形化安装界面。"
            "请使用命令行安装模式: python install_entry.py --init --interactive"
        )

    root = tk.Tk()
    _InstallerGUI(root)
    root.mainloop()


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def installer_self_test() -> dict[str, Any]:
    """Validate frozen resources and storage without opening a window."""

    manifest = _find_install_json()
    service: InstallService | None = None
    if manifest is not None:
        try:
            service = InstallService.from_manifest(
                manifest, source_root=manifest.parent
            )
        except (FileNotFoundError, KeyError, ComponentError):
            service = None
    persistent_path = Path(_default_install_path()).expanduser().resolve()
    raw_bundle_root = getattr(sys, "_MEIPASS", None)
    bundle_root = Path(raw_bundle_root).resolve() if raw_bundle_root else None
    checks = {
        "tkinter": _tkinter_available,
        "manifest": manifest is not None and manifest.is_file(),
        "install_service": service is not None,
        "components": service is not None and bool(service.components),
        "persistent_path_outside_bundle": (
            bundle_root is None or not persistent_path.is_relative_to(bundle_root)
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "manifest": str(manifest) if manifest else None,
        "persistent_path": str(persistent_path),
        "bundle_root": str(bundle_root) if bundle_root else None,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for ``python -m installer.gui_installer``."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)

    if args == ["--self-test"]:
        report = installer_self_test()
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["ok"] else 1
    if args:
        print("usage: gui_installer.py [--self-test]", file=sys.stderr)
        return 2

    if not _tkinter_available:
        print(
            "错误: tkinter 不可用，无法启动图形化安装界面。\n"
            "请使用命令行安装模式: python install_entry.py --init --interactive",
            file=sys.stderr,
        )
        return 1

    launch_gui_installer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
