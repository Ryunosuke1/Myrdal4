import pytest
from myrdal.memory.manager import MemoryManager
from autogen_core.memory import ListMemory

def test_memory_manager_get_agent_memory():
    mm = MemoryManager()
    mem1 = mm.get_agent_memory("agent1")
    mem2 = mm.get_agent_memory("agent2")
    assert isinstance(mem1, ListMemory)
    assert isinstance(mem2, ListMemory)
    assert mem1 is not mem2
    # agent1のメモリは同じインスタンスが返る
    assert mm.get_agent_memory("agent1") is mem1 