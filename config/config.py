import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    # AI Provider Settings
    # Supported: "gemini", "openai", "ollama"
    AI_PROVIDER: str = "gemini"
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # System Prompt (Jarvis Personality)
    SYSTEM_PROMPT: str = (
        "You are J.A.R.V.I.S., a highly advanced AI desktop assistant inspired by Iron Man. "
        "Your personality is polite, elegant, witty, and extremely competent. "
        "Address the user as 'Sir' or 'Madame' (default to 'Sir' unless instructed otherwise). "
        "Keep your responses concise, intelligent, and helpful. "
        "Never show any internal chain-of-thought or reasoning XML tags in your response. "
        "Respond only with the final output. Always maintain the Jarvis persona."
    )
    
    # Speech-to-Text (STT) Settings
    # Supported: "local" (speech_recognition), "openai" (whisper)
    STT_PROVIDER: str = "local"
    
    # Text-to-Speech (TTS) Settings
    # Supported: "edge-tts" (realistic free), "local" (pyttsx3 offline), "openai"
    TTS_PROVIDER: str = "edge-tts"
    TTS_VOICE: str = "en-US-GuyNeural"
    
    # Voice Activation
    WAKE_WORD: str = "jarvis"
    WAKE_WORD_SENSITIVITY: float = 0.5
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/jarvis.db"
    
    # Config loading
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
