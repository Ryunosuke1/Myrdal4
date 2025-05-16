from .short_term import ShortTermMemory
from .long_term import LongTermMemory

class MemoryManager:
    def __init__(self):
        self.short_term_memories = {}
        self.long_term_memory = LongTermMemory()
    def get_short_term(self, agent_id: str) -> ShortTermMemory:
        if agent_id not in self.short_term_memories:
            self.short_term_memories[agent_id] = ShortTermMemory()
        return self.short_term_memories[agent_id]
    def get_long_term(self) -> LongTermMemory:
        return self.long_term_memory 