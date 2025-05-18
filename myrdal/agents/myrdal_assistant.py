from autogen_agentchat.agents._assistant_agent import AssistantAgent
from myrdal.memory.manager import MemoryManager
from myrdal.metacognition.metacognition import MetacognitionFramework
from myrdal.knowledge.abstract_thinking import AbstractThinking
from myrdal.knowledge.multilingual import MultilingualUnderstanding
from myrdal.knowledge.explainable_ai import ExplainableAI
from myrdal.knowledge.social_cognition import SocialCognition
from myrdal.knowledge.knowledge_integration import KnowledgeIntegration
from autogen_core.models import ChatCompletionClient, AssistantMessage, CreateResult
from myrdal.reasoning.causal_reasoner import CausalReasoner
from autogen_agentchat.messages import ThoughtEvent, BaseAgentEvent, BaseChatMessage, ModelClientStreamingChunkEvent
from autogen_agentchat.base import Response
from typing import Sequence, AsyncGenerator, Union, List
from autogen_core import CancellationToken
import json
from pydantic import BaseModel

class MyrdalAssistantAgent(AssistantAgent):
    def __init__(self, *, agent_id: str, memory, memory_manager: MemoryManager, model_client: ChatCompletionClient, model=None, feature_names=None, tools=None, mcp_tools=None, system_message=None, **kwargs):
        # tools: 通常のツールリスト, mcp_tools: MCP経由のツールリスト
        all_tools = []
        if tools:
            all_tools.extend(tools)
        if mcp_tools:
            all_tools.extend(mcp_tools)
        super().__init__(name=agent_id, memory=memory, tools=all_tools, system_message=system_message, model_client=model_client)
        self.memory_manager = memory_manager
        # 知識モジュールの初期化
        # self.knowledge_modules = {
        #     "abstract_thinking": AbstractThinking(),
        #     "multilingual": MultilingualUnderstanding(),
        #     "explainable_ai": ExplainableAI(model, feature_names),
        #     "social_cognition": SocialCognition(),
        #     "knowledge_integration": KnowledgeIntegration(),
        #     "causal_reasoner": CausalReasoner(),
        # }
        # chat_client（ChatCompletionClientベース）を必須でMetacognitionFrameworkに渡す

    

    @classmethod
    async def _call_llm(
        cls,
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        system_messages: List,
        model_context,
        workbench,
        handoff_tools,
        agent_name: str,
        cancellation_token: CancellationToken,
        output_content_type: type[BaseModel] | None,
    ) -> AsyncGenerator[Union[CreateResult, ModelClientStreamingChunkEvent, ThoughtEvent], None]:
        """
        WMN(WorldModelNexus)のcreate_streamがThoughtEventを返す場合もサポート。
        ThoughtEvent, CreateResult, ModelClientStreamingChunkEventをすべてストリーミングでyieldする。
        """
        all_messages = await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=system_messages + all_messages)
        tools = (await workbench.list_tools()) + handoff_tools

        if model_client_stream:
            model_result = None
            async for chunk in model_client.create_stream(
                llm_messages,
                tools=tools,
                json_output=output_content_type,
                cancellation_token=cancellation_token,
            ):
                if isinstance(chunk, CreateResult):
                    model_result = chunk
                    yield model_result
                elif isinstance(chunk, ThoughtEvent):
                    yield chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
            if model_result is None:
                raise RuntimeError("No final model result in streaming mode.")
        else:
            model_result = await model_client.create(
                llm_messages,
                tools=tools,
                cancellation_token=cancellation_token,
                json_output=output_content_type,
            )
            yield model_result