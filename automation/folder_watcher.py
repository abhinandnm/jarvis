"""
Folder Watcher — Watchdog-based directory monitoring.
Automatically organizes new files dropped into watched folders.
Broadcasts real-time events to JARVIS WebSocket clients.
"""

import logging
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional

logger = logging.getLogger("jarvis.automation.folder_watcher")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog not installed. Run: pip install watchdog")


class JarvisFileHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Handles file system events for watched directories."""

    def __init__(self, folder_path: str, broadcast_fn: Optional[Callable] = None, auto_organize: bool = False):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.folder_path = folder_path
        self._broadcast_fn = broadcast_fn
        self.auto_organize = auto_organize
        self._loop = None

    def set_loop(self, loop):
        """Sets the asyncio event loop for broadcasting."""
        self._loop = loop

    def on_created(self, event):
        """Triggered when a new file is created in the watched folder."""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        logger.info(f"New file detected in watched folder: {filename}")

        # Broadcast file event
        if self._broadcast_fn and self._loop:
            import asyncio
            asyncio.run_coroutine_threadsafe(
                self._broadcast_fn({
                    "type": "notification",
                    "content": f"📁 New file detected: {filename} in {os.path.basename(self.folder_path)}",
                    "level": "info",
                }),
                self._loop
            )

        # Auto-organize if enabled
        if self.auto_organize:
            # Small delay to ensure file is fully written
            time.sleep(1.5)
            self._auto_organize_file(event.src_path)

    def _auto_organize_file(self, file_path: str):
        """Moves a newly created file to its appropriate category subfolder."""
        try:
            from automation.organizer import folder_organizer
            # Organize the specific file
            ext = Path(file_path).suffix.lower()
            category = folder_organizer.get_category_for_extension(ext)
            
            if category:
                dest_dir = os.path.join(self.folder_path, category)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, os.path.basename(file_path))
                
                # Avoid overwrite conflicts
                if not os.path.exists(dest):
                    os.rename(file_path, dest)
                    logger.info(f"Auto-organized: {os.path.basename(file_path)} -> {category}/")
        except Exception as e:
            logger.error(f"Auto-organize failed for {file_path}: {e}")


class FolderWatcher:
    """Manages watchdog observers for multiple directories."""

    def __init__(self):
        self._observers: Dict[str, any] = {}
        self._broadcast_fn: Optional[Callable] = None
        self._loop = None

    def initialize(self, broadcast_fn: Callable, loop):
        """Initialize with a broadcast function and event loop."""
        self._broadcast_fn = broadcast_fn
        self._loop = loop

    def watch(self, folder_path: str, auto_organize: bool = False) -> str:
        """
        Starts watching a directory for new files.

        Args:
            folder_path: Absolute path to the folder to watch.
            auto_organize: If True, automatically organizes new files.

        Returns:
            str: Status message.
        """
        if not WATCHDOG_AVAILABLE:
            return "Folder watcher unavailable. Run: pip install watchdog"
        
        folder_path = os.path.expanduser(folder_path)
        if not os.path.exists(folder_path):
            return f"Folder not found: {folder_path}"
        
        if folder_path in self._observers:
            return f"Already watching: {folder_path}"

        try:
            handler = JarvisFileHandler(
                folder_path=folder_path,
                broadcast_fn=self._broadcast_fn,
                auto_organize=auto_organize
            )
            if self._loop:
                handler.set_loop(self._loop)

            observer = Observer()
            observer.schedule(handler, folder_path, recursive=False)
            observer.daemon = True
            observer.start()

            self._observers[folder_path] = observer
            logger.info(f"Started watching folder: {folder_path}")
            mode = "with auto-organize" if auto_organize else "in monitor mode"
            return f"Now watching folder: {folder_path} {mode}"

        except Exception as e:
            logger.error(f"Failed to start folder watcher: {e}")
            return f"Failed to watch folder: {str(e)}"

    def unwatch(self, folder_path: str) -> str:
        """Stops watching a specific directory."""
        folder_path = os.path.expanduser(folder_path)
        observer = self._observers.pop(folder_path, None)
        if observer:
            observer.stop()
            observer.join(timeout=2)
            return f"Stopped watching: {folder_path}"
        return f"Folder not being watched: {folder_path}"

    def list_watched(self) -> List[Dict]:
        """Returns a list of currently watched folders."""
        return [
            {"path": path, "active": obs.is_alive()}
            for path, obs in self._observers.items()
        ]

    def shutdown(self):
        """Stops all watchers."""
        for path, observer in list(self._observers.items()):
            try:
                observer.stop()
                observer.join(timeout=2)
            except Exception:
                pass
        self._observers.clear()
        logger.info("All folder watchers stopped.")


folder_watcher = FolderWatcher()
