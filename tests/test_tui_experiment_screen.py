from __future__ import annotations

import asyncio

from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


def test_tui_explicit_switch_opens_experiment_screen_and_preserves_prompt_focus(
    tmp_path,
):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            assert app._current_view == "experiment"
            assert app._views["experiment"].display is True
            assert app.query_one("#prompt-input", Input).has_focus
            assert t("nav_experiment") in _static_text(
                app.query_one("#view-title", Static)
            )
            assert t("experiment_boundary") in _static_text(
                app.query_one("#experiment-boundary", Static)
            )
            assert t("experiment_current_step") in _static_text(
                app.query_one("#experiment-step", Static)
            )
            assert app.query_one("#experiment-data-input", TextArea) is not None

            app.action_switch_view("chat")
            await pilot.pause()

            assert app._current_view == "chat"
            assert app.query_one("#prompt-input", Input).has_focus

    asyncio.run(scenario())


def test_experiment_screen_accepts_input_calculates_advances_and_saves_redacted_log(
    tmp_path,
):
    secret = "sk-experiment-screen-secret"

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            data_input = app.query_one("#experiment-data-input", TextArea)
            data_input.load_text(
                '{"sample_id":"S1","target_protein":"GAPDH",'
                f'"notes":"api_key={secret}"}}'
            )
            app.query_one("#experiment-output-input", Input).value = "样本已裂解"

            await pilot.click("#experiment-calculate")
            await pilot.pause()

            calculation_text = _static_text(
                app.query_one("#experiment-reagent-result", Static)
            )
            assert t("experiment_reagent_result") in calculation_text
            assert "protein_loading_normalization" in calculation_text
            assert "experiment-wb" in calculation_text
            assert "preview" not in calculation_text
            assert secret not in calculation_text
            assert "[REDACTED]" in calculation_text
            assert t("experiment_reagent_result") in _static_text(
                app.query_one("#experiment-status", Static)
            )

            await pilot.click("#experiment-submit")
            await pilot.pause()

            view = app._views["experiment"]
            assert view._session.current_step.step_id == "gel_electrophoresis"
            assert t("experiment_step_saved") in _static_text(
                app.query_one("#experiment-status", Static)
            )

            await pilot.click("#experiment-save-log")
            await pilot.pause()

            log_files = list((tmp_path / ".supermedicine" / "logs").glob("*.json"))
            assert len(log_files) == 1
            log_text = log_files[0].read_text(encoding="utf-8")
            assert secret not in log_text
            assert "[REDACTED]" in log_text
            assert t("experiment_log_saved") in _static_text(
                app.query_one("#experiment-status", Static)
            )

    asyncio.run(scenario())


def test_experiment_screen_reports_missing_required_input(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            app.query_one("#experiment-data-input", TextArea).load_text(
                '{"sample_id":"S1"}'
            )
            await pilot.click("#experiment-submit")
            await pilot.pause()

            status = _static_text(app.query_one("#experiment-status", Static))
            assert t("error") in status
            assert t("experiment_missing_required") in status
            assert "目标蛋白" in status

    asyncio.run(scenario())


def test_experiment_screen_initial_empty_copy_and_safe_layout_are_visible(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            assert t("experiment_protocol") in _static_text(
                app.query_one("#experiment-session", Static)
            )
            assert t("experiment_current_step") in _static_text(
                app.query_one("#experiment-step", Static)
            )
            assert t("experiment_step_instructions") in _static_text(
                app.query_one("#experiment-instructions", Static)
            )
            assert app.query_one("#experiment-input-table", DataTable).row_count > 0
            assert t("experiment_boundary") in _static_text(
                app.query_one("#experiment-boundary", Static)
            )
            assert app.query_one("#experiment-data-input", TextArea).text == ""
            assert app.query_one("#experiment-output-input", Input).value == ""
            assert t("experiment_calculate_step") in str(
                app.query_one("#experiment-calculate", Button).label
            )
            assert t("experiment_submit_step") in str(
                app.query_one("#experiment-submit", Button).label
            )
            assert t("experiment_save_log") in str(
                app.query_one("#experiment-save-log", Button).label
            )

    asyncio.run(scenario())
