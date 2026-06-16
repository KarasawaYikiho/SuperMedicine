"""Tests for DashboardView real-time refresh — DBG-BUG-005."""

from __future__ import annotations

import asyncio
import inspect
import time

import yaml
from textual.widgets import DataTable, Static

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.tui.screens.dashboard import (
    DashboardOverviewController,
    DashboardView,
    collect_dashboard_context,
)
from core.workspace import WorkspaceManager


# ═══ Shared helpers ═══


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


async def _wait_for_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


# ═══ Dashboard refresh tests ═══


def test_dashboard_view_exposes_refresh_view_data_hook():
    """DashboardView declares refresh_view_data method for activation refresh."""
    assert hasattr(DashboardView, "refresh_view_data")
    source = inspect.getsource(DashboardView.refresh_view_data)
    assert "_load_data" in source


def test_dashboard_view_uses_targeted_refresh_without_polling():
    """DashboardView uses refresh_view_data hook, not polling timer."""
    source = inspect.getsource(DashboardView)

    assert "refresh_view_data" in source
    assert "set_interval" not in source


def test_dashboard_view_compose_declares_required_widgets():
    """DashboardView.compose yields all required widgets."""
    source = inspect.getsource(DashboardView.compose)

    assert 'id="dashboard-table"' in source
    assert 'id="dashboard-advice"' in source
    assert 'id="dashboard-summary"' in source
    assert 'id="dashboard-shortcuts"' in source


def test_dashboard_view_loads_data_on_mount(tmp_path):
    """DashboardView populates table on mount with overview data."""
    (tmp_path / ".supermedicine").mkdir()

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            table = app.query_one("#dashboard-table", DataTable)
            assert table.row_count > 0
            # Verify metric labels are present
            rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
            combined = " ".join(rows)
            assert t("dashboard_init_status") in combined

    asyncio.run(scenario())


def test_dashboard_view_refresh_view_data_reloads_table(tmp_path):
    """refresh_view_data reloads dashboard data when called explicitly."""
    (tmp_path / ".supermedicine").mkdir()

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            table = app.query_one("#dashboard-table", DataTable)
            initial_rows = table.row_count

            # Add workspace and refresh
            WorkspaceManager(tmp_path).initialize_workspace("dash-ws")
            view = app._views["dashboard"]
            view.refresh_view_data()
            await pilot.pause()

            # Table should still have same number of metric rows but with updated data
            assert table.row_count == initial_rows
            # Verify workspace count changed
            rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
            combined = " ".join(rows)
            assert "1" in combined  # workspace_count should now be 1

    asyncio.run(scenario())


def test_dashboard_view_switch_back_and_forth_refreshes_data(tmp_path):
    """Switching away and back to dashboard triggers refresh_view_data."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("switch-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            table = app.query_one("#dashboard-table", DataTable)
            rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
            combined = " ".join(rows)
            assert "1" in combined

            # Switch away and back
            app.action_switch_view("chat")
            await pilot.pause()

            manager.initialize_workspace("switch-ws-2")
            app.action_switch_view("dashboard")
            await pilot.pause()

            rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
            combined = " ".join(rows)
            assert "2" in combined

    asyncio.run(scenario())


def test_dashboard_view_advice_text_updates_on_refresh(tmp_path):
    """Advice text changes based on project state after refresh."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            # action_switch_view creates .supermedicine, so project is initialized
            # but no workspaces yet -> create_workspace advice
            advice = _static_text(app.query_one("#dashboard-advice", Static))
            assert advice.startswith(t("dashboard_action_hint"))
            assert t("dashboard_action_create_workspace") in advice

            # Create workspace and refresh
            WorkspaceManager(tmp_path).initialize_workspace("adv-ws")
            view = app._views["dashboard"]
            view.refresh_view_data()
            await pilot.pause()

            advice = _static_text(app.query_one("#dashboard-advice", Static))
            assert advice.startswith(t("dashboard_action_hint"))
            assert t("dashboard_action_configure_llm") in advice

    asyncio.run(scenario())


def test_dashboard_view_advice_shows_ready_when_fully_configured(tmp_path):
    """Advice text shows ready state when project is fully configured."""
    (tmp_path / ".supermedicine").mkdir()
    WorkspaceManager(tmp_path).initialize_workspace("ready-ws")
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.test/v1",
                            "api_key": "sk-ready-test-key",
                            "model": "gpt-test",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            advice = _static_text(app.query_one("#dashboard-advice", Static))
            assert t("dashboard_action_ready") in advice

    asyncio.run(scenario())


def test_dashboard_controller_overview_rows_returns_metric_value_pairs(tmp_path):
    """DashboardOverviewController.overview_rows returns (metric, value) tuples."""
    controller = DashboardOverviewController(tmp_path)

    rows = controller.overview_rows()

    assert len(rows) == 8
    labels = [label for label, _ in rows]
    assert t("dashboard_init_status") in labels
    assert t("dashboard_workspaces") in labels
    assert t("dashboard_plugins") in labels
    assert t("dashboard_modules") in labels
    assert t("dashboard_llm_status") in labels
    assert t("dashboard_token_stats") in labels
    assert t("dashboard_recent_hint") in labels
    assert t("dashboard_version") in labels


def test_dashboard_controller_context_reflects_state_changes(tmp_path):
    """collect_dashboard_context reflects project state changes."""
    context_before = collect_dashboard_context(tmp_path)
    assert context_before["initialized"] is False
    assert context_before["workspace_count"] == 0

    (tmp_path / ".supermedicine").mkdir()
    WorkspaceManager(tmp_path).initialize_workspace("ctx-ws")

    context_after = collect_dashboard_context(tmp_path)
    assert context_after["initialized"] is True
    assert context_after["workspace_count"] == 1


def test_dashboard_controller_context_no_secret_leak(tmp_path):
    """Dashboard context and rows never contain API keys."""
    secret = "sk-dashboard-refresh-secret"
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.test/v1",
                            "api_key": secret,
                            "model": "gpt-test",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)
    controller = DashboardOverviewController(tmp_path)
    rows = controller.overview_rows()

    rendered = str(context) + str(rows)
    assert secret not in rendered


def test_dashboard_view_table_has_two_columns(tmp_path):
    """Dashboard table has metric and value columns."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            table = app.query_one("#dashboard-table", DataTable)
            columns = [str(col.label) for col in table.columns.values()]
            assert len(columns) == 2
            assert t("dashboard_metric") in columns
            assert t("dashboard_value") in columns

    asyncio.run(scenario())


def test_dashboard_view_shows_llm_status_in_table(tmp_path):
    """LLM status appears in dashboard table."""
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.test/v1",
                            "api_key": "sk-llm-status-test",
                            "model": "gpt-dash",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 50)) as pilot:
            app.action_switch_view("dashboard")
            await pilot.pause()

            table = app.query_one("#dashboard-table", DataTable)
            rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
            combined = " ".join(rows)
            assert "openai" in combined
            assert "gpt-dash" in combined
            assert "LLM 已就绪" in combined

    asyncio.run(scenario())


def test_dashboard_view_no_polling_timer():
    """DashboardView source has no set_interval or Timer usage."""
    source = inspect.getsource(DashboardView)

    assert "set_interval" not in source
    assert "Timer" not in source


def test_dashboard_context_action_hint_varies_by_state(tmp_path):
    """Action hint text changes based on project initialization and configuration state."""
    # Not initialized
    context = collect_dashboard_context(tmp_path)
    assert t("dashboard_action_init") in context["action_hint"]

    # Initialized, no workspace
    (tmp_path / ".supermedicine").mkdir()
    context = collect_dashboard_context(tmp_path)
    assert t("dashboard_action_create_workspace") in context["action_hint"]

    # Initialized with workspace, no LLM
    WorkspaceManager(tmp_path).initialize_workspace("hint-ws")
    context = collect_dashboard_context(tmp_path)
    assert t("dashboard_action_configure_llm") in context["action_hint"]


def test_dashboard_controller_advice_text_returns_action_hint(tmp_path):
    """DashboardOverviewController.advice_text returns the action_hint from context."""
    controller = DashboardOverviewController(tmp_path)
    context = controller.context()

    assert controller.advice_text() == context["action_hint"]
