"""Tests for agent workflow helpers."""

from puterui.agent import Agent
from puterui.config import Config


def test_mini_agent_lifecycle(tmp_path):
    agent = Agent(Config(), tmp_path)

    msg = agent.create_mini_agent("recon", "collect target surface")
    assert "created" in msg
    assert len(agent.list_mini_agents()) == 1

    msg = agent.update_mini_agent_status("recon", "running")
    assert "running" in msg
    assert agent.list_mini_agents()[0].status == "running"

    prompt = agent.get_mini_agents_prompt()
    assert "Active Mini-Agents" in prompt
    assert "recon [running]" in prompt

    msg = agent.remove_mini_agent("recon")
    assert "removed" in msg
    assert agent.list_mini_agents() == []


def test_mini_agent_validation(tmp_path):
    agent = Agent(Config(), tmp_path)

    assert "Error" in agent.create_mini_agent("", "goal")
    assert "Error" in agent.create_mini_agent("x", "")

    agent.create_mini_agent("x", "goal")
    assert "Error" in agent.update_mini_agent_status("x", "invalid")
    assert "Error" in agent.update_mini_agent_status("nope", "running")
    assert "Error" in agent.remove_mini_agent("nope")
