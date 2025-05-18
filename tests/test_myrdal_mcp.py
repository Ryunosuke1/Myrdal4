import pytest

# causal-learnのバージョン互換性テスト
def test_causal_learn_import():
    import causal_learn
    from packaging import version
    assert version.parse(causal_learn.__version__) <= version.parse("0.1.4.1")

# MyrdalAssistantAgentのMCPツール統合テスト
def test_myrdal_assistant_mcp_tools():
    from myrdal.agents import MyrdalAssistantAgent
    from myrdal.memory.manager import MemoryManager
    from autogen_core.models import ChatCompletionClient
    # ダミーMCPツール
    class DummyTool:
        name = "dummy"
    mcp_tools = [DummyTool()]
    agent = MyrdalAssistantAgent(
        agent_id="test",
        memory=MemoryManager().get_agent_memory("test"),
        memory_manager=MemoryManager(),
        chat_client=ChatCompletionClient(model="gpt-4o-2024-08-06"),
        mcp_tools=mcp_tools,
    )
    # tools属性にmcp_toolsが統合されているか
    assert any(t.name == "dummy" for t in agent.tools) 