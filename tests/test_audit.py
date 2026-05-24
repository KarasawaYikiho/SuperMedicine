import json
from permission.audit import AuditLogger

class TestAuditLogger:
    def test_log_entry_creation(self, tmp_path):
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file)
        logger.log(agent_id="test-agent", action="tool.execute", resource="python/stats", result="DENIED", reason="blacklist_match")
        assert log_file.exists()
        entry = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert entry["agent_id"] == "test-agent"
        assert entry["result"] == "DENIED"
        assert "timestamp" in entry
    def test_multiple_entries(self, tmp_path):
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file)
        logger.log(agent_id="a1", action="act1", resource="r1", result="ALLOWED", reason="whitelist")
        logger.log(agent_id="a2", action="act2", resource="r2", result="DENIED", reason="default_deny")
        assert len(log_file.read_text(encoding="utf-8").strip().split("\n")) == 2
