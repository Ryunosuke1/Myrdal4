from autogen_core.models import ChatCompletionClient, CreateResult, ModelInfo, RequestUsage, UserMessage, AssistantMessage, SystemMessage
from typing import Sequence, Mapping, Any, AsyncGenerator
import json
from myrdal.knowledge.abstract_thinking import AbstractThinking
from myrdal.knowledge.multilingual import MultilingualUnderstanding
from myrdal.knowledge.explainable_ai import ExplainableAI
from myrdal.knowledge.social_cognition import SocialCognition
from myrdal.knowledge.knowledge_integration import KnowledgeIntegration
from myrdal.reasoning.causal_reasoner import CausalReasoner
from autogen_agentchat.messages import ThoughtEvent

class WorldModelNexus(ChatCompletionClient):
    def __init__(self, chat_client=None, model="myrdal-wmn"):
        super().__init__()
        # 6つの主要知識モジュールをデフォルトで追加
        self.knowledge_modules = {
            "abstract_thinking": AbstractThinking(),
            "multilingual": MultilingualUnderstanding(),
            "social_cognition": SocialCognition(),
            "knowledge_integration": KnowledgeIntegration(),
            "causal_reasoner": CausalReasoner(),
        }
        self.client = chat_client  # LLMクライアント
        # 内部状態やキャッシュ、ログ用変数など自由に追加OK

    @property
    def capabilities(self) -> ModelInfo:
        return ModelInfo(
            function_calling=True,
            json_output=True,
            structured_output=True,
            vision=False,
        )

    @property
    def model_info(self):
        return ModelInfo(
            family="myrdal-wmn",
            function_calling=True,
            json_output=True,
            structured_output=True,
            vision=False,
        )

    async def create(
        self,
        messages: Sequence,
        tools: Sequence = [],
        json_output: bool | type = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token=None,
    ) -> CreateResult:
        result = await self._run_deliberation_loop(messages, extra_create_args)
        return CreateResult(
            content=result.get("final_answer", ""),
            thought=result.get("thought", ""),
            usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
        )

    async def create_stream(
        self,
        messages: Sequence,
        tools: Sequence = [],
        json_output: bool | type = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token=None,
    ) -> AsyncGenerator[ThoughtEvent | CreateResult, None]:
        """
        WMNの熟考ループ（deliberate_stream）の各ステップをThoughtEventとしてストリーミング返却し、
        最後にCreateResultを返す。
        これにより、_call_llm経由でも熟考過程をストリーミングで受け取れる。
        """
        step = 1
        final_result = None
        async for result in self._deliberation_stream(messages, extra_create_args):
            thought = result.get("thought", "")
            yield ThoughtEvent(
                content=f"Step {step}: {thought}",
                source="wmn"
            )
            step += 1
            if result.get("satisfied"):
                final_result = result
                break
        if final_result:
            yield CreateResult(
                content=final_result.get("final_answer", ""),
                thought=final_result.get("thought", ""),
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
            )

    async def close(self):
        pass

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def count_tokens(self, messages, *args, **kwargs) -> int:
        return 0

    def remaining_tokens(self) -> int:
        return 10000

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    # --- ここから下は内部用メソッド ---
    async def _run_deliberation_loop(self, messages, extra_create_args):
        context = {"messages": messages, "goal": extra_create_args.get("goal") if extra_create_args else None}
        return await self.deliberate(context)

    async def _deliberation_stream(self, messages, extra_create_args):
        context = {"messages": messages, "goal": extra_create_args.get("goal") if extra_create_args else None}
        async for step in self.deliberate_stream(context):
            yield step

    # --- Verifier向け知識管理API ---
    def set_priority(self, knowledge_graph, node_id: str, priority: int):
        knowledge_graph.graph.nodes[node_id]['priority'] = priority

    def insert_priority(self, knowledge_graph, node_id: str, after_priority: int):
        for n, d in knowledge_graph.graph.nodes(data=True):
            if d.get('priority', 0) > after_priority:
                d['priority'] += 1
        knowledge_graph.graph.nodes[node_id]['priority'] = after_priority + 1

    def merge_nodes(self, knowledge_graph, node_ids: list, new_content: str, **kwargs):
        new_id = knowledge_graph.add_fact(new_content, **kwargs)
        for nid in node_ids:
            knowledge_graph.add_edge(nid, new_id, relation="merged_into")
        return new_id

    def remove_nodes(self, knowledge_graph, node_ids: list):
        knowledge_graph.graph.remove_nodes_from(node_ids)

    def update_from_llm_decision(self, knowledge_graph, llm_decision: dict):
        """
        LLMの熟考ループやプロンプトで出力された知識更新指示(JSON)を受けて、
        priority調整・統合・削除などを実行する。
        例: {
            "set_priority": [{"node_id": "fact_1", "priority": 3}],
            "merge": [{"node_ids": ["fact_1", "fact_2"], "new_content": "..."}],
            "remove": ["fact_3"]
        }
        """
        # priority調整
        for item in llm_decision.get("set_priority", []):
            self.set_priority(knowledge_graph, item["node_id"], item["priority"])
        # priority挿入
        for item in llm_decision.get("insert_priority", []):
            self.insert_priority(knowledge_graph, item["node_id"], item["after_priority"])
        # ノード統合
        for item in llm_decision.get("merge", []):
            self.merge_nodes(knowledge_graph, item["node_ids"], item["new_content"], **item.get("kwargs", {}))
        # ノード削除
        if "remove" in llm_decision:
            self.remove_nodes(knowledge_graph, llm_decision["remove"])

    # --- WMN本体の熟考・メタ認知API ---
    def _to_llm_message(self, msg):
        if isinstance(msg, (UserMessage, AssistantMessage, SystemMessage)):
            return msg
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                return UserMessage(content=msg["content"], source=msg.get("source", "user"))
            elif msg["role"] == "assistant":
                return AssistantMessage(content=msg["content"], source=msg.get("source", "assistant"))
            elif msg["role"] == "system":
                return SystemMessage(content=msg["content"])
        raise ValueError(f"Unknown message type: {type(msg)}")

    async def deliberate(self, context: dict) -> dict:
        """
        熟考・メタ認知推論のメインメソッド。
        context: {"messages": ..., "goal": ...}
        knowledge_modulesを活用しながら熟考ループを回し、最終的な推論・知識統合・自己評価を返す。
        """
        messages = context["messages"]
        goal = context.get("goal", "")
        step = 1
        deliberation_messages = list(messages)
        while True:
            prompt = (
                f"You are a metacognitive world model AI.\n"
                f"Goal: {goal}\n"
                f"You can use the following knowledge modules:\n"
                f"- abstract_thinking: for abstraction, analogy, and high-level reasoning.\n"
                f"- multilingual: for multilingual understanding and translation.\n"
                f"- social_cognition: for social reasoning and theory of mind.\n"
                f"- knowledge_integration: for integrating and synthesizing knowledge.\n"
                f"- causal_reasoner: for causal inference and reasoning.\n"
                f"Step {step}: Think step by step. Output your thought, which knowledge module to call (if any), call_args, satisfied (true/false), and final_answer if satisfied.\n"
                f"Output in JSON: {{'thought': ..., 'call_module': ..., 'call_args': ..., 'satisfied': ..., 'final_answer': ...}}"
            )
            deliberation_messages.append({"role": "system", "content": prompt})
            # dict→LLMMessage型に変換
            deliberation_messages_llm = [self._to_llm_message(m) for m in deliberation_messages]
            response_schema = {
                "type": "object",
                "properties": {
                    "thought": {"type": "string"},
                    "call_module": {"type": ["string", "null"]},
                    "call_args": {"type": "object"},
                    "satisfied": {"type": "boolean"},
                    "final_answer": {"type": ["string", "null"]}
                },
                "required": ["thought", "satisfied"]
            }
            result = await self.client.create(
                deliberation_messages_llm,
                extra_create_args={"response_format": {"type": "json_schema", "schema": response_schema}}
            )
            try:
                parsed = result.content if isinstance(result.content, dict) else json.loads(result.content)
            except Exception:
                parsed = {"thought": result.content, "call_module": None, "call_args": {}, "satisfied": False, "final_answer": None}
            if parsed["call_module"] and parsed["call_module"] in self.knowledge_modules:
                module = self.knowledge_modules[parsed["call_module"]]
                module_result = await module(**parsed["call_args"])
                parsed["module_result"] = module_result
            if parsed["satisfied"]:
                return parsed
            step += 1

    async def deliberate_stream(self, context: dict):
        """
        熟考・メタ認知推論のストリーミング版。
        各ステップの思考・知識統合過程をyieldで返す。
        """
        messages = context["messages"]
        goal = context.get("goal", "")
        step = 1
        deliberation_messages = list(messages)
        while True:
            prompt = (
                f"You are a metacognitive world model AI.\n"
                f"Goal: {goal}\n"
                f"You can use the following knowledge modules:\n"
                f"- abstract_thinking: for abstraction, analogy, and high-level reasoning.\n"
                f"- multilingual: for multilingual understanding and translation.\n"
                f"- explainable_ai: for explainable AI and model interpretation.\n"
                f"- social_cognition: for social reasoning and theory of mind.\n"
                f"- knowledge_integration: for integrating and synthesizing knowledge.\n"
                f"- causal_reasoner: for causal inference and reasoning.\n"
                f"Step {step}: Think step by step. Output your thought, which knowledge module to call (if any), call_args, satisfied (true/false), and final_answer if satisfied.\n"
                f"Output in JSON: {{'thought': ..., 'call_module': ..., 'call_args': ..., 'satisfied': ..., 'final_answer': ...}}"
            )
            deliberation_messages.append({"role": "system", "content": prompt})
            # dict→LLMMessage型に変換
            deliberation_messages_llm = [self._to_llm_message(m) for m in deliberation_messages]
            response_schema = {
                "type": "object",
                "properties": {
                    "thought": {"type": "string"},
                    "call_module": {"type": ["string", "null"]},
                    "call_args": {"type": "object"},
                    "satisfied": {"type": "boolean"},
                    "final_answer": {"type": ["string", "null"]}
                },
                "required": ["thought", "satisfied"]
            }
            async for chunk in self.client.create_stream(
                deliberation_messages_llm,
                extra_create_args={"response_format": {"type": "json_schema", "schema": response_schema}}
            ):
                try:
                    parsed = chunk if isinstance(chunk, dict) else json.loads(chunk)
                except Exception:
                    parsed = {"thought": chunk, "call_module": None, "call_args": {}, "satisfied": False, "final_answer": None}
                yield parsed
                if parsed["call_module"] and parsed["call_module"] in self.knowledge_modules:
                    module = self.knowledge_modules[parsed["call_module"]]
                    module_result = await module(**parsed["call_args"])
                    parsed["module_result"] = module_result
                if parsed["satisfied"]:
                    break
            step += 1 