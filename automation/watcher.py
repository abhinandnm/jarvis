import os
import asyncio
import logging
from typing import Set, Callable

logger = logging.getLogger("jarvis.automation.watcher")

class DirectoryWatcher:
    def __init__(self):
        self.is_watching = False
        self.watch_path = ""
        self.known_files: Set[str] = set()
        self.callback: Callable[[str], None] = None
        self.task = None

    def start_watching(self, path: str, on_new_file_callback: Callable[[str], None]):
        """Starts the asynchronous polling watcher for a path."""
        if self.is_watching:
            self.stop_watching()
            
        if not os.path.exists(path):
            logger.warning(f"Cannot start watcher. Path '{path}' does not exist.")
            return

        self.watch_path = path
        self.callback = on_new_file_callback
        self.is_watching = True
        
        # Initialize baseline file list
        try:
            self.known_files = set(os.listdir(self.watch_path))
        except Exception as e:
            logger.error(f"Error reading baseline directory for watcher: {e}")
            self.known_files = set()
            
        logger.info(f"Directory watcher started for path: {self.watch_path}")
        
        # Spawn polling task in the active event loop
        self.task = asyncio.create_task(self._watch_loop())

    def stop_watching(self):
        """Stops the directory watcher."""
        self.is_watching = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("Directory watcher stopped.")

    async def _watch_loop(self):
        """Asynchronous folder scanning loop."""
        try:
            while self.is_watching:
                await asyncio.sleep(5.0)  # Scan every 5 seconds
                
                if not os.path.exists(self.watch_path):
                    continue
                    
                try:
                    current_files = set(os.listdir(self.watch_path))
                    new_files = current_files - self.known_files
                    
                    if new_files:
                        for filename in new_files:
                            full_path = os.path.join(self.watch_path, filename)
                            # Verify it is indeed a file and fully copied
                            if os.path.isfile(full_path):
                                logger.info(f"New file detected by watcher: {filename}")
                                if self.callback:
                                    # Execute callback
                                    self.callback(full_path)
                                    
                    # Update cache
                    self.known_files = current_files
                except Exception as e:
                    logger.error(f"Error in directory watcher polling loop: {e}")
        except asyncio.CancelledError:
            pass  # Task cancelled

directory_watcher = DirectoryWatcher()
