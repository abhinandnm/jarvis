from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """Abstract Base Class for J.A.R.V.I.S. Plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The technical name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does, used by the LLM."""
        pass

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Returns the JSON schema defining the plugin's function interface for LLM tool calling.
        
        Matches the OpenAI / Gemini function definition format.
        """
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """Executes the plugin action and returns a string response."""
        pass
