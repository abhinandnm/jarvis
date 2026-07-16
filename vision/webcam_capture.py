import os
import logging

logger = logging.getLogger("jarvis.vision.webcam")

class WebcamCapturer:
    def __init__(self):
        self.cache_dir = os.path.join(os.getcwd(), "cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def capture(self) -> str:
        """Captures a single frame from the default webcam device.
        
        Returns:
            str: Path to the saved webcam image file.
        """
        # Dynamic import of cv2 to avoid errors if opencv package failed installation
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV library 'cv2' is not installed or available.")

        logger.info("Initializing webcam capture device...")
        # Bind to default webcam index 0
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            raise RuntimeError("Webcam device could not be opened. Verify it is plugged in or not used by another program.")

        try:
            # Let the camera auto-adjust white balance/exposure by reading and discarding first few frames
            for _ in range(5):
                cap.read()
                
            ret, frame = cap.read()
            if not ret or frame is None:
                raise RuntimeError("Failed to retrieve image frame from webcam.")
                
            temp_path = os.path.join(self.cache_dir, "webcam_view.jpg")
            # Save using OpenCV imwrite
            cv2.imwrite(temp_path, frame)
            logger.info(f"Webcam frame saved to {temp_path}")
            return temp_path
            
        finally:
            # Ensure device release is always called
            cap.release()
            logger.info("Webcam device released.")

webcam_capturer = WebcamCapturer()
