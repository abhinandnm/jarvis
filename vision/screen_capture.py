import os
import logging
import tempfile
from PIL import Image
import pyautogui

logger = logging.getLogger("jarvis.vision.screen")

class ScreenCapturer:
    def __init__(self):
        # Create local cache folder for temporary visual files
        self.cache_dir = os.path.join(os.getcwd(), "cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def capture(self) -> str:
        """Captures the current screen state and saves to cache.
        
        Returns:
            str: Path to the saved image file.
        """
        try:
            logger.info("Capturing desktop screen...")
            # Take screenshot using pyautogui
            screenshot = pyautogui.screenshot()
            
            # Save to temporary path inside the cache folder
            temp_path = os.path.join(self.cache_dir, "screen_view.png")
            screenshot.save(temp_path)
            logger.info(f"Screenshot saved to {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            raise RuntimeError(f"Unable to capture screen: {str(e)}")

screen_capturer = ScreenCapturer()
