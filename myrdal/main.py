from typing import Optional, AsyncGenerator, Any
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_core.memory import ListMemory
from autogen_agentchat.agents import BaseChatAgent
from autogen_core import CancellationToken
from autogen_agentchat.teams import SelectorGroupChat
from myrdal.memory.manager import MemoryManager
from myrdal.memory.short_term import ShortTermMemory
from myrdal.memory.long_term import LongTermMemory
from myrdal.agents import MyrdalAssistantAgent

# --- MemoryManager ---
class MemoryManager:
    def __init__(self):
        self.agent_memories = {}
    def get_agent_memory(self, agent_id: str):
        if agent_id not in self.agent_memories:
            self.agent_memories[agent_id] = ListMemory()
        return self.agent_memories[agent_id]

# --- MyrdalSpec 3〜16の拡張コンポーネント例（スタブ） ---
class WorldModelNexus:
    pass
class CausalReasoner:
    pass
class AbstractThinking:
    pass
class MetaCognition:
    pass
# ...他にも必要に応じて追加

# --- CustomAgent ---
class MyrdalCustomAgent(BaseChatAgent):
    def __init__(self, name, memory, long_term_memory=None, world_model=None, causal_reasoner=None, abstract_thinking=None, meta_cognition=None, **kwargs):
        super().__init__(name, description=kwargs.get("description", ""))
        self.memory = memory  # ListMemory（短期記憶）
        self.long_term_memory = long_term_memory
        self.world_model = world_model
        self.causal_reasoner = causal_reasoner
        self.abstract_thinking = abstract_thinking
        self.meta_cognition = meta_cognition
        # ...他の拡張もここで受け取れる

    @property
    def produced_message_types(self):
        return (TextMessage,)

    async def on_messages(self, messages, cancellation_token: CancellationToken):
        # 短期記憶（ListMemory）への保存例
        for msg in messages:
            await self.memory.add(msg)
        # 長期記憶やworld_model、因果推論なども必要に応じて利用
        # ...
        return Response(chat_message=TextMessage(content=f"{self.name}応答例", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken):
        await self.memory.clear()

# --- Myrdal本体 ---
class Myrdal:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.agents = {}
        # 各種拡張コンポーネントのインスタンス生成（本実装時はDIやFactoryで動的に切り替えも可）
        self.long_term_memory = LongTermMemory()
        self.world_model = WorldModelNexus()
        self.causal_reasoner = CausalReasoner()
        self.abstract_thinking = AbstractThinking()
        self.meta_cognition = MetaCognition()
        self.is_active = False
        self.current_messages = []
        self.agents = self._create_agent_team()
        self.team = SelectorGroupChat(
            agents=self.agents,
            selector_func=self._selector_func,
            memory=self.memory_manager.get_agent_memory("group"),
        )
        self._last_task: Optional[str] = None

    def _create_agent_team(self):
        # Agentごとに必要な拡張を割り当てる
        agents = [
            MyrdalCustomAgent(
                name="orchestrator",
                memory=self.memory_manager.get_agent_memory("orchestrator"),
                long_term_memory=self.long_term_memory,
                world_model=self.world_model,
            ),
            MyrdalCustomAgent(
                name="reasoner",
                memory=self.memory_manager.get_agent_memory("reasoner"),
                long_term_memory=self.long_term_memory,
                causal_reasoner=self.causal_reasoner,
                abstract_thinking=self.abstract_thinking,
            ),
            MyrdalCustomAgent(
                name="meta_controller",
                memory=self.memory_manager.get_agent_memory("meta_controller"),
                meta_cognition=self.meta_cognition,
            ),
            # ...他のAgentも必要な拡張を割り当てて追加
        ]
        return agents

    def _selector_func(self, messages, agents, **kwargs):
        # 仮実装: 最初のエージェントを選択
        return 0

    async def inteact_with_myrdal(self, message: str) -> None:
        if not self.is_active:
            self.is_active = True
        await self.memory_manager.get_agent_memory("user").add(TextMessage(content=message, source="user"))
        self.current_messages.append({"role": "user", "content": message})
        self._last_task = message

    def pause(self) -> None:
        self.is_active = False

    async def get_responses_async(self) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        if not self.is_active or not self._last_task:
            return
        async for event in self.team.run_stream(task=self._last_task):
            if hasattr(event, "message") and hasattr(event.message, "content"):
                await self.memory_manager.get_agent_memory("assistant").add(event.message)
                self.current_messages.append({"role": "assistant", "content": event.message.content})
            yield event

    def create_agent(self, agent_id: str, **knowledge_modules):
        short_term = self.memory_manager.get_short_term(agent_id)
        agent = MyrdalAssistantAgent(
            agent_id=agent_id,
            memory=short_term,
            memory_manager=self.memory_manager,
            **knowledge_modules
        )
        self.agents[agent_id] = agent
        return agent