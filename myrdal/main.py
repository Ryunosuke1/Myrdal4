from typing import Optional, AsyncGenerator
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.base import TaskResult
class Myrdal:
    def __init__(self):
        pass
    async def inteact_with_myrdal(self ,message: str) -> None:
        """
        The user uses this method to talk to Myrdal and then receive responses from myrdal.
        The team or agent will start when is not initalized.
        The team or agent will resume when is paused
        The user can use this method to send a message to Myrdal.
        Args:
            message (str): The message to send to Myrdal.
        """
        pass
    def pause(self) -> None:
        """
        Pause the Myrdal agent.
        """
        pass
    async def get_responses_async(self) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        Get responses from Myrdal asynchronously.
        Yields:
            AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]: The responses from Myrdal.
        """
        pass