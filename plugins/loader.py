import os
import inspect
import importlib
import logging
from typing import Dict, List, Type
from plugins.base import BasePlugin

logger = logging.getLogger("jarvis.plugins.loader")

class PluginLoader:
    def __init__(self):
        self.loaded_plugins: Dict[str, BasePlugin] = {}

    def load_plugins(self) -> Dict[str, BasePlugin]:
        """Scans the plugins directory and imports all BasePlugin subclasses."""
        self.loaded_plugins.clear()
        
        plugins_dir = os.path.dirname(__file__)
        logger.info(f"Scanning directory for plugins: {plugins_dir}")
        
        for file in os.listdir(plugins_dir):
            # Check for python files (exclude base.py, loader.py, and dunder files)
            if file.endswith(".py") and file not in ["__init__.py", "base.py", "loader.py"]:
                module_name = file[:-3]
                full_module_name = f"plugins.{module_name}"
                
                try:
                    # Dynamically import module
                    module = importlib.import_module(full_module_name)
                    
                    # Search classes inside module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # Verify it is a subclass of BasePlugin (and not BasePlugin itself)
                        if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                            plugin_instance = obj()
                            self.loaded_plugins[plugin_instance.name] = plugin_instance
                            logger.info(f"Successfully loaded plugin: {plugin_instance.name} ({plugin_instance.description[:40]}...)")
                except Exception as e:
                    logger.error(f"Failed to load plugin module {full_module_name}: {e}")

        logger.info(f"Total plugin(s) loaded: {len(self.loaded_plugins)}")
        return self.loaded_plugins

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Compiles function-calling schema definitions for all loaded plugins."""
        return [plugin.get_tool_definition() for plugin in self.loaded_plugins.values()]

plugin_loader = PluginLoader()
# Proactively scan and load
plugin_loader.load_plugins()
