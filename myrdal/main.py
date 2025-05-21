import pickle
from typing import Optional, AsyncGenerator, Any
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.base import TaskResult, Response
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_agentchat.agents import BaseChatAgent
from autogen_core import CancellationToken
from autogen_agentchat.teams import SelectorGroupChat
from myrdal.memory.manager import MemoryManager
from myrdal.memory.short_term import ShortTermMemory
from myrdal.memory.long_term import LongTermMemory
from myrdal.agents import MyrdalAssistantAgent
from autogen_core.models import ChatCompletionClient
import json
import os
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from myrdal.knowledge.world_model_nexus import WorldModelNexus
from myrdal.reasoning.causal_reasoner import CausalReasoner
from myrdal.knowledge.multilayer_knowledge_graph import MultiLayerKnowledgeGraph
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import ThoughtEvent
import os


# --- MemoryManager ---
# class MemoryManager:
#     def __init__(self):
#         self.agent_memories = {}
#     def get_agent_memory(self, agent_id: str):
#         if agent_id not in self.agent_memories:
#             self.agent_memories[agent_id] = ListMemory()
#         return self.agent_memories[agent_id]

# # --- MyrdalSpec 3〜16の拡張コンポーネント例（スタブ） ---
# class WorldModelNexus:
#     pass
# class CausalReasoner:
#     pass
# class AbstractThinking:
#     pass
# class MetaCognition:
#     pass
# # ...他にも必要に応じて追加

# # --- CustomAgent ---
# class MyrdalCustomAgent(BaseChatAgent):
#     def __init__(self, name, memory, long_term_memory=None, world_model=None, causal_reasoner=None, abstract_thinking=None, meta_cognition=None, **kwargs):
#         super().__init__(name, description=kwargs.get("description", ""))
#         self.memory = memory  # ListMemory（短期記憶）
#         self.long_term_memory = long_term_memory
#         self.world_model = world_model
#         self.causal_reasoner = causal_reasoner
#         self.abstract_thinking = abstract_thinking
#         self.meta_cognition = meta_cognition
#         # ...他の拡張もここで受け取れる

#     @property
#     def produced_message_types(self):
#         return (TextMessage,)

#     async def on_messages(self, messages, cancellation_token: CancellationToken):
#         # 短期記憶（ListMemory）への保存例
#         for msg in messages:
#             await self.memory.add(msg)
#         # 長期記憶やworld_model、因果推論なども必要に応じて利用
#         # ...
#         return Response(chat_message=TextMessage(content=f"{self.name}応答例", source=self.name))

#     async def on_reset(self, cancellation_token: CancellationToken):
#         await self.memory.clear()

# --- Myrdal本体 ---
class Myrdal:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.agents = {}
        self.is_active = False
        self.current_messages = []
        self._last_task: Optional[str] = None
        # 非同期初期化は外部からainit_team()をawaitして呼ぶ

    async def ainit_team(self, mcp_config_path="mcp.json"):
        # ChatCompletionClientのインスタンスを作成
        if os.path.isfile("myrdal_pickle.pkl"):
            with open("myrdal_pickle.pkl", "w+b", ) as f:
                self.team = pickle.load(f)
            return
        llm_client = OpenAIChatCompletionClient(
            model="tngtech/deepseek-r1t-chimera:free", 
            api_key="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", 
            base_url="https://openrouter.ai/api/v1", 
            model_info={
                "function_calling": True,
                "family": "unknown",
                "json_output": True,
                "structured_output": True,
                "vision": False,
                "multiple_system_messages": True,
            },
        )
        # MCPサーバー設定を読み込む
        mcp_tools = []
        if os.path.exists(mcp_config_path):
            with open(mcp_config_path, "r") as f:
                mcp_conf = json.load(f)
            mcp_servers = mcp_conf.get("mcpServers", {})
            for name, server in mcp_servers.items():
                params = StdioServerParams(
                    command=server["command"],
                    args=server.get("args", []),
                    env=server.get("env", None),
                )
                workbench = McpWorkbench(server_params=params)
                await workbench.start()
                tools = await workbench.list_tools()
                mcp_tools.extend(tools)
                await workbench.stop()
        # WorldModelNexusをchat_clientとして渡す
        wmn = WorldModelNexus(chat_client=llm_client)
        self.agents = [
            MyrdalAssistantAgent(
                agent_id="myrdal_assistant",
                memory=[self.memory_manager.get_short_term("myrdal_assistant")],
                memory_manager=self.memory_manager,
                model_client=wmn,
                mcp_tools=mcp_tools,
                stream=True,
            ),
            MyrdalAssistantAgent(
                agent_id="verifier",
                memory=[self.memory_manager.get_short_term("verifier")],
                memory_manager=self.memory_manager,
                model_client=wmn,
                system_message="You are a knowledge verifier. Organize, merge, and validate knowledge. Also, Check the user's request is successfully completed and reply 'The conversation is over.' in a sentence.",
                mcp_tools=mcp_tools,
                stream=True
            ),
        ]
        self.team = SelectorGroupChat(
            participants=self.agents,
            model_client=llm_client,
        )

    def _selector_func(self, messages, agents, **kwargs):
        # 例: 最初のエージェントを選択（高度化可）
        return 0

    async def interact_with_myrdal(self, message: str, resume: bool = False) -> None:
        """
        従来のインタラクションメソッド（下位互換性のために維持）
        新しい実装ではinteract_and_get_responsesを使用してください
        """
        if not self.is_active or not resume:
            self.is_active = True
            self.current_messages = []
        self.current_messages.append({"role": "user", "content": message})
        self._last_task = message

    def pause(self) -> None:
        self.is_active = False
        self.team.pause()
        with open("myrdal_pickle.pkl", "wb") as f:
            pickle.dump(self.team, f)

    async def get_responses_async(self) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        従来のレスポンス取得メソッド（下位互換性のために維持）
        新しい実装ではinteract_and_get_responsesを使用してください
        """
        if not self.is_active or not self._last_task:
            return
        async for event in self.team.run_stream(task=self._last_task):
            # inner_messagesもストリームで流す
            if hasattr(event, "messages") and event.messages:
                for inner in event.model_dump():
                    yield inner
            if hasattr(event, "message") and hasattr(event.message, "content"):
                await self.memory_manager.get_agent_memory("assistant").add(event.message)
                self.current_messages.append({"role": "assistant", "content": event.message.content})
            print("----------------------------------------------------------------")
            print(event)
            print("----------------------------------------------------------------")
            yield event
            
    async def interact_and_get_responses(self, message: str, resume: bool = False) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        interact_with_myrdalとget_responses_asyncを統合した新しいメソッド
        メッセージを送信し、そのレスポンスをストリームとして直接返します
        
        Args:
            message (str): ユーザーからのメッセージ
            resume (bool, optional): 会話を再開するかどうか. デフォルトはFalse
            
        Yields:
            AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]: レスポンスイベントのストリーム
        """
        # 状態の設定（interact_with_myrdalと同様）
        if not self.is_active or not resume:
            self.is_active = True
            self.current_messages = []
        self.current_messages.append({"role": "user", "content": message})
        self._last_task = message
        
        # レスポンスの取得と生成（get_responses_asyncと同様）
        if not self.is_active or not self._last_task:
            return
        async for event in self.team.run_stream(task=self._last_task):
            # イベントの詳細構造を出力（デバッグ用）
            print("===== イベントタイプ =====")
            print(type(event))
            print("===== イベント内容 =====")
            if hasattr(event, "model_dump"):
                print(event.model_dump_json())
            else:
                print(event)
            print("===== 属性チェック =====")
            print(f"has 'inner_messages': {hasattr(event, 'inner_messages')}")
            print(f"has 'message': {hasattr(event, 'message')}")
            print(f"has 'messages': {hasattr(event, 'messages')}")
            
            # すべてのイベントをそのまま転送
            yield event

    def resume(self):
        self.is_active = True
        # 必要に応じてcurrent_messagesや状態を復元

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