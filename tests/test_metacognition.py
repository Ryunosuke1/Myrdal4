import pytest
from myrdal.metacognition.metacognition import MetacognitionFramework

class DummyChatClient:
    async def create(self, messages, json_output):
        class DummyResponse:
            content = '{"thought": "dummy", "call_module": null, "call_args": {}, "satisfied": true, "final_answer": "done"}'
        return DummyResponse()

@pytest.mark.asyncio
async def test_metacognitionframework_deliberate():
    knowledge_modules = {}
    chat_client = DummyChatClient()
    meta = MetacognitionFramework(knowledge_modules, chat_client=chat_client)
    context = {"messages": [], "goal": "test"}
    result = await meta.deliberate(context)
    assert result["satisfied"] is True
    assert result["final_answer"] == "done" 