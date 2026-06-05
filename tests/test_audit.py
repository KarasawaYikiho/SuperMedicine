from __future__ import annotations

import json
import stat
import permission.audit as audit
from permission.audit import AuditLogger


class TestAuditLogger:
    def test_log_entry_creation(self, tmp_path):
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file)
        logger.log(
            agent_id="test-agent",
            action="tool.execute",
            resource="python/stats",
            result="DENIED",
            reason="blacklist_match",
        )
        assert log_file.exists()
        entry = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert entry["agent_id"] == "test-agent"
        assert entry["result"] == "DENIED"
        assert "timestamp" in entry

    def test_multiple_entries(self, tmp_path):
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file)
        logger.log(
            agent_id="a1",
            action="act1",
            resource="r1",
            result="ALLOWED",
            reason="whitelist",
        )
        logger.log(
            agent_id="a2",
            action="act2",
            resource="r2",
            result="DENIED",
            reason="default_deny",
        )
        assert len(log_file.read_text(encoding="utf-8").strip().split("\n")) == 2

    def test_audit_log_redacts_secret_values(self, tmp_path):
        log_file = tmp_path / "audit.log"
        secret = "sk-audit-secret-value"
        logger = AuditLogger(log_file)

        logger.log(
            agent_id="agent-token=abc123",
            action="llm.call",
            resource=f"https://example.test/v1?api_key={secret}",
            result="DENIED",
            reason=f"Authorization=Bearer {secret}",
        )

        text = log_file.read_text(encoding="utf-8")
        entry = json.loads(text)
        assert secret not in text
        assert (
            "api_key=[REDACTED]" in entry["resource"] or "api_key=" in entry["resource"]
        )
        assert "[REDACTED]" in text

    def test_audit_log_redacts_experiment_plugin_resource_and_reason(self, tmp_path):
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file)

        logger.log(
            agent_id="experiment-agent",
            action="execute",
            resource="experiment.wb.normalize_loading?token=wb-secret-token",
            result="DENIED",
            reason="external_api blocked api_key=sk-experiment-audit-secret",
        )

        text = log_file.read_text(encoding="utf-8")
        entry = json.loads(text)
        assert entry["action"] == "execute"
        assert entry["result"] == "DENIED"
        assert "wb-secret-token" not in text
        assert "sk-experiment-audit-secret" not in text
        assert "[REDACTED]" in entry["resource"]
        assert "[REDACTED]" in entry["reason"]

    def test_audit_log_redacts_headers_cookies_password_and_private_key(self, tmp_path):
        log_file = tmp_path / "audit.log"
        secret = "sk-audit-header-secret"
        private_material = "MIIEvauditprivatekeymaterial"
        logger = AuditLogger(log_file)

        logger.log(
            agent_id="agent-cookie=session-cookie-secret",
            action="http.request",
            resource=f"https://example.test/cb?code={secret}&state=ok",
            result="DENIED",
            reason=(
                f"headers Authorization: Bearer {secret}; Cookie=sid=audit-cookie-secret; "
                "password=audit-password; private_key=-----BEGIN PRIVATE KEY-----\n"
                f"{private_material}\n-----END PRIVATE KEY-----"
            ),
        )

        text = log_file.read_text(encoding="utf-8")
        entry = json.loads(text)
        assert entry["resource"].endswith("state=ok")
        for secret_value in (
            secret,
            "session-cookie-secret",
            "audit-cookie-secret",
            "audit-password",
            private_material,
        ):
            assert secret_value not in text
        assert text.count("[REDACTED]") >= 5

    def test_new_audit_log_is_owner_only_when_platform_supports_modes(self, tmp_path):
        log_file = tmp_path / "audit.log"

        AuditLogger(log_file).log("a1", "act", "resource", "ALLOWED", "reason")

        probe_file = tmp_path / "chmod-probe.tmp"
        probe_file.write_text("probe", encoding="utf-8")
        try:
            probe_file.chmod(0o600)
        except OSError:
            # This branch only means POSIX stat-mode observation is unavailable
            # here; it does not verify Windows ACL-level owner-only protection.
            return

        probe_mode = stat.S_IMODE(probe_file.stat().st_mode)
        can_observe_owner_only_mode = (
            probe_mode & stat.S_IWOTH == 0 and probe_mode & stat.S_IROTH == 0
        )
        if not can_observe_owner_only_mode:
            # The platform/filesystem did not reflect chmod(0o600) via stat()
            # mode bits, so POSIX owner-only bits cannot be asserted here. This
            # is not evidence that Windows ACL-level owner-only access was
            # verified.
            return

        mode = stat.S_IMODE(log_file.stat().st_mode)
        assert mode & stat.S_IWOTH == 0
        assert mode & stat.S_IROTH == 0

    def test_chmod_failure_emits_redacted_warning(self, tmp_path, monkeypatch, caplog):
        log_file = tmp_path / "audit.log"
        secret = "sk-audit-chmod-secret"
        logger = AuditLogger(log_file)

        def fail_chmod(path, mode=0o600):
            raise OSError(f"chmod failed api_key={secret}")

        caplog.set_level("WARNING", logger="permission.audit")
        monkeypatch.setattr(audit, "restrict_file_permissions", fail_chmod)
        logger.log("a1", "act", "resource", "ALLOWED", "reason")

        assert "audit_log_permission_restriction_failed" in caplog.text
        assert secret not in caplog.text
