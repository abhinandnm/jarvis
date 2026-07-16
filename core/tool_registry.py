import logging
import asyncio
import uuid
from typing import Dict, Any, List, Callable, Optional

from tools.os_control import os_controller
from tools.pyautogui_tool import pyautogui_tool
from tools.file_search import file_search_engine
from vision.screen_capture import screen_capturer
from vision.webcam_capture import webcam_capturer
from memory.memory_engine import memory_engine
from automation.organizer import folder_organizer
from plugins.loader import plugin_loader

logger = logging.getLogger("jarvis.core.registry")

# Central registry to coordinate pending UI permissions
pending_permissions: Dict[str, asyncio.Future] = {}

class ToolRegistry:
    def __init__(self):
        # Tools that require user permission before executing
        self.dangerous_tools = [
            "execute_terminal_command",
            "organize_directory"
        ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema list of all tools and loaded plugins for the LLM."""
        schemas = [
            # OS Control
            {
                "name": "open_application",
                "description": "Opens a system application, folder, file or web URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Application name (e.g. Notepad, Chrome) or file path or website URL"}
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "close_application",
                "description": "Terminates a running application or process on Windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "process_name": {"type": "string", "description": "Process executable name (e.g. notepad, chrome)"}
                    },
                    "required": ["process_name"]
                }
            },
            {
                "name": "set_volume",
                "description": "Adjusts the system speaker volume.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "description": "Target volume level percentage (0 to 100)"}
                    },
                    "required": ["level"]
                }
            },
            {
                "name": "execute_terminal_command",
                "description": "Runs a command prompt/shell command on the host machine. USE CAUTIOUSLY.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run"}
                    },
                    "required": ["command"]
                }
            },
            # File search
            {
                "name": "search_files",
                "description": "Searches for matching files recursively in user directories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob or file name query (e.g. report.pdf, *.docx)"},
                        "search_dir": {"type": "string", "description": "Optional search directory override", "default": None}
                    },
                    "required": ["pattern"]
                }
            },
            # Mouse / Keyboard pyautogui
            {
                "name": "simulate_click",
                "description": "Simulates a mouse click. Coordinates must be within screen dimensions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"},
                        "clicks": {"type": "integer", "description": "Click count", "default": 1},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "simulate_scroll",
                "description": "Scrolls the desktop screen view. Positive is scroll up, negative is down.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clicks": {"type": "integer", "description": "Number of scroll clicks (e.g., 200, -200)"}
                    },
                    "required": ["clicks"]
                }
            },
            {
                "name": "simulate_typing",
                "description": "Types text characters at current focus point.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "String text to type"},
                        "press_enter": {"type": "boolean", "description": "If true, hits Enter key after typing", "default": False}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "simulate_keypress",
                "description": "Simulates pressing a key or key combination (hotkey).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key_name": {"type": "string", "description": "Key name (e.g. enter, space, ctrl+c, alt+f4)"}
                    },
                    "required": ["key_name"]
                }
            },
            # Vision
            {
                "name": "read_screen_contents",
                "description": "Takes a screenshot of the user's screen and performs multimodal vision understanding to explain what is currently displayed.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "capture_webcam",
                "description": "Saves a webcam snap to cache and performs image analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            # Memory
            {
                "name": "remember_user_fact",
                "description": "Saves a personal user fact, preference, or task details into J.A.R.V.I.S.'s memory database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Unique key descriptor (e.g., user_birthday, project_name)"},
                        "value": {"type": "string", "description": "Fact value (e.g., October 12, Jarvis Assistant)"},
                        "category": {"type": "string", "enum": ["preference", "project", "app", "website", "task", "general"], "default": "general"}
                    },
                    "required": ["key", "value"]
                }
            },
            # Automation Organizer
            {
                "name": "organize_directory",
                "description": "Sorts and organizes scattered files in a folder into categorized subfolders based on extension.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string", "description": "Absolute folder path to clean up"}
                    },
                    "required": ["target_dir"]
                }
            }
        ]
        
        # Append dynamic plugin definitions (e.g. get_weather)
        schemas.extend(plugin_loader.get_tool_definitions())
        return schemas

    async def execute_tool(self, name: str, args: Dict[str, Any], websocket_broadcast_fn: Callable[[dict], Any]) -> str:
        """Executes tool action. Checks security authorization gates for dangerous operations."""
        logger.info(f"Registry executing tool '{name}' with arguments: {args}")

        # 1. Security check gate
        if name in self.dangerous_tools:
            logger.warning(f"Tool '{name}' is flagged as dangerous. Dispatching permission request to client.")
            req_id = str(uuid.uuid4())
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            pending_permissions[req_id] = fut
            
            # Request permission on the frontend
            await websocket_broadcast_fn({
                "type": "permission_request",
                "id": req_id,
                "tool": name,
                "arguments": args
            })
            
            # Await user response (resolves when websocket receives response packet)
            try:
                approved = await asyncio.wait_for(fut, timeout=60.0) # 60 second timeout limit
            except asyncio.TimeoutExpired:
                if req_id in pending_permissions:
                    del pending_permissions[req_id]
                return "Operation canceled: Request timed out awaiting user confirmation."
                
            if req_id in pending_permissions:
                del pending_permissions[req_id]
                
            if not approved:
                logger.info(f"Permission denied by user for tool execution: '{name}'")
                return "Operation aborted: Permission denied by user."
            
            logger.info(f"Permission approved by user for tool: '{name}'")

        # 2. Route execution to standard controller
        try:
            if name == "open_application":
                return os_controller.open_application(args["app_name"])
                
            elif name == "close_application":
                return os_controller.close_application(args["process_name"])
                
            elif name == "set_volume":
                return os_controller.set_system_volume(args["level"])
                
            elif name == "execute_terminal_command":
                return os_controller.execute_terminal_command(args["command"])
                
            elif name == "search_files":
                results = file_search_engine.search(args["pattern"], args.get("search_dir"))
                if not results:
                    return "No matching files located."
                return "\n".join([f"- {r['filename']} ({r['path']})" for r in results])
                
            elif name == "simulate_click":
                return pyautogui_tool.click_mouse(args["x"], args["y"], args.get("clicks", 1), args.get("button", "left"))
                
            elif name == "simulate_scroll":
                return pyautogui_tool.scroll_mouse(args["clicks"])
                
            elif name == "simulate_typing":
                return pyautogui_tool.type_text(args["text"], args.get("press_enter", False))
                
            elif name == "simulate_keypress":
                return pyautogui_tool.press_key(args["key_name"])
                
            elif name == "read_screen_contents":
                # Screen understanding: captures screenshot and calls LLM multi-modal description
                from ai.llm import llm_manager
                image_path = screen_capturer.capture()
                
                # Perform screenshot explanation prompt
                prompt = (
                    "Look at this screenshot of my computer display. "
                    "Describe what applications are open, what text is visible, "
                    "and summarize the current layout in detail for the user."
                )
                logger.info("Sending screen capture to LLM for multi-modal analysis...")
                
                # Setup Gemini/OpenAI vision description
                from openai import OpenAI
                from config.config import settings
                import base64
                
                # Read image
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                
                # For Gemini/OpenAI providers, call multimodal
                if settings.AI_PROVIDER == "gemini":
                    # We can use Gemini Client API
                    client = llm_manager._get_gemini_client()
                    # Open-Meteo or image content helper
                    from google.genai import types
                    response = client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                            prompt
                        ]
                    )
                    return f"[Screenshot Analyzed]: {response.text}"
                else:
                    # Fallback to OpenAI Vision API if keys present
                    if settings.OPENAI_API_KEY:
                        client = llm_manager._get_openai_client()
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                    ]
                                }
                            ]
                        )
                        return f"[Screen Description]: {response.choices[0].message.content}"
                    else:
                        return "Failed to analyze screen. Vision analysis requires Gemini or OpenAI API keys."
                        
            elif name == "capture_webcam":
                image_path = webcam_capturer.capture()
                # Run visual check
                from ai.llm import llm_manager
                from config.config import settings
                import base64
                
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                    
                prompt = "Explain what is visible on this webcam capture in a polite manner."
                
                if settings.AI_PROVIDER == "gemini":
                    client = llm_manager._get_gemini_client()
                    from google.genai import types
                    response = client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            prompt
                        ]
                    )
                    return f"[Webcam Analyzed]: {response.text}"
                elif settings.OPENAI_API_KEY:
                    client = llm_manager._get_openai_client()
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ]
                    )
                    return f"[Webcam Description]: {response.choices[0].message.content}"
                else:
                    return f"Webcam image captured at {image_path}, but vision API requires API keys."
                
            elif name == "remember_user_fact":
                return await memory_engine.save_memory_fact(args["key"], args["value"], args.get("category", "general"))
                
            elif name == "organize_directory":
                return folder_organizer.organize_folder(args["target_dir"])
                
            else:
                # Route to dynamic plugin execution (e.g. get_weather)
                if name in plugin_loader.loaded_plugins:
                    logger.info(f"Routing to plugin executor: {name}")
                    plugin = plugin_loader.loaded_plugins[name]
                    return await plugin.execute(args)
                else:
                    return f"Error: Tool name '{name}' is not registered."
                    
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return f"Error executing tool '{name}': {str(e)}"

tool_registry = ToolRegistry()
