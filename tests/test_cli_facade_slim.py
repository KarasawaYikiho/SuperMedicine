from __future__ import annotations

from cli_entry import CLI


def test_cli_facade_keeps_forwarded_commands_out_of_class_dict(monkeypatch):
    from cli.commands import workspace

    def fake_workspace_list(cli):
        assert isinstance(cli, CLI)
        return [{"id": "demo"}]

    monkeypatch.setattr(workspace, "workspace_list", fake_workspace_list)

    assert "workspace_list" not in CLI.__dict__
    assert CLI().workspace_list() == [{"id": "demo"}]


def test_cli_facade_forwards_keyword_arguments(monkeypatch):
    from cli.commands import tool

    def fake_tool_add(cli, workspace_id, selections=None, *, language=None, overwrite=False):
        assert isinstance(cli, CLI)
        return {
            "workspace": workspace_id,
            "selections": selections,
            "language": language,
            "overwrite": overwrite,
        }

    monkeypatch.setattr(tool, "tool_add", fake_tool_add)

    assert "tool_add" not in CLI.__dict__
    assert CLI().tool_add(
        "trial",
        selections=["1"],
        language="python",
        overwrite=True,
    ) == {
        "workspace": "trial",
        "selections": ["1"],
        "language": "python",
        "overwrite": True,
    }


def test_cli_facade_forwards_llm_commands(monkeypatch):
    from cli.commands import llm

    def fake_llm_list(cli):
        assert isinstance(cli, CLI)
        return {"providers": []}

    monkeypatch.setattr(llm, "llm_list", fake_llm_list)

    assert "llm_list" not in CLI.__dict__
    assert CLI().llm_list() == {"providers": []}


def test_cli_facade_exposes_persisted_multi_agent_switch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli = CLI()

    assert cli.multi_agent_status() == {"enabled": False}
    enabled = cli.multi_agent_set(True)

    assert enabled["enabled"] is True
    assert "四角色" in enabled["message"]
    assert CLI().multi_agent_status() == {"enabled": True}


def test_cli_parser_can_enable_and_disable_multi_agent(tmp_path, monkeypatch):
    from cli.parser import main

    monkeypatch.chdir(tmp_path)

    main(["multi-agent", "enable"])
    assert CLI().multi_agent_status()["enabled"] is True
    main(["multi-agent", "disable"])
    assert CLI().multi_agent_status()["enabled"] is False
