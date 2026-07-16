"""
OCR Tool — Extracts text from screenshots using pytesseract.
Supports full-screen OCR and region-based OCR (x, y, width, height).
Falls back gracefully if Tesseract is not installed.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("jarvis.tools.ocr")

# Attempt to import required vision libraries
try:
    import pytesseract
    from PIL import ImageGrab, Image
    TESSERACT_AVAILABLE = True
    # On Windows, set the Tesseract path if not in PATH
    if os.name == 'nt':
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or Pillow not installed. OCR tools unavailable.")


class OCRTool:
    """Handles Optical Character Recognition (OCR) operations."""

    def ocr_full_screen(self) -> str:
        """
        Captures the full screen and extracts all visible text via OCR.

        Returns:
            str: Extracted text, or an error message if OCR is unavailable.
        """
        if not TESSERACT_AVAILABLE:
            return (
                "OCR unavailable: Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki "
                "and run: pip install pytesseract pillow"
            )
        try:
            screenshot = ImageGrab.grab()
            text = pytesseract.image_to_string(screenshot, lang="eng")
            cleaned = text.strip()
            if not cleaned:
                return "No readable text found on screen."
            logger.info(f"OCR full screen extracted {len(cleaned)} characters.")
            return cleaned
        except Exception as e:
            logger.error(f"OCR full screen error: {e}")
            return f"OCR failed: {str(e)}"

    def ocr_region(self, x: int, y: int, width: int, height: int) -> str:
        """
        Captures a specific screen region and extracts text.

        Args:
            x: Left coordinate of the region.
            y: Top coordinate of the region.
            width: Width of the region in pixels.
            height: Height of the region in pixels.

        Returns:
            str: Extracted text from the specified region.
        """
        if not TESSERACT_AVAILABLE:
            return "OCR unavailable. Please install Tesseract OCR and pytesseract."
        try:
            region = (x, y, x + width, y + height)
            screenshot = ImageGrab.grab(bbox=region)
            text = pytesseract.image_to_string(screenshot, lang="eng")
            cleaned = text.strip()
            if not cleaned:
                return f"No readable text found in region ({x}, {y}, {width}x{height})."
            logger.info(f"OCR region ({x},{y},{width}x{height}) extracted {len(cleaned)} characters.")
            return cleaned
        except Exception as e:
            logger.error(f"OCR region error: {e}")
            return f"OCR region failed: {str(e)}"

    def ocr_image_file(self, image_path: str) -> str:
        """
        Performs OCR on an image file.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            str: Extracted text from the image.
        """
        if not TESSERACT_AVAILABLE:
            return "OCR unavailable. Please install Tesseract OCR and pytesseract."
        try:
            if not os.path.exists(image_path):
                return f"Image not found at path: {image_path}"
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang="eng")
            cleaned = text.strip()
            return cleaned if cleaned else "No text found in image."
        except Exception as e:
            logger.error(f"OCR image file error: {e}")
            return f"OCR image file failed: {str(e)}"


ocr_tool = OCRTool()
