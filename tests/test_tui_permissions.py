"""Tests for permission UI input separation and FULL confirmation logic."""

from __future__ import annotations

import pytest

from core.tui.screens.permission_screen import (
    PermissionScreenController,
    PermissionView,
    PERMISSION_RISK_NOTICE,
)
from permission.access_mode import (
    FullAccessConfirmationRequired,
)


# ═══ PermissionScreenController Tests ═══


class TestPermissionScreenController:
    """Test the TUI permission controller in isolation."""

    def test_set_mode_conservative_without_confirmation(self, tmp_path):
        """Conservative mode does not require FULL confirmation text."""
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("conservative")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_set_mode_full_requires_full_confirmation_text(self, tmp_path):
        """FULL mode requires exact 'FULL' confirmation text."""
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("full", confirmation_text="FULL")

        assert result["mode"] == "full"
        assert result["full_mode_confirmed"] is True

    def test_set_mode_full_without_confirmation_text_raises(self, tmp_path):
        """FULL mode without 'FULL' text raises FullAccessConfirmationRequired."""
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="")

    def test_set_mode_full_with_wrong_confirmation_text_raises(self, tmp_path):
        """FULL mode with incorrect confirmation text raises."""
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="full")

    def test_set_mode_full_with_whitespace_confirmation_raises(self, tmp_path):
        """FULL mode with whitespace-only confirmation text raises."""
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="   ")

    def test_set_mode_conservative_ignores_confirmation_text(self, tmp_path):
        """Conservative mode ignores any confirmation text."""
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("conservative", confirmation_text="anything")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_set_mode_persists_to_config_file(self, tmp_path):
        """Mode changes persist through save/reload cycle."""
        controller = PermissionScreenController(tmp_path)
        controller.set_mode("full", confirmation_text="FULL")

        # Reload from disk
        reloaded = PermissionScreenController(tmp_path)
        config = reloaded.current_config()

        assert config["mode"] == "full"
        assert config["full_mode_confirmed"] is True

    def test_set_mode_switches_from_full_back_to_conservative(self, tmp_path):
        """Switching from FULL back to conservative clears full_mode_confirmed."""
        controller = PermissionScreenController(tmp_path)
        controller.set_mode("full", confirmation_text="FULL")
        result = controller.set_mode("conservative")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_authorize_directory_adds_to_config(self, tmp_path):
        """Authorizing a directory persists it in the config."""
        external = tmp_path / "external"
        external.mkdir()
        controller = PermissionScreenController(tmp_path)

        result = controller.authorize_directory(external)

        assert str(external.resolve()) in result["authorized_external_roots"]

    def test_revoke_directory_removes_from_config(self, tmp_path):
        """Revoking a directory removes it from authorized roots."""
        external = tmp_path / "external"
        external.mkdir()
        controller = PermissionScreenController(tmp_path)
        controller.authorize_directory(external)

        result = controller.revoke_directory(external)

        assert str(external.resolve()) not in result["authorized_external_roots"]

    def test_access_decision_returns_correct_structure(self, tmp_path):
        """access_decision returns a complete serializable dict."""
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(project / "notes.md", "write")

        assert decision["status"] == "allowed"
        assert decision["mode"] == "conservative"
        assert isinstance(decision["reason"], str)
        assert isinstance(decision["path"], str)
        assert isinstance(decision["helper"], str)

    def test_access_decision_external_write_denied_in_conservative(self, tmp_path):
        """External writes are denied in conservative mode."""
        project = tmp_path / "project"
        external = tmp_path / "external"
        project.mkdir()
        external.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(external / "out.csv", "write")

        assert decision["status"] == "denied"

    def test_access_decision_external_read_prompts_in_conservative(self, tmp_path):
        """External reads return prompt_required in conservative mode."""
        project = tmp_path / "project"
        external = tmp_path / "external"
        project.mkdir()
        external.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(external / "data.csv", "read")

        assert decision["status"] == "prompt_required"

    def test_current_config_returns_default_when_no_config_file(self, tmp_path):
        """current_config returns safe defaults when no config file exists."""
        controller = PermissionScreenController(tmp_path)
        config = controller.current_config()

        assert config["mode"] == "conservative"
        assert config["full_mode_confirmed"] is False
        assert config["authorized_external_roots"] == []

    def test_project_root_defaults_to_cwd(self, tmp_path, monkeypatch):
        """Controller defaults project_root to cwd when not specified."""
        monkeypatch.chdir(tmp_path)
        controller = PermissionScreenController()

        assert controller.project_root == tmp_path


# ═══ PermissionView Widget Composition Tests ═══


class TestPermissionViewComposition:
    """Test that PermissionView composes the expected UI widgets."""

    def test_permission_view_has_separate_mode_select_and_confirm_input(self):
        """Mode selection and FULL confirmation are separate input widgets."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert "permission-mode-select" in source
        assert "permission-confirm-input" in source
        # They are distinct widgets
        assert "Select" in source
        assert "Input" in source

    def test_permission_view_has_add_and_remove_root_controls(self):
        """Root authorization has separate add/remove controls."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert "permission-root-input" in source
        assert "permission-add-root" in source
        assert "permission-remove-root" in source

    def test_permission_view_has_refresh_button(self):
        """Permission view includes a refresh control."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert "permission-refresh" in source

    def test_permission_view_has_status_and_risk_notice(self):
        """Permission view displays status and risk notice."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert "permission-status" in source
        assert "permission-risk" in source
        assert "permission-current" in source

    def test_permission_risk_notice_mentions_full_confirmation(self):
        """Risk notice documents FULL mode confirmation requirement."""
        assert "FULL" in PERMISSION_RISK_NOTICE
        assert "显式确认" in PERMISSION_RISK_NOTICE

    def test_permission_risk_notice_mentions_no_silent_escalation(self):
        """Risk notice documents no silent privilege escalation."""
        assert "不会静默提权" in PERMISSION_RISK_NOTICE
        assert "不会绕过" in PERMISSION_RISK_NOTICE


# ═══ Permission Input Separation Tests ═══


class TestPermissionInputSeparation:
    """Test that mode switching and FULL confirmation are correctly separated."""

    def test_mode_select_widget_offers_conservative_and_full(self):
        """Select widget offers both conservative and full modes."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert '"conservative"' in source
        assert '"full"' in source

    def test_confirm_input_placeholder_documents_full_requirement(self):
        """Confirmation input placeholder explains FULL requirement."""
        import inspect

        source = inspect.getsource(PermissionView.compose)

        assert "FULL" in source

    def test_controller_uses_separate_mode_and_confirmation(self, tmp_path):
        """Controller independently processes mode value and confirmation text."""
        controller = PermissionScreenController(tmp_path)

        # Mode "conservative" doesn't need confirmation
        result1 = controller.set_mode("conservative")
        assert result1["mode"] == "conservative"

        # Mode "full" with proper confirmation
        result2 = controller.set_mode("full", confirmation_text="FULL")
        assert result2["mode"] == "full"

        # Mode "full" without confirmation fails
        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="")

    def test_handle_input_submit_routes_confirm_input_to_set_mode(self):
        """handle_input_submit routes confirm-input to set_mode logic."""
        import inspect

        source = inspect.getsource(PermissionView.handle_input_submit)

        assert "permission-confirm-input" in source
        assert "_set_mode_from_form" in source

    def test_handle_input_submit_routes_root_input_to_add_root(self):
        """handle_input_submit routes root-input to add_root logic."""
        import inspect

        source = inspect.getsource(PermissionView.handle_input_submit)

        assert "permission-root-input" in source
        assert "_add_root_from_form" in source

    def test_set_mode_from_form_clears_confirmation_input_after_success(self, tmp_path):
        """After successful mode switch, confirmation input is cleared."""
        import inspect

        source = inspect.getsource(PermissionView._set_mode_from_form)

        # Should clear confirmation input after mode switch
        assert 'permission-confirm-input' in source
        assert '.value = ""' in source


# ═══ Controller Save Integration Tests ═══


class TestPermissionControllerSaveIntegration:
    """Test that controller operations properly persist config."""

    def test_authorize_then_access_decision_allows(self, tmp_path):
        """Authorizing a directory makes subsequent access decisions allow."""
        external = tmp_path / "external"
        external.mkdir()
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.authorize_directory(external)
        decision = controller.access_decision(external / "file.txt", "write")

        assert decision["status"] == "allowed"

    def test_revoke_then_access_decision_denies(self, tmp_path):
        """Revoking a directory makes subsequent access decisions deny."""
        external = tmp_path / "external"
        external.mkdir()
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.authorize_directory(external)
        controller.revoke_directory(external)
        decision = controller.access_decision(external / "file.txt", "write")

        assert decision["status"] == "denied"

    def test_full_mode_access_decision_allows_external(self, tmp_path):
        """FULL mode allows external path access decisions."""
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.set_mode("full", confirmation_text="FULL")
        decision = controller.access_decision(tmp_path / "anywhere" / "file.txt", "write")

        assert decision["status"] == "allowed"
        assert decision["mode"] == "full"
