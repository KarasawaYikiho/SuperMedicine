"""LLM provider management view for the SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class LLMScreenController:
    """Thin TUI facade over the shared LLM configuration manager."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_path = self.project_root / ".supermedicine" / "config.yaml"
        self.manager = LLMConfigManager(ConfigCenter(self.config_path))

    def list_providers(self) -> dict[str, Any]:
        return self.manager.list_providers(redacted=True)

    def current_provider(self) -> dict[str, Any]:
        return self.manager.get_current_provider(redacted=True)

    def readiness(self) -> dict[str, Any]:
        current = self.current_provider()
        provider = str(current.get("provider") or "")
        if not provider:
            return {"ok": False, "provider": "", "message": t("llm_not_ready")}
        validation = self.manager.validate_provider(provider)
        if validation is None:
            return {"ok": True, "provider": provider, "message": t("llm_ready")}
        return {
            "ok": False,
            "provider": provider,
            "message": str(redact_sensitive(validation.get("error", {}).get("message") or t("llm_not_ready"))),
        }

    def add_provider(
        self,
        provider: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
        api_format: str = "",
        set_current: bool = True,
    ) -> dict[str, Any]:
        values = {
            "base_url": base_url.strip(),
            "api_key": api_key.strip(),
            "model": model.strip(),
        }
        if api_format.strip():
            values["api_format"] = api_format.strip()
        return self.manager.add_provider(provider, values, set_current=set_current)

    def switch_provider(self, provider: str) -> dict[str, Any]:
        return self.manager.switch_provider(provider)

    def save_exit_state(self) -> dict[str, Any]:
        return self.manager.save_exit_state()


class LLMView(Vertical):
    """View for adding, selecting, and switching LLM providers."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._controller: LLMScreenController | None = None

    def compose(self) -> ComposeResult:
        yield Static(t("llm_title"), classes="section-title")
        yield Static("", id="llm-current")
        yield Static(t("llm_secret_hidden"), id="llm-secret-hint")
        yield DataTable(id="llm-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Select([], prompt=t("llm_missing_selection"), id="llm-provider-select")
            yield Button(t("llm_switch_provider"), id="llm-switch", classes="btn btn-primary")
            yield Button(t("refresh"), id="llm-refresh", classes="btn btn-secondary")
        with Vertical(id="llm-form"):
            yield Input(placeholder=t("llm_provider_name"), id="llm-provider-input")
            yield Input(placeholder=t("llm_base_url"), id="llm-base-url-input")
            yield Input(placeholder=t("llm_model"), id="llm-model-input")
            yield Input(placeholder=t("llm_api_key"), password=True, id="llm-api-key-input")
            yield Input(placeholder=t("llm_api_format"), id="llm-api-format-input")
            yield Button(t("llm_add_provider"), id="llm-add", classes="btn btn-primary")
        yield Static("", id="llm-status")

    @property
    def controller(self) -> LLMScreenController:
        if self._controller is None:
            self._controller = LLMScreenController(self._project_root)
        return self._controller

    def on_mount(self) -> None:
        self.refresh_llm_state()

    def refresh_llm_state(self) -> None:
        table = self.query_one("#llm-table", DataTable)
        select = self.query_one("#llm-provider-select", Select)
        current_widget = self.query_one("#llm-current", Static)
        table.clear(columns=True)
        table.add_columns(t("llm_provider"), t("llm_base_url"), t("llm_model"), t("dashboard_status"))

        providers = self.controller.list_providers()
        readiness = self.controller.readiness()
        current_provider = str(readiness.get("provider") or "")
        options: list[tuple[str, str]] = []

        for name, config in providers.items():
            provider_name = str(name)
            if not isinstance(config, dict):
                config = {}
            options.append((provider_name, provider_name))
            status = t("llm_ready") if self.controller.manager.validate_provider(provider_name) is None else t("llm_not_ready")
            table.add_row(
                provider_name,
                str(config.get("base_url") or ""),
                str(config.get("model") or ""),
                status,
            )

        select.set_options(options)
        if current_provider and any(value == current_provider for _, value in options):
            select.value = current_provider

        current_label = current_provider or t("no_selection")
        state_label = t("llm_ready") if readiness.get("ok") else t("llm_not_ready")
        current_widget.update(f"{t('llm_current')}: {current_label} · {state_label}")
        if not providers:
            self._set_status(t("llm_no_providers"))
        else:
            self._set_status(str(readiness.get("message") or state_label))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "llm-refresh":
            self.refresh_llm_state()
            self._set_status(t("llm_refreshed"))
        elif event.button.id == "llm-add":
            self._add_provider_from_form()
        elif event.button.id == "llm-switch":
            self._switch_selected_provider()

    def _add_provider_from_form(self) -> None:
        provider = self.query_one("#llm-provider-input", Input).value.strip()
        if not provider:
            self._set_status(t("llm_missing_provider"))
            return

        result = self.controller.add_provider(
            provider,
            base_url=self.query_one("#llm-base-url-input", Input).value,
            api_key=self.query_one("#llm-api-key-input", Input).value,
            model=self.query_one("#llm-model-input", Input).value,
            api_format=self.query_one("#llm-api-format-input", Input).value,
            set_current=True,
        )
        self.query_one("#llm-api-key-input", Input).value = ""
        if result.get("ok"):
            self._set_status(f"{t('llm_provider_added')}: {provider.lower()}")
            self.refresh_llm_state()
        else:
            self._set_status(self._safe_error_message(result))

    def _switch_selected_provider(self) -> None:
        select = self.query_one("#llm-provider-select", Select)
        if select.value is None or select.value == Select.BLANK:
            self._set_status(t("llm_missing_selection"))
            return
        provider = str(select.value)
        result = self.controller.switch_provider(provider)
        if result.get("ok"):
            self._set_status(f"{t('llm_provider_switched')}: {provider}")
            self.refresh_llm_state()
        else:
            self._set_status(self._safe_error_message(result))

    def _safe_error_message(self, result: dict[str, Any]) -> str:
        error = result.get("error", {}) if isinstance(result, dict) else {}
        message = str(error.get("message") or t("error")) if isinstance(error, dict) else t("error")
        return f"{t('error')}: {redact_sensitive(message) or t('safe_error_hint')}"

    def _set_status(self, message: str) -> None:
        status = self.query_one("#llm-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def on_unmount(self) -> None:
        try:
            self.controller.save_exit_state()
        except Exception:
            pass


LLMScreen = LLMView
