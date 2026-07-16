import os
import shutil
import logging
from typing import Dict, List

logger = logging.getLogger("jarvis.automation.organizer")

class FolderOrganizer:
    def __init__(self):
        # Mappings of file extensions to subfolders
        self.extension_map = {
            "Documents": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".pptx", ".csv", ".rtf"],
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".webp", ".ico"],
            "Archives": [".zip", ".rar", ".tar", ".gz", ".7z", ".pkg"],
            "Installers": [".exe", ".msi", ".dmg", ".iso"],
            "Code": [".py", ".js", ".html", ".css", ".json", ".cpp", ".c", ".java", ".sh", ".bat"],
            "Audio_Video": [".mp3", ".wav", ".mp4", ".avi", ".mkv", ".mov", ".flac"]
        }

    def organize_folder(self, target_dir: str) -> str:
        """Sorts files in the target folder into appropriate subfolders.
        
        Args:
            target_dir: Absolute path of folder to organize.
        """
        if not os.path.exists(target_dir):
            return f"Folder organizing failed: Path '{target_dir}' does not exist."
            
        logger.info(f"Organizing files in directory: {target_dir}")
        moved_count = 0
        skipped_count = 0
        
        try:
            # List items in the target dir
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                
                # We only organize files, not subdirectories
                if not os.path.isfile(item_path):
                    continue
                    
                filename, ext = os.path.splitext(item.lower())
                
                # Determine folder category
                target_category = "Others"
                for category, extensions in self.extension_map.items():
                    if ext in extensions:
                        target_category = category
                        break
                        
                # Create category folder
                category_dir = os.path.join(target_dir, target_category)
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir)
                    
                # Move file
                dest_path = os.path.join(category_dir, item)
                
                # Handle filename collisions
                if os.path.exists(dest_path):
                    skipped_count += 1
                    logger.warning(f"File {item} already exists in {category_dir}. Skipped to prevent overwrite.")
                    continue
                    
                shutil.move(item_path, dest_path)
                moved_count += 1
                
            return f"Organizing complete for '{target_dir}'. Sorted {moved_count} file(s) into category folders. (Skipped {skipped_count} conflicting file(s))."
            
        except Exception as e:
            logger.error(f"Error organizing directory {target_dir}: {e}")
            return f"Organizing failed: {str(e)}"

folder_organizer = FolderOrganizer()
