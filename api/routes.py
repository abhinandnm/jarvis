import psutil
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from config.config import settings, Settings

logger = logging.getLogger("jarvis.api.routes")
router = APIRouter(prefix="/api")

# Pydantic models for request bodies
class SettingsUpdate(BaseModel):
    ai_provider: str
    gemini_model: str
    openai_model: str
    ollama_model: str
    stt_provider: str
    tts_provider: str
    tts_voice: str
    wake_word: str

@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Retrieve system diagnostics for dashboard."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Get battery status if available
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 100
        power_plugged = battery.power_plugged if battery else True

        # Get system temperatures if supported by hardware/OS
        temp = 0.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Find core temperature
                for name, entries in temps.items():
                    for entry in entries:
                        if "cpu" in entry.label.lower() or "core" in entry.label.lower():
                            temp = entry.current
                            break
        except Exception:
            pass  # Fallback for OS where temperatures aren't exposed

        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "battery": battery_percent,
            "power_plugged": power_plugged,
            "temperature": temp,
            "network_status": "online"  # Basic placeholder for now
        }
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve system diagnostics.")

@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Get active Jarvis configurations."""
    return {
        "ai_provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "ollama_model": settings.OLLAMA_MODEL,
        "stt_provider": settings.STT_PROVIDER,
        "tts_provider": settings.TTS_PROVIDER,
        "tts_voice": settings.TTS_VOICE,
        "wake_word": settings.WAKE_WORD,
        # Check if keys are present (boolean status, don't return raw key values)
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_openai_key": bool(settings.OPENAI_API_KEY)
    }

@router.post("/settings")
async def update_settings(data: SettingsUpdate) -> Dict[str, str]:
    """Update settings on-the-fly."""
    try:
        settings.AI_PROVIDER = data.ai_provider
        settings.GEMINI_MODEL = data.gemini_model
        settings.OPENAI_MODEL = data.openai_model
        settings.OLLAMA_MODEL = data.ollama_model
        settings.STT_PROVIDER = data.stt_provider
        settings.TTS_PROVIDER = data.tts_provider
        settings.TTS_VOICE = data.tts_voice
        settings.WAKE_WORD = data.wake_word
        
        logger.info("Configuration updated successfully.")
        return {"status": "success", "message": "Settings updated"}
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/voices")
async def list_voices() -> Dict[str, List[Dict[str, str]]]:
    """List supported voices."""
    # Hardcoded popular Edge-TTS voices + Local voices mapping
    return {
        "edge_tts": [
            {"id": "en-US-GuyNeural", "name": "Guy (Male, English US)"},
            {"id": "en-US-AriaNeural", "name": "Aria (Female, English US)"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (Female, English UK)"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (Male, English UK)"},
            {"id": "en-IN-NeerjaNeural", "name": "Neerja (Female, English India)"},
            {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Male, English India)"}
        ],
        "local": [
            {"id": "0", "name": "Default Local Male Voice"},
            {"id": "1", "name": "Default Local Female Voice"}
        ],
        "openai": [
            {"id": "alloy", "name": "Alloy"},
            {"id": "echo", "name": "Echo"},
            {"id": "fable", "name": "Fable"},
            {"id": "onyx", "name": "Onyx"},
            {"id": "nova", "name": "Nova"},
            {"id": "shimmer", "name": "Shimmer"}
        ]
    }

@router.get("/processes")
async def get_running_processes() -> List[Dict[str, Any]]:
    """Retrieve top CPU and Memory consuming processes."""
    processes = []
    try:
        # Fetch running processes
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
            try:
                # Add to list
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory": round(proc.info['memory_percent'] or 0, 1),
                    "cpu": round(proc.info['cpu_percent'] or 0, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by memory usage and return top 12
        processes.sort(key=lambda x: x['memory'], reverse=True)
        return processes[:12]
    except Exception as e:
        logger.error(f"Error fetching running processes: {e}")
        return []
