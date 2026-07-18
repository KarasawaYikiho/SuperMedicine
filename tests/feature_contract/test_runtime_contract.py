from __future__ import annotations

from pathlib import Path

from agents.alpha_agent import AlphaAgent
from agents.beta_agent import BetaAgent
from agents.delta_agent import DeltaAgent
from agents.gamma_agent import GammaAgent
from core.plugin_registry import PluginRegistry

def test_required_plugins_name_their_runtime_contract(manifest: dict[str, object]) -> None:
    required_plugins = [
        record
        for record in manifest["features"]
        if record["category"] == "plugin" and record.get("required")
    ]
    assert required_plugins
    assert {record["runtime_contract"] for record in required_plugins} == {
        "rag_local_query",
        "harness_checkpoint",
    }


def test_required_plugins_are_discovered(repository_root: Path) -> None:
    registry = PluginRegistry(repository_root / "plugins")
    discovered = {meta.name for meta in registry.discover()}
    assert {"rag-interface", "harness-core"} <= discovered


def test_four_agent_roles_are_preserved() -> None:
    agents = [AlphaAgent(), BetaAgent(), GammaAgent(), DeltaAgent()]
    assert {(agent.agent_id, agent.role) for agent in agents} == {
        ("alpha", "analyst"),
        ("beta", "reviewer"),
        ("gamma", "writer"),
        ("delta", "orchestrator"),
    }
