import io
import logging
import speech_recognition as sr
from config.config import settings

logger = logging.getLogger("jarvis.speech.stt")

class STTManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Adjust recognizer sensitivity settings
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 0.8

    def transcribe_audio_bytes(self, audio_data: bytes, sample_rate: int = 16000, sample_width: int = 2) -> str:
        """Transcribes raw PCM audio bytes.
        
        Args:
            audio_data: Raw PCM audio bytes.
            sample_rate: Audio sampling rate.
            sample_width: Number of bytes per sample (e.g., 2 for 16-bit).
        """
        try:
            # Create a speech recognition AudioData object
            sr_audio = sr.AudioData(audio_data, sample_rate, sample_width)
            
            # Perform transcription based on config
            if settings.STT_PROVIDER == "openai" and settings.OPENAI_API_KEY:
                # Transcribe using OpenAI API
                logger.info("Transcribing using OpenAI Whisper API...")
                # SpeechRecognition has built-in support for OpenAI Whisper API
                result = self.recognizer.recognize_whisper_api(
                    sr_audio, 
                    api_key=settings.OPENAI_API_KEY
                )
                return result.strip()
            else:
                # Default to Google Speech Recognition (free, no API key required)
                logger.info("Transcribing using Google Speech Recognition...")
                result = self.recognizer.recognize_google(sr_audio)
                return result.strip()
                
        except sr.UnknownValueError:
            logger.debug("Speech recognition could not understand audio.")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return ""

    def transcribe_file(self, file_path: str) -> str:
        """Transcribes an audio file (wav, mp3, etc.) using SpeechRecognition."""
        try:
            with sr.AudioFile(file_path) as source:
                audio = self.recognizer.record(source)
                
            if settings.STT_PROVIDER == "openai" and settings.OPENAI_API_KEY:
                result = self.recognizer.recognize_whisper_api(
                    audio, 
                    api_key=settings.OPENAI_API_KEY
                )
            else:
                result = self.recognizer.recognize_google(audio)
            return result.strip()
        except Exception as e:
            logger.error(f"Failed to transcribe file {file_path}: {e}")
            return ""

stt_manager = STTManager()
