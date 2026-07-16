"""
Plugin Base Class — Abstract interface for all JARVIS plugins.
Plugins can now expose multiple tool definitions (multi-skill plugins).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class PluginBase(ABC):
    """Abstract Base Class for J.A.R.V.I.S. Plugins.
    
    Each plugin can expose one or multiple tool definitions.
    All tools route through the plugin's execute() method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique plugin identifier (e.g. 'weather', 'github')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the plugin does."""
        pass

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns a list of JSON schemas for all tools this plugin exposes.
        Override this method to expose multiple tools.
        
        Defaults to wrapping the legacy single get_tool_definition() result.
        """
        defn = self.get_tool_definition()
        if defn:
            return [defn]
        return []

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Legacy single-tool definition. Override get_tool_definitions() instead
        for multi-tool plugins.
        """
        return {}

    @abstractmethod
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Executes a tool action and returns a string result.
        
        Args:
            tool_name: The specific tool being called (matches get_tool_definitions name).
            arguments: The arguments provided by the LLM.
        """
        pass


# Backwards compatibility alias
BasePlugin = PluginBase
