from __future__ import annotations

from pathlib import Path

from agents.roles import ROLE_SPECS, AlphaAgent, BetaAgent, DeltaAgent, GammaAgent
from core.plugin_registry import PluginRegistry


def test_required_plugins_name_their_runtime_contract(
    manifest: dict[str, object],
) -> None:
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
    assert tuple(ROLE_SPECS) == ("alpha", "beta", "gamma", "delta")
    assert ROLE_SPECS["alpha"].next_role == "beta"
    assert ROLE_SPECS["beta"].next_role == "gamma"
    assert ROLE_SPECS["gamma"].next_role is None
    assert all(
        spec.prompt and spec.input_keys and spec.output_keys
        for spec in ROLE_SPECS.values()
    )
