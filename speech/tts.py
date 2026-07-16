import io
import os
import asyncio
import logging
import tempfile
import pyttsx3
import edge_tts
from openai import OpenAI
from config.config import settings

logger = logging.getLogger("jarvis.speech.tts")

class TTSManager:
    def __init__(self):
        # Initialize pyttsx3 engine in a thread-safe way when needed, as it is synchronous
        self._local_engine_lock = asyncio.Lock()

    async def synthesize(self, text: str) -> bytes:
        """Synthesizes text into audio bytes.
        
        Returns:
            bytes: Audio content (typically MP3, or WAV for local).
        """
        provider = settings.TTS_PROVIDER.lower()
        
        if provider == "openai" and settings.OPENAI_API_KEY:
            return await self._synthesize_openai(text)
        elif provider == "local":
            return await self._synthesize_local(text)
        else:
            # Default fallback to edge-tts (free neural voices)
            return await self._synthesize_edge_tts(text)

    async def _synthesize_edge_tts(self, text: str) -> bytes:
        """Synthesizes speech using edge-tts (free neural voice)."""
        try:
            logger.info("Synthesizing with Edge-TTS...")
            voice = settings.TTS_VOICE or "en-US-GuyNeural"
            communicate = edge_tts.Communicate(text, voice)
            
            # Write to a temporary file and read the bytes back
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_name = tmp_file.name
                
            try:
                await communicate.save(tmp_name)
                with open(tmp_name, "rb") as f:
                    audio_data = f.read()
                return audio_data
            finally:
                if os.path.exists(tmp_name):
                    os.remove(tmp_name)
        except Exception as e:
            logger.error(f"Edge-TTS error: {e}. Falling back to offline local TTS.")
            return await self._synthesize_local(text)

    async def _synthesize_openai(self, text: str) -> bytes:
        """Synthesizes speech using OpenAI TTS API."""
        try:
            logger.info("Synthesizing with OpenAI TTS...")
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Run in thread pool to prevent blocking the event loop
            def _api_call():
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=settings.TTS_VOICE if settings.TTS_VOICE in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
                    input=text
                )
                return response.content
                
            return await asyncio.to_thread(_api_call)
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}. Falling back to edge-tts.")
            return await self._synthesize_edge_tts(text)

    async def _synthesize_local(self, text: str) -> bytes:
        """Synthesizes speech offline using pyttsx3."""
        async with self._local_engine_lock:
            try:
                logger.info("Synthesizing offline with pyttsx3...")
                # Write to file because pyttsx3's in-memory sound generation is platform-dependent
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_name = tmp_file.name
                
                def _speak():
                    engine = pyttsx3.init()
                    # Adjust speaking rate
                    engine.setProperty('rate', 175)
                    engine.save_to_file(text, tmp_name)
                    engine.runAndWait()
                    
                await asyncio.to_thread(_speak)
                
                try:
                    with open(tmp_name, "rb") as f:
                        audio_data = f.read()
                    return audio_data
                finally:
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
            except Exception as e:
                logger.error(f"Offline pyttsx3 error: {e}")
                return b""

tts_manager = TTSManager()
