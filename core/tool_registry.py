"""
Tool Registry — Central registry for all JARVIS agent tools.
Includes OS control, file ops, mouse/keyboard, vision, OCR, memory,
clipboard, brightness, automation, and all loaded plugins.
Security gate implemented for dangerous operations.
"""

import logging
import asyncio
import uuid
import os
from typing import Dict, Any, List, Callable, Optional

from tools.os_control import os_controller
from tools.pyautogui_tool import pyautogui_tool
from tools.file_search import file_search_engine
from tools.ocr_tool import ocr_tool
from tools.brightness_tool import brightness_tool
from tools.clipboard_tool import clipboard_tool
from vision.screen_capture import screen_capturer
from vision.webcam_capture import webcam_capturer
from memory.memory_engine import memory_engine
from automation.organizer import folder_organizer
from plugins.loader import plugin_loader

logger = logging.getLogger("jarvis.core.registry")

# Central registry for pending UI permission futures
pending_permissions: Dict[str, asyncio.Future] = {}


class ToolRegistry:
    """Manages all available JARVIS tools with security gating."""

    def __init__(self):
        # Tools requiring explicit user permission before execution
        self.dangerous_tools = {
            "execute_terminal_command",
            "organize_directory",
            "delete_file",
            "bulk_rename_files",
        }

    # ------------------------------------------------------------------ #
    #  Schema Definitions                                                  #
    # ------------------------------------------------------------------ #
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema list of all registered tools for the LLM."""
        schemas = [
            # ── Application Control ─────────────────────────────────────
            {
                "name": "open_application",
                "description": "Opens a system application, folder, file, or web URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Application name (e.g. Notepad, Chrome) or file path or website URL"
                        }
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "close_application",
                "description": "Terminates a running application or process by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "process_name": {
                            "type": "string",
                            "description": "Process executable name (e.g. notepad.exe, chrome.exe)"
                        }
                    },
                    "required": ["process_name"]
                }
            },
            # ── System Controls ──────────────────────────────────────────
            {
                "name": "set_volume",
                "description": "Adjusts the system speaker volume to a specific percentage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "description": "Target volume level 0-100"}
                    },
                    "required": ["level"]
                }
            },
            {
                "name": "set_brightness",
                "description": "Adjusts the display screen brightness.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "description": "Brightness level 0-100"}
                    },
                    "required": ["level"]
                }
            },
            {
                "name": "execute_terminal_command",
                "description": "Runs a terminal/PowerShell command on the host machine. USE CAUTIOUSLY — requires user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"}
                    },
                    "required": ["command"]
                }
            },
            # ── File System ──────────────────────────────────────────────
            {
                "name": "search_files",
                "description": "Searches recursively for files matching a pattern in user directories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob or filename pattern (e.g. report.pdf, *.docx)"},
                        "search_dir": {"type": "string", "description": "Optional search directory override"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "read_file_content",
                "description": "Reads and returns the text content of a file (txt, py, js, md, json, csv, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute path to the file to read"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "create_file",
                "description": "Creates a new file with specified content at the given path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute path for the new file"},
                        "content": {"type": "string", "description": "Content to write to the file"}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "organize_directory",
                "description": "Sorts files in a folder into category subfolders by extension. Requires user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string", "description": "Absolute folder path to organize"}
                    },
                    "required": ["target_dir"]
                }
            },
            {
                "name": "bulk_rename_files",
                "description": "Renames multiple files in a directory using a pattern replacement. Requires user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory containing files to rename"},
                        "search_pattern": {"type": "string", "description": "Text to search for in filenames"},
                        "replace_with": {"type": "string", "description": "Text to replace the search pattern with"},
                        "file_extension": {"type": "string", "description": "Optional: filter by extension (e.g. .txt)"}
                    },
                    "required": ["directory", "search_pattern", "replace_with"]
                }
            },
            # ── Mouse & Keyboard (PyAutoGUI) ──────────────────────────────
            {
                "name": "simulate_click",
                "description": "Simulates a mouse click at specified screen coordinates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"},
                        "clicks": {"type": "integer", "description": "Number of clicks", "default": 1},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "simulate_scroll",
                "description": "Scrolls the screen. Positive clicks = up, negative = down.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clicks": {"type": "integer", "description": "Scroll amount (positive=up, negative=down)"}
                    },
                    "required": ["clicks"]
                }
            },
            {
                "name": "simulate_typing",
                "description": "Types text at the current cursor position.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to type"},
                        "press_enter": {"type": "boolean", "description": "Press Enter after typing", "default": False}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "simulate_keypress",
                "description": "Presses a keyboard key or key combination (e.g. ctrl+c, alt+f4, enter).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key_name": {"type": "string", "description": "Key or hotkey string (e.g. 'ctrl+c', 'alt+f4', 'enter')"}
                    },
                    "required": ["key_name"]
                }
            },
            {
                "name": "move_mouse",
                "description": "Moves the mouse cursor to a specific position on screen.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "Target X coordinate"},
                        "y": {"type": "integer", "description": "Target Y coordinate"},
                        "duration": {"type": "number", "description": "Movement duration in seconds", "default": 0.3}
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "take_screenshot",
                "description": "Takes a screenshot and saves it to a file. Returns the file path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Optional output filename (default: screenshot_TIMESTAMP.png)"}
                    },
                    "required": []
                }
            },
            # ── Vision & OCR ──────────────────────────────────────────────
            {
                "name": "read_screen_contents",
                "description": "Takes a screenshot and uses AI vision to describe all visible content, open apps, and text.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "ocr_screen",
                "description": "Extracts and returns all visible text from the screen using OCR (no AI vision needed).",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "ocr_screen_region",
                "description": "Extracts text from a specific rectangular region of the screen using OCR.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "Left coordinate of region"},
                        "y": {"type": "integer", "description": "Top coordinate of region"},
                        "width": {"type": "integer", "description": "Width of region in pixels"},
                        "height": {"type": "integer", "description": "Height of region in pixels"}
                    },
                    "required": ["x", "y", "width", "height"]
                }
            },
            {
                "name": "capture_webcam",
                "description": "Captures a webcam photo and uses AI to describe what is visible.",
                "parameters": {"type": "object", "properties": {}}
            },
            # ── Clipboard ─────────────────────────────────────────────────
            {
                "name": "get_clipboard",
                "description": "Reads and returns the current clipboard text content.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "set_clipboard",
                "description": "Copies text to the system clipboard.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to copy to clipboard"}
                    },
                    "required": ["text"]
                }
            },
            # ── Memory ────────────────────────────────────────────────────
            {
                "name": "remember_user_fact",
                "description": "Saves a user fact, preference, or task detail to JARVIS long-term memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Unique key descriptor (e.g. user_birthday, project_name)"},
                        "value": {"type": "string", "description": "The value to remember"},
                        "category": {
                            "type": "string",
                            "enum": ["preference", "project", "app", "website", "task", "general"],
                            "default": "general"
                        }
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "recall_user_facts",
                "description": "Retrieves stored memory facts, optionally filtered by category.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional category filter",
                            "enum": ["preference", "project", "app", "website", "task", "general"]
                        }
                    },
                    "required": []
                }
            },
            # ── Automation Scheduler ──────────────────────────────────────
            {
                "name": "schedule_task",
                "description": "Creates a recurring or one-time automated task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Task name"},
                        "command": {"type": "string", "description": "Shell command to run"},
                        "trigger_type": {
                            "type": "string",
                            "enum": ["interval", "cron", "date"],
                            "description": "Trigger type"
                        },
                        "interval_seconds": {
                            "type": "integer",
                            "description": "For interval trigger: seconds between runs"
                        },
                        "cron_expression": {
                            "type": "string",
                            "description": "For cron trigger: cron string e.g. '0 9 * * 1-5' (9am weekdays)"
                        },
                        "run_at": {
                            "type": "string",
                            "description": "For date trigger: ISO datetime string"
                        }
                    },
                    "required": ["name", "command", "trigger_type"]
                }
            },
            {
                "name": "list_scheduled_tasks",
                "description": "Lists all currently scheduled automation tasks.",
                "parameters": {"type": "object", "properties": {}}
            },
        ]

        # Append dynamic plugin tool definitions
        schemas.extend(plugin_loader.get_tool_definitions())
        return schemas

    # ------------------------------------------------------------------ #
    #  Tool Execution                                                       #
    # ------------------------------------------------------------------ #
    async def execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        websocket_broadcast_fn: Callable[[dict], Any]
    ) -> str:
        """
        Executes the named tool with the given arguments.
        Applies security gate for dangerous operations before execution.
        """
        logger.info(f"Executing tool '{name}' with args: {args}")

        # ── Security Gate ────────────────────────────────────────────────
        if name in self.dangerous_tools:
            logger.warning(f"Tool '{name}' requires user permission.")
            req_id = str(uuid.uuid4())
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            pending_permissions[req_id] = fut

            await websocket_broadcast_fn({
                "type": "permission_request",
                "id": req_id,
                "tool": name,
                "arguments": args
            })

            try:
                approved = await asyncio.wait_for(fut, timeout=60.0)
            except asyncio.TimeoutExpired:
                pending_permissions.pop(req_id, None)
                return "Operation canceled: Permission request timed out."

            pending_permissions.pop(req_id, None)

            if not approved:
                return "Operation aborted: User denied permission."

        # ── Tool Routing ─────────────────────────────────────────────────
        try:
            # Application control
            if name == "open_application":
                return os_controller.open_application(args["app_name"])

            elif name == "close_application":
                return os_controller.close_application(args["process_name"])

            # System controls
            elif name == "set_volume":
                return os_controller.set_system_volume(args["level"])

            elif name == "set_brightness":
                return brightness_tool.set_brightness(args["level"])

            elif name == "execute_terminal_command":
                return os_controller.execute_terminal_command(args["command"])

            # File system
            elif name == "search_files":
                results = file_search_engine.search(args["pattern"], args.get("search_dir"))
                if not results:
                    return "No matching files found."
                return "\n".join([f"• {r['filename']} → {r['path']}" for r in results])

            elif name == "read_file_content":
                return self._read_file(args["file_path"])

            elif name == "create_file":
                return self._create_file(args["file_path"], args["content"])

            elif name == "organize_directory":
                return folder_organizer.organize_folder(args["target_dir"])

            elif name == "bulk_rename_files":
                return self._bulk_rename(
                    args["directory"],
                    args["search_pattern"],
                    args["replace_with"],
                    args.get("file_extension")
                )

            # Mouse / Keyboard
            elif name == "simulate_click":
                return pyautogui_tool.click_mouse(
                    args["x"], args["y"],
                    args.get("clicks", 1),
                    args.get("button", "left")
                )

            elif name == "simulate_scroll":
                return pyautogui_tool.scroll_mouse(args["clicks"])

            elif name == "simulate_typing":
                return pyautogui_tool.type_text(args["text"], args.get("press_enter", False))

            elif name == "simulate_keypress":
                return pyautogui_tool.press_key(args["key_name"])

            elif name == "move_mouse":
                return pyautogui_tool.move_mouse(args["x"], args["y"], args.get("duration", 0.3))

            elif name == "take_screenshot":
                return self._take_screenshot(args.get("filename"))

            # Vision
            elif name == "read_screen_contents":
                return await self._analyze_screen(websocket_broadcast_fn)

            elif name == "ocr_screen":
                return ocr_tool.ocr_full_screen()

            elif name == "ocr_screen_region":
                return ocr_tool.ocr_region(args["x"], args["y"], args["width"], args["height"])

            elif name == "capture_webcam":
                return await self._analyze_webcam(websocket_broadcast_fn)

            # Clipboard
            elif name == "get_clipboard":
                return clipboard_tool.get_clipboard()

            elif name == "set_clipboard":
                return clipboard_tool.set_clipboard(args["text"])

            # Memory
            elif name == "remember_user_fact":
                return await memory_engine.save_memory_fact(
                    args["key"], args["value"], args.get("category", "general")
                )

            elif name == "recall_user_facts":
                return await self._recall_facts(args.get("category"))

            # Scheduler
            elif name == "schedule_task":
                return self._schedule_task(args)

            elif name == "list_scheduled_tasks":
                return self._list_tasks()

            # Plugin routing (weather, github, calendar, etc.)
            else:
                if name in plugin_loader.tool_to_plugin:
                    return await plugin_loader.execute_plugin_tool(name, args)
                return f"Unknown tool: '{name}'. It may not be registered."

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return f"Tool '{name}' encountered an error: {str(e)}"

    # ------------------------------------------------------------------ #
    #  Helper Methods                                                       #
    # ------------------------------------------------------------------ #
    def _read_file(self, file_path: str) -> str:
        """Reads text content from a file."""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        try:
            size = os.path.getsize(file_path)
            if size > 500_000:  # 500KB limit
                return f"File too large to read ({size} bytes). Maximum is 500KB."
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return f"File content ({file_path}):\n\n{content[:5000]}{'...[truncated]' if len(content) > 5000 else ''}"
        except Exception as e:
            return f"Failed to read file: {str(e)}"

    def _create_file(self, file_path: str, content: str) -> str:
        """Creates a new file with given content."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File created successfully: {file_path}"
        except Exception as e:
            return f"Failed to create file: {str(e)}"

    def _bulk_rename(self, directory: str, search: str, replace: str, ext_filter: Optional[str] = None) -> str:
        """Renames files in bulk using find-and-replace on filenames."""
        if not os.path.isdir(directory):
            return f"Directory not found: {directory}"
        renamed = 0
        for fname in os.listdir(directory):
            if ext_filter and not fname.lower().endswith(ext_filter.lower()):
                continue
            if search in fname:
                new_name = fname.replace(search, replace)
                src = os.path.join(directory, fname)
                dst = os.path.join(directory, new_name)
                if not os.path.exists(dst):
                    os.rename(src, dst)
                    renamed += 1
        return f"Bulk rename complete: {renamed} file(s) renamed in {directory}."

    def _take_screenshot(self, filename: Optional[str] = None) -> str:
        """Takes a screenshot and saves it."""
        try:
            import datetime
            from PIL import ImageGrab
            os.makedirs("cache", exist_ok=True)
            if not filename:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            path = os.path.join("cache", filename)
            img = ImageGrab.grab()
            img.save(path)
            return f"Screenshot saved to: {os.path.abspath(path)}"
        except ImportError:
            return screen_capturer.capture()
        except Exception as e:
            return f"Screenshot failed: {str(e)}"

    async def _analyze_screen(self, broadcast_fn) -> str:
        """Captures screen and runs AI vision analysis."""
        from ai.llm import llm_manager
        from config.config import settings
        import base64

        image_path = screen_capturer.capture()
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        prompt = (
            "Analyze this screenshot of my computer. Describe: "
            "1) What applications or windows are open, "
            "2) What text or content is visible, "
            "3) The overall state of the display. Be concise and specific."
        )

        if settings.AI_PROVIDER == "gemini":
            client = llm_manager._get_gemini_client()
            from google.genai import types
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/png"), prompt]
            )
            return f"[Screenshot Analyzed]: {response.text}"
        elif settings.OPENAI_API_KEY:
            client = llm_manager._get_openai_client()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]}]
            )
            return f"[Screen Description]: {response.choices[0].message.content}"
        else:
            return f"Screen captured at {image_path}. Vision analysis requires Gemini or OpenAI API key."

    async def _analyze_webcam(self, broadcast_fn) -> str:
        """Captures webcam and runs AI vision analysis."""
        from ai.llm import llm_manager
        from config.config import settings
        import base64

        image_path = webcam_capturer.capture()
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        prompt = "Describe what you see in this webcam capture in a helpful, polite manner."

        if settings.AI_PROVIDER == "gemini":
            client = llm_manager._get_gemini_client()
            from google.genai import types
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), prompt]
            )
            return f"[Webcam Analyzed]: {response.text}"
        elif settings.OPENAI_API_KEY:
            client = llm_manager._get_openai_client()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}]
            )
            return f"[Webcam Description]: {response.choices[0].message.content}"
        else:
            return f"Webcam image captured at {image_path}. Vision analysis requires API key."

    async def _recall_facts(self, category: Optional[str] = None) -> str:
        """Retrieves stored memory facts."""
        try:
            all_memories = await memory_engine.get_all_memories(category)
            if not all_memories:
                cat_str = f" in category '{category}'" if category else ""
                return f"No memories stored{cat_str} yet."
            lines = [f"Stored memories{' (' + category + ')' if category else ''}:"]
            for m in all_memories:
                lines.append(f"• {m['key']}: {m['value']} [{m['category']}]")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to retrieve memories: {str(e)}"

    def _schedule_task(self, args: Dict[str, Any]) -> str:
        """Creates a scheduled task via the JARVIS scheduler."""
        try:
            from automation.scheduler import jarvis_scheduler
            import uuid as _uuid

            task_id = str(_uuid.uuid4())[:8]
            trigger_type = args["trigger_type"]

            # Build trigger config
            if trigger_type == "interval":
                config = {"seconds": args.get("interval_seconds", 3600)}
            elif trigger_type == "cron":
                expr = args.get("cron_expression", "0 9 * * *")
                parts = expr.strip().split()
                if len(parts) != 5:
                    return f"Invalid cron expression: {expr}. Use 5-field format (e.g. '0 9 * * 1-5')."
                config = {
                    "minute": parts[0], "hour": parts[1],
                    "day": parts[2], "month": parts[3], "day_of_week": parts[4]
                }
            elif trigger_type == "date":
                config = {"run_date": args.get("run_at")}
            else:
                return f"Unknown trigger type: {trigger_type}"

            return jarvis_scheduler.add_task(
                task_id=task_id,
                name=args["name"],
                command=args["command"],
                trigger_type=trigger_type,
                trigger_config=config
            )
        except Exception as e:
            return f"Failed to schedule task: {str(e)}"

    def _list_tasks(self) -> str:
        """Returns a formatted list of scheduled tasks."""
        try:
            from automation.scheduler import jarvis_scheduler
            tasks = jarvis_scheduler.list_tasks()
            if not tasks:
                return "No scheduled tasks running."
            lines = ["Active scheduled tasks:"]
            for t in tasks:
                nxt = t.get("next_run", "N/A")
                builtin = " [built-in]" if t.get("is_builtin") else ""
                lines.append(f"• {t['name']}{builtin} — next run: {nxt}")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to list tasks: {str(e)}"


tool_registry = ToolRegistry()
