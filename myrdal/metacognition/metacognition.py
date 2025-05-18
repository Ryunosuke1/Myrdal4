# 統合メタ認知フレームワーク
# これは今使われていない

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ChatCompletionClient
import json
import os

class MetacognitionFramework:
    def __init__(self, knowledge_modules: dict, chat_client: ChatCompletionClient, llm_model="gpt-3.5-turbo", causal_reasoner=None):
        self.knowledge_modules = knowledge_modules.copy() if knowledge_modules else {}
        self.llm_model = llm_model
        self.client = chat_client  # 必須引数として受け取る

    async def deliberate(self, context: dict) -> dict:
        messages = context["messages"]
        goal = context.get("goal", "")
        module_results = []
        while True:
            prompt = (
                "You are a metacognitive AI. For each step, output a JSON with: "
                "'thought', 'call_module', 'call_args', 'satisfied', 'final_answer'. "
                "Use only the following modules: abstract_thinking, multilingual, explainable_ai, social_cognition, knowledge_integration, causal_reasoner. "
                "If you need to call a module, set 'call_module' and 'call_args'. If you are satisfied, set 'satisfied': true and provide 'final_answer'.\n"
                f"Goal: {goal}\nMessages: {messages}\nModuleResults: {module_results}"
            )
            response = await self.client.create(
                messages=[{"role": "system", "content": prompt}],
                json_output=True
            )
            content = response.content if hasattr(response, "content") else response["choices"][0]["message"]["content"]
            try:
                result = json.loads(content)
            except Exception:
                result = {"thought": content, "call_module": None, "call_args": {}, "satisfied": False, "final_answer": None}
            if result["call_module"]:
                module = self.knowledge_modules.get(result["call_module"])
                if module:
                    method = getattr(module, result["call_args"].get("method", ""), None)
                    if method:
                        module_result = await method(**{k: v for k, v in result["call_args"].items() if k != "method"})
                        module_results.append({"module": result["call_module"], "result": module_result})
                        continue  # モジュール呼び出し後、再度LLMに熟考を促す
            return result

    async def deliberate_stream(self, context: dict):
        messages = context["messages"]
        goal = context.get("goal", "")
        module_results = []
        while True:
            prompt = (
                "You are a metacognitive AI. For each step, output a JSON with: "
                "'thought', 'call_module', 'call_args', 'satisfied', 'final_answer'. "
                "Use only the following modules: abstract_thinking, multilingual, explainable_ai, social_cognition, knowledge_integration, causal_reasoner. "
                "If you need to call a module, set 'call_module' and 'call_args'. If you are satisfied, set 'satisfied': true and provide 'final_answer'.\n"
                f"Goal: {goal}\nMessages: {messages}\nModuleResults: {module_results}"
            )
            async for chunk in self.client.create_stream(
                messages=[{"role": "system", "content": prompt}],
                json_output=True
            ):
                try:
                    result = json.loads(chunk.content)
                except Exception:
                    result = {"thought": chunk.content, "call_module": None, "call_args": {}, "satisfied": False, "final_answer": None}
                yield chunk
                if result["call_module"]:
                    module = self.knowledge_modules.get(result["call_module"])
                    if module:
                        method = getattr(module, result["call_args"].get("method", ""), None)
                        if method:
                            module_result = await method(**{k: v for k, v in result["call_args"].items() if k != "method"})
                            module_results.append({"module": result["call_module"], "result": module_result})
                            break  # モジュール呼び出し後、再度LLMに熟考を促す
                if result["satisfied"]:
                    return 