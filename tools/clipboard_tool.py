"""
Clipboard Tool — Read, write, and track clipboard history.
Uses pyperclip for cross-platform clipboard access.
Maintains an in-memory history of recent clipboard entries (up to 50).
"""

import logging
from collections import deque
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("jarvis.tools.clipboard")

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    logger.warning("pyperclip not installed. Clipboard tools unavailable. Run: pip install pyperclip")


class ClipboardTool:
    """Manages clipboard read/write operations and history tracking."""

    def __init__(self, max_history: int = 50):
        self._history: deque = deque(maxlen=max_history)
        self._last_value: str = ""

    def get_clipboard(self) -> str:
        """
        Reads the current clipboard content.

        Returns:
            str: Current clipboard text, or error message.
        """
        if not CLIPBOARD_AVAILABLE:
            return "Clipboard unavailable. Run: pip install pyperclip"
        try:
            content = pyperclip.paste()
            if not content:
                return "Clipboard is empty."
            return f"Clipboard content: {content}"
        except Exception as e:
            logger.error(f"Get clipboard error: {e}")
            return f"Failed to read clipboard: {str(e)}"

    def set_clipboard(self, text: str) -> str:
        """
        Writes text to the clipboard.

        Args:
            text: Text to copy to clipboard.

        Returns:
            str: Confirmation message.
        """
        if not CLIPBOARD_AVAILABLE:
            return "Clipboard unavailable. Run: pip install pyperclip"
        try:
            pyperclip.copy(text)
            # Add to history
            self._add_to_history(text)
            logger.info(f"Clipboard set to: {text[:50]}...")
            return f"Copied to clipboard: '{text[:100]}{'...' if len(text) > 100 else ''}'"
        except Exception as e:
            logger.error(f"Set clipboard error: {e}")
            return f"Failed to write to clipboard: {str(e)}"

    def _add_to_history(self, text: str):
        """Adds an entry to clipboard history, avoiding duplicates."""
        if text and text != self._last_value:
            self._history.append({
                "content": text,
                "timestamp": datetime.now().isoformat(),
                "preview": text[:80] + ("..." if len(text) > 80 else "")
            })
            self._last_value = text

    def get_history(self) -> List[Dict]:
        """
        Returns the clipboard history.

        Returns:
            List[Dict]: List of clipboard history entries with timestamp and preview.
        """
        return list(reversed(self._history))

    def get_history_summary(self) -> str:
        """
        Returns a formatted summary of clipboard history.

        Returns:
            str: Human-readable clipboard history.
        """
        if not self._history:
            return "No clipboard history recorded yet."
        lines = ["Recent clipboard history:"]
        for i, entry in enumerate(reversed(self._history), 1):
            lines.append(f"{i}. [{entry['timestamp'][:19]}] {entry['preview']}")
        return "\n".join(lines)

    def clear_history(self) -> str:
        """Clears the clipboard history."""
        count = len(self._history)
        self._history.clear()
        self._last_value = ""
        return f"Cleared {count} clipboard history entries."


clipboard_tool = ClipboardTool()
