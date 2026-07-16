import asyncio
import logging
import threading
import speech_recognition as sr
from config.config import settings

logger = logging.getLogger("jarvis.speech.wakeword")

class WakeWordDetector:
    def __init__(self, on_wake_callback=None):
        self.on_wake_callback = on_wake_callback
        self.is_running = False
        self.thread = None
        self._stop_listening = None

    def start(self):
        """Starts the background wake word listener."""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_listener, daemon=True)
        self.thread.start()
        logger.info("Wake word detector background thread started.")

    def stop(self):
        """Stops the background listener."""
        self.is_running = False
        if self._stop_listening:
            try:
                self._stop_listening(wait_for_stop=False)
            except Exception as e:
                logger.error(f"Error stopping wake word listener function: {e}")
        logger.info("Wake word detector stopped.")

    def _run_listener(self):
        """Main loop running inside the background thread."""
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            # Calibrate for ambient noise
            with microphone as source:
                logger.info("Calibrating microphone for ambient noise (1 second)...")
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
            
            logger.info(f"Microphone calibrated. Listening for wake word '{settings.WAKE_WORD}'...")
            
            def callback(rec, audio):
                if not self.is_running:
                    return
                try:
                    # Perform fast local transcription of the phrase
                    logger.debug("Wake word audio captured, processing...")
                    text = rec.recognize_google(audio).lower()
                    logger.debug(f"Heard background audio: '{text}'")
                    
                    if settings.WAKE_WORD.lower() in text:
                        logger.info(f"Wake word '{settings.WAKE_WORD}' detected!")
                        if self.on_wake_callback:
                            # Run the callback in the event loop of the main thread
                            self.on_wake_callback()
                except sr.UnknownValueError:
                    pass  # Speech was unintelligible
                except sr.RequestError as e:
                    logger.error(f"Wake word API request error: {e}")
                except Exception as e:
                    logger.error(f"Wake word callback processing error: {e}")

            # Start listening in background (native SpeechRecognition method)
            self._stop_listening = recognizer.listen_in_background(microphone, callback, phrase_time_limit=3.0)
            
            # Keep the thread alive as long as we are running
            while self.is_running:
                threading.Event().wait(1.0)
                
        except (OSError, AttributeError) as e:
            logger.warning(
                "Could not initialize microphone or PyAudio is not installed. "
                "Wake word detection will be disabled. You can still use the frontend microphone button. "
                f"Error details: {e}"
            )
            self.is_running = False
        except Exception as e:
            logger.error(f"Wake word listener thread encountered error: {e}")
            self.is_running = False
