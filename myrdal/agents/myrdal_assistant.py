from autogen_agentchat.agents import AssistantAgent
from myrdal.memory.manager import MemoryManager
from myrdal.metacognition.metacognition import MetacognitionFramework
from myrdal.knowledge.abstract_thinking import AbstractThinking
from myrdal.knowledge.multilingual import MultilingualUnderstanding
from myrdal.knowledge.explainable_ai import ExplainableAI
from myrdal.knowledge.social_cognition import SocialCognition
from myrdal.knowledge.knowledge_integration import KnowledgeIntegration
from autogen_core.models import ChatCompletionClient
import json

class MyrdalAssistantAgent(AssistantAgent):
    def __init__(self, *, agent_id: str, memory, memory_manager: MemoryManager, chat_client: ChatCompletionClient, model=None, feature_names=None, **kwargs):
        super().__init__(agent_id=agent_id, memory=memory)
        self.memory_manager = memory_manager
        # 知識モジュールの初期化
        self.knowledge_modules = {
            "abstract_thinking": AbstractThinking(),
            "multilingual": MultilingualUnderstanding(),
            "explainable_ai": ExplainableAI(model, feature_names),
            "social_cognition": SocialCognition(),
            "knowledge_integration": KnowledgeIntegration(),
        }
        # chat_client（ChatCompletionClientベース）を必須でMetacognitionFrameworkに渡す
        self.metacognition = MetacognitionFramework(self.knowledge_modules, chat_client=chat_client)

    async def on_messages_stream(self, messages, sender, config=None, **kwargs):
        context = {"messages": messages, "goal": kwargs.get("goal")}
        async for chunk in self.metacognition.deliberate_stream(context):
            # chunk.contentはJSON文字列
            try:
                result = json.loads(chunk.content)
            except Exception:
                result = {"thought": chunk.content, "call_module": None, "call_args": {}, "satisfied": False, "final_answer": None}
            yield {"type": "thought", "content": result.get("thought", "")}
            if result["call_module"]:
                module = self.knowledge_modules.get(result["call_module"])
                if module:
                    # モジュール呼び出し（非同期）
                    method = getattr(module, result["call_args"].get("method", ""), None)
                    if method:
                        module_result = await method(**{k: v for k, v in result["call_args"].items() if k != "method"})
                        yield {"type": "module_result", "content": module_result}
            if result["satisfied"]:
                # satisfied=True時、AssistantAgentのfunction calling/外部ツール呼び出しロジックを利用
                async for event in super().on_messages_stream(messages, sender, config, **kwargs):
                    yield event
                break 