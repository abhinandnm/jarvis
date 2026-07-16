import os
import glob
import logging
from typing import List, Dict, Any

logger = logging.getLogger("jarvis.tools.file_search")

class FileSearchEngine:
    def __init__(self):
        # Default scan roots: Desktop, Documents, Downloads, and Workspace
        self.home_dir = os.path.expanduser("~")
        self.default_paths = [
            os.path.join(self.home_dir, "Downloads"),
            os.path.join(self.home_dir, "Documents"),
            os.path.join(self.home_dir, "Desktop"),
            os.getcwd()  # Workspace root
        ]

    def search(self, pattern: str, search_dir: str = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Searches recursively for files matching a pattern.
        
        Args:
            pattern: Glob-style query or simple text search (e.g., "*.pdf", "report").
            search_dir: Custom starting directory. If None, uses default user folders.
            limit: Maximum result returns.
        """
        # Format the query: add wildcards if not present
        if "*" not in pattern and "?" not in pattern:
            search_pattern = f"*{pattern}*"
        else:
            search_pattern = pattern

        search_paths = [search_dir] if search_dir else self.default_paths
        results = []

        logger.info(f"Initiating file search for '{search_pattern}' across: {search_paths}")
        
        for path in search_paths:
            if not path or not os.path.exists(path):
                continue
                
            try:
                # Walk directories up to depth of 3 to avoid infinite scanning of deep system files
                for root, dirs, files in os.walk(path):
                    # Limit depth of scan
                    depth = root[len(path):].count(os.sep)
                    if depth > 3:
                        # Clear dirs to prevent walking deeper
                        dirs.clear()
                        continue
                        
                    # Filter matching files
                    for file in files:
                        if self._match_filename(file.lower(), search_pattern.lower()):
                            full_path = os.path.join(root, file)
                            try:
                                size = os.path.getsize(full_path)
                                mtime = os.path.getmtime(full_path)
                            except OSError:
                                size = 0
                                mtime = 0
                                
                            results.append({
                                "filename": file,
                                "path": full_path.replace("\\", "/"),
                                "size_bytes": size,
                                "modified_time": mtime
                            })
                            
                            if len(results) >= limit:
                                return results
            except Exception as e:
                logger.error(f"Error scanning folder {path}: {e}")

        return results

    def _match_filename(self, name: str, pattern: str) -> bool:
        """Helper to match filenames using simple glob logic."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

file_search_engine = FileSearchEngine()
