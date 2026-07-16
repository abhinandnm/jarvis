import logging
import time
import pyautogui
from typing import Tuple, Dict, Any

# Configure pyautogui safety margins
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

logger = logging.getLogger("jarvis.tools.pyautogui")

class PyAutoGUITool:
    def __init__(self):
        pass

    def get_screen_dimensions(self) -> Dict[str, int]:
        """Returns the current screen resolution (width and height)."""
        width, height = pyautogui.size()
        return {"width": width, "height": height}

    def move_mouse(self, x: int, y: int, duration: float = 0.3) -> str:
        """Moves the mouse cursor to specific coordinates with optional animation duration."""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return f"Moved cursor to X: {x}, Y: {y}."
        except pyautogui.FailSafeException:
            return "Mouse movement aborted by failsafe trigger (cursor moved to screen corner)."
        except Exception as e:
            return f"Failed to move cursor: {str(e)}"

    def click_mouse(self, x: int = None, y: int = None, clicks: int = 1, button: str = 'left') -> str:
        """Clicks the mouse. If x and y are given, moves first."""
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, button=button)
                return f"Performed {clicks} {button}-click(s) at X: {x}, Y: {y}."
            else:
                pyautogui.click(clicks=clicks, button=button)
                return f"Performed {clicks} {button}-click(s) at current cursor position."
        except pyautogui.FailSafeException:
            return "Click action aborted by failsafe trigger."
        except Exception as e:
            return f"Click action failed: {str(e)}"

    def scroll_mouse(self, clicks: int) -> str:
        """Scrolls the mouse. Positive value scrolls up, negative scrolls down."""
        try:
            pyautogui.scroll(clicks)
            direction = "up" if clicks > 0 else "down"
            return f"Scrolled mouse {direction} by {abs(clicks)} units."
        except Exception as e:
            return f"Scroll failed: {str(e)}"

    def type_text(self, text: str, press_enter: bool = False) -> str:
        """Types string text into the active cursor position."""
        try:
            pyautogui.write(text, interval=0.02)
            if press_enter:
                pyautogui.press('enter')
            return f"Typed text: '{text[:30]}...' onto target."
        except Exception as e:
            return f"Typing failed: {str(e)}"

    def press_key(self, key_name: str) -> str:
        """Presses a single key or key combination (e.g. 'enter', 'tab', 'ctrl+c')."""
        try:
            key_name = key_name.lower().strip()
            if '+' in key_name:
                keys = key_name.split('+')
                # Press hotkey combination
                pyautogui.hotkey(*keys)
                return f"Executed hotkey: {key_name}."
            else:
                pyautogui.press(key_name)
                return f"Pressed key: '{key_name}'."
        except Exception as e:
            return f"Key press failed for {key_name}: {str(e)}"

    def simulate_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        """Drags from start coordinates to end coordinates."""
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.5, button='left')
            return f"Dragged cursor from ({start_x}, {start_y}) to ({end_x}, {end_y})."
        except Exception as e:
            return f"Drag operation failed: {str(e)}"

pyautogui_tool = PyAutoGUITool()
