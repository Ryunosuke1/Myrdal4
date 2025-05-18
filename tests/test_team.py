import pytest
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage

class DummyAgent(BaseChatAgent):
    def __init__(self, name):
        super().__init__(name)
    @property
    def produced_message_types(self):
        return (TextMessage,)
    async def on_messages(self, messages, cancellation_token):
        return TextMessage(content=f"{self.name}応答", source=self.name)

@pytest.mark.asyncio
async def test_selector_group_chat():
    agents = [DummyAgent("a1"), DummyAgent("a2")]
    def selector_func(messages, agents, **kwargs):
        return 1  # 常に2番目のエージェント
    team = SelectorGroupChat(agents=agents, selector_func=selector_func)
    # run_streamは本来非同期ストリームだが、ここでは初期化のみテスト
    assert team.agents[1].name == "a2" 