"""
Plugin Loader — Dynamically discovers and loads all JARVIS plugins.
Supports single-tool and multi-tool plugin definitions.
"""

import os
import inspect
import importlib
import logging
from typing import Dict, List, Any
from plugins.base import PluginBase

logger = logging.getLogger("jarvis.plugins.loader")


class PluginLoader:
    """Scans the plugins directory and instantiates all PluginBase subclasses."""

    def __init__(self):
        self.loaded_plugins: Dict[str, PluginBase] = {}
        # Map from tool_name -> plugin instance (one plugin can expose many tools)
        self.tool_to_plugin: Dict[str, PluginBase] = {}

    def load_plugins(self) -> Dict[str, PluginBase]:
        """Scans the plugins directory and imports all PluginBase subclasses."""
        self.loaded_plugins.clear()
        self.tool_to_plugin.clear()

        plugins_dir = os.path.dirname(__file__)
        logger.info(f"Scanning directory for plugins: {plugins_dir}")

        for file in os.listdir(plugins_dir):
            # Only process Python files; skip internal files
            if file.endswith(".py") and file not in ["__init__.py", "base.py", "loader.py"]:
                module_name = file[:-3]
                full_module_name = f"plugins.{module_name}"

                try:
                    module = importlib.import_module(full_module_name)

                    for class_name, obj in inspect.getmembers(module, inspect.isclass):
                        # Check it's a non-abstract subclass of PluginBase
                        if issubclass(obj, PluginBase) and obj is not PluginBase and not inspect.isabstract(obj):
                            try:
                                plugin_instance = obj()
                                self.loaded_plugins[plugin_instance.name] = plugin_instance

                                # Register all exposed tools -> plugin routing
                                for tool_def in plugin_instance.get_tool_definitions():
                                    tool_name = tool_def.get("name")
                                    if tool_name:
                                        self.tool_to_plugin[tool_name] = plugin_instance

                                tool_count = len(plugin_instance.get_tool_definitions())
                                logger.info(
                                    f"Loaded plugin: '{plugin_instance.name}' "
                                    f"({tool_count} tool(s)) — {plugin_instance.description[:60]}"
                                )
                            except Exception as e:
                                logger.error(f"Failed to instantiate plugin class {class_name}: {e}")

                except Exception as e:
                    logger.error(f"Failed to import plugin module {full_module_name}: {e}")

        logger.info(f"Total plugins loaded: {len(self.loaded_plugins)} | Total tools: {len(self.tool_to_plugin)}")
        return self.loaded_plugins

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Compiles all tool definitions from all loaded plugins.

        Returns:
            List of JSON schema tool definitions for LLM function calling.
        """
        definitions = []
        for plugin in self.loaded_plugins.values():
            try:
                definitions.extend(plugin.get_tool_definitions())
            except Exception as e:
                logger.error(f"Error getting tool definitions from plugin '{plugin.name}': {e}")
        return definitions

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Returns metadata about all loaded plugins for the UI."""
        result = []
        for plugin in self.loaded_plugins.values():
            tools = plugin.get_tool_definitions()
            result.append({
                "name": plugin.name,
                "description": plugin.description,
                "tool_count": len(tools),
                "tools": [t.get("name") for t in tools],
                "active": True
            })
        return result

    async def execute_plugin_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Routes a tool call to the correct plugin instance."""
        plugin = self.tool_to_plugin.get(tool_name)
        if not plugin:
            return f"No plugin registered for tool: '{tool_name}'"
        try:
            return await plugin.execute(tool_name, args)
        except Exception as e:
            logger.error(f"Plugin '{plugin.name}' failed on tool '{tool_name}': {e}")
            return f"Plugin error: {str(e)}"


plugin_loader = PluginLoader()
# Proactively scan and load all plugins on module import
plugin_loader.load_plugins()
