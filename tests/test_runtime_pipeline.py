from __future__ import annotations

from agents.checkpoint import CheckpointManager
from core.runtime_pipeline import HarnessRuntime
from plugins.harness.monitor import AgentPerformanceMonitor


def test_harness_runtime_finalizes_a_run_once_and_records_performance(tmp_path):
    checkpoints = CheckpointManager(tmp_path / "checkpoints")
    monitor = AgentPerformanceMonitor(tmp_path / "performance.jsonl")
    runtime = HarnessRuntime(checkpoints, monitor)

    run = runtime.begin(task="summarize evidence", entrypoint="cli", agent_mode="single")
    runtime.stage(run, "rag", rag_status="empty")
    final = runtime.finalize(run, status="success", output={"answer": "ok"})
    repeated = runtime.finalize(run, status="failed")

    assert run.run_id != ""
    assert final["finalized"] is True
    assert repeated == final
    assert checkpoints.load_latest(run.run_id)["state"] == "completed"
    assert monitor.get_stats("alpha")["alpha"]["total"] == 1
