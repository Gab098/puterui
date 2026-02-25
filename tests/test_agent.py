"""Tests for agent workflow helpers."""

import pytest

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


@pytest.mark.asyncio
async def test_fallback_when_model_does_not_support_tools(tmp_path, monkeypatch):
    from puterui.client import OllamaError

    agent = Agent(Config(), tmp_path)
    calls = []

    class FakeClient:
        async def chat(self, messages, tools=None):
            calls.append(tools)
            if tools is not None:
                raise OllamaError(
                    "Ollama API error (400): model does not support tools"
                )
            return {
                "message": {
                    "role": "assistant",
                    "content": "hello text-only",
                    "tool_calls": [],
                }
            }

    warnings = []
    monkeypatch.setattr("puterui.ui.print_warning", lambda msg: warnings.append(msg))
    monkeypatch.setattr("puterui.ui.print_assistant", lambda _msg: None)

    agent.client = FakeClient()
    agent.messages.append({"role": "user", "content": "hi"})

    result = await agent._run_agent_loop()

    assert result == "hello text-only"
    assert calls[0] is not None
    assert calls[1] is None
    assert any("text-only mode" in msg for msg in warnings)


@pytest.mark.asyncio
async def test_tools_disabled_persist_after_detection(tmp_path, monkeypatch):
    agent = Agent(Config(), tmp_path)
    agent._tools_supported = False

    seen_tools = []

    class FakeClient:
        async def chat(self, messages, tools=None):
            seen_tools.append(tools)
            return {"message": {"role": "assistant", "content": "ok", "tool_calls": []}}

    agent.client = FakeClient()
    monkeypatch.setattr("puterui.ui.print_assistant", lambda _msg: None)
    agent.messages.append({"role": "user", "content": "hello"})

    result = await agent._run_agent_loop()
    assert result == "ok"
    assert seen_tools == [None]


def test_model_switch_resets_tool_capability_flag(tmp_path):
    agent = Agent(Config(), tmp_path)
    agent._tools_supported = False

    agent.on_model_switch()

    assert agent._tools_supported is True


@pytest.mark.asyncio
async def test_task_log_records_prompt_and_response(tmp_path, monkeypatch):
    agent = Agent(Config(), tmp_path)

    class FakeClient:
        async def chat_stream(self, messages, tools=None):
            yield {"message": {"role": "assistant", "content": "Hello"}}
            yield {"message": {"role": "assistant", "content": " world"}}

    monkeypatch.setattr("puterui.ui.print_stream_start", lambda: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_start", lambda: None)
    monkeypatch.setattr("puterui.ui.print_stream_chunk", lambda _text: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_chunk", lambda _text: None)
    monkeypatch.setattr("puterui.ui.print_stream_end", lambda: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_end", lambda: None)

    agent.client = FakeClient()
    result = await agent.send("hi there")

    assert result == "Hello world"
    log_path = tmp_path / ".puterui" / "tasks.log"
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert '"event": "user_prompt"' in log_text
    assert '"event": "assistant_response"' in log_text


@pytest.mark.asyncio
async def test_streaming_response_skips_panel_print(tmp_path, monkeypatch):
    agent = Agent(Config(), tmp_path)

    class FakeClient:
        async def chat_stream(self, messages, tools=None):
            yield {"message": {"role": "assistant", "content": "A"}}

    panel_calls: list[str] = []
    monkeypatch.setattr("puterui.ui.print_stream_start", lambda: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_start", lambda: None)
    monkeypatch.setattr("puterui.ui.print_stream_chunk", lambda _text: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_chunk", lambda _text: None)
    monkeypatch.setattr("puterui.ui.print_stream_end", lambda: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_end", lambda: None)
    monkeypatch.setattr("puterui.ui.print_assistant", lambda text: panel_calls.append(text))

    agent.client = FakeClient()
    result = await agent.send("stream please")

    assert result == "A"
    assert panel_calls == []


@pytest.mark.asyncio
async def test_read_timeout_warning_hint(tmp_path, monkeypatch):
    from puterui.client import OllamaError

    agent = Agent(Config(), tmp_path)

    class FakeClient:
        async def chat(self, messages, tools=None):
            raise OllamaError(
                "Connection error to http://localhost:11434 (model: x): ReadTimeout"
            )

    warnings: list[str] = []
    monkeypatch.setattr("puterui.ui.print_warning", lambda msg: warnings.append(msg))
    monkeypatch.setattr("puterui.ui.print_error", lambda _msg: None)

    agent.client = FakeClient()
    agent.messages.append({"role": "user", "content": "hi"})

    result = await agent._run_agent_loop()
    assert "ReadTimeout" in result
    assert any("ollama_read_timeout" in msg for msg in warnings)


@pytest.mark.asyncio
async def test_reasoning_stream_is_rendered(tmp_path, monkeypatch):
    agent = Agent(Config(), tmp_path)

    class FakeClient:
        async def chat_stream(self, messages, tools=None):
            yield {"message": {"role": "assistant", "thinking": "step 1. "}}
            yield {"message": {"role": "assistant", "thinking": "step 2. "}}
            yield {"message": {"role": "assistant", "content": "Done"}}

    reasoning_chunks: list[str] = []
    monkeypatch.setattr("puterui.ui.print_stream_start", lambda: None)
    monkeypatch.setattr("puterui.ui.print_stream_chunk", lambda _text: None)
    monkeypatch.setattr("puterui.ui.print_stream_end", lambda: None)
    monkeypatch.setattr("puterui.ui.print_reasoning_start", lambda: None)
    monkeypatch.setattr(
        "puterui.ui.print_reasoning_chunk",
        lambda text: reasoning_chunks.append(text),
    )
    monkeypatch.setattr("puterui.ui.print_reasoning_end", lambda: None)

    agent.client = FakeClient()
    result = await agent.send("why")

    assert result == "Done"
    assert "".join(reasoning_chunks) == "step 1. step 2. "
