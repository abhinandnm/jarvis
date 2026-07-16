"""
API Routes — FastAPI HTTP routes for JARVIS system data and settings.
Provides endpoints for: stats, settings, processes, voices, memory,
scheduler tasks, plugins, notifications, clipboard history, and GPU.
"""

import psutil
import logging
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from config.config import settings, Settings

logger = logging.getLogger("jarvis.api.routes")
router = APIRouter(prefix="/api")


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Request Models
# ──────────────────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    ai_provider: str
    gemini_model: str
    openai_model: str
    ollama_model: str
    stt_provider: str
    tts_provider: str
    tts_voice: str
    wake_word: str


class MemoryFactRequest(BaseModel):
    key: str
    value: str
    category: str = "general"


class ScheduledTaskRequest(BaseModel):
    name: str
    command: str
    trigger_type: str           # 'cron', 'interval', 'date'
    interval_seconds: Optional[int] = 3600
    cron_expression: Optional[str] = "0 9 * * *"
    run_at: Optional[str] = None
    description: Optional[str] = None


class FolderWatchRequest(BaseModel):
    folder_path: str
    auto_organize: bool = False


# ──────────────────────────────────────────────────────────────────────────────
# System Stats
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Retrieve real-time system diagnostics for the HUD dashboard."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        # Battery
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 100
        power_plugged = battery.power_plugged if battery else True

        # Temperature (platform-dependent)
        temp = 0.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if "cpu" in entry.label.lower() or "core" in entry.label.lower() or "package" in name.lower():
                            temp = entry.current
                            break
                    if temp > 0:
                        break
        except Exception:
            pass

        # GPU stats (nvidia-smi, fall back gracefully)
        gpu_usage = 0
        gpu_name = "N/A"
        gpu_memory = 0
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                if len(parts) >= 4:
                    gpu_name = parts[0]
                    gpu_usage = float(parts[1])
                    used_mb = float(parts[2])
                    total_mb = float(parts[3])
                    gpu_memory = round((used_mb / total_mb) * 100, 1) if total_mb > 0 else 0
        except Exception:
            pass

        # Network status
        network_status = "online"
        try:
            net = psutil.net_io_counters()
            network_status = "online" if net.bytes_sent > 0 else "offline"
        except Exception:
            pass

        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "battery": battery_percent,
            "power_plugged": power_plugged,
            "temperature": temp,
            "network_status": network_status,
            "gpu_usage": gpu_usage,
            "gpu_name": gpu_name,
            "gpu_memory": gpu_memory
        }
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve system diagnostics.")


@router.get("/processes")
async def get_running_processes() -> List[Dict[str, Any]]:
    """Retrieve top memory-consuming processes for the process monitor."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'status']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory": round(proc.info['memory_percent'] or 0, 1),
                    "cpu": round(proc.info['cpu_percent'] or 0, 1),
                    "status": proc.info.get('status', 'running')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        processes.sort(key=lambda x: x['memory'], reverse=True)
        return processes[:15]
    except Exception as e:
        logger.error(f"Error fetching processes: {e}")
        return []


@router.get("/network")
async def get_network_stats() -> Dict[str, Any]:
    """Returns network interface statistics."""
    try:
        net = psutil.net_io_counters()
        interfaces = {}
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface, addr_list in addrs.items():
            iface_stats = stats.get(iface)
            ipv4 = next((a.address for a in addr_list if a.family.name == "AF_INET"), "N/A")
            interfaces[iface] = {
                "ip": ipv4,
                "is_up": iface_stats.isup if iface_stats else False,
                "speed_mbps": iface_stats.speed if iface_stats else 0
            }

        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "interfaces": interfaces
        }
    except Exception as e:
        logger.error(f"Error fetching network stats: {e}")
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Get the active JARVIS configuration."""
    return {
        "ai_provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "ollama_model": settings.OLLAMA_MODEL,
        "stt_provider": settings.STT_PROVIDER,
        "tts_provider": settings.TTS_PROVIDER,
        "tts_voice": settings.TTS_VOICE,
        "wake_word": settings.WAKE_WORD,
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_github_token": bool(getattr(settings, "GITHUB_TOKEN", None))
    }


@router.post("/settings")
async def update_settings(data: SettingsUpdate) -> Dict[str, str]:
    """Update JARVIS settings on-the-fly."""
    try:
        settings.AI_PROVIDER = data.ai_provider
        settings.GEMINI_MODEL = data.gemini_model
        settings.OPENAI_MODEL = data.openai_model
        settings.OLLAMA_MODEL = data.ollama_model
        settings.STT_PROVIDER = data.stt_provider
        settings.TTS_PROVIDER = data.tts_provider
        settings.TTS_VOICE = data.tts_voice
        settings.WAKE_WORD = data.wake_word
        logger.info("Settings updated successfully.")
        return {"status": "success", "message": "Settings updated"}
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/voices")
async def list_voices() -> Dict[str, List[Dict[str, str]]]:
    """List supported TTS voices."""
    return {
        "edge_tts": [
            {"id": "en-US-GuyNeural", "name": "Guy (Male, English US)"},
            {"id": "en-US-AriaNeural", "name": "Aria (Female, English US)"},
            {"id": "en-US-AndrewNeural", "name": "Andrew (Male, English US)"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (Female, English UK)"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (Male, English UK)"},
            {"id": "en-IN-NeerjaNeural", "name": "Neerja (Female, English India)"},
            {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Male, English India)"},
            {"id": "en-AU-NatashaNeural", "name": "Natasha (Female, English AU)"},
        ],
        "local": [
            {"id": "0", "name": "Default Local Male Voice"},
            {"id": "1", "name": "Default Local Female Voice"}
        ],
        "openai": [
            {"id": "alloy", "name": "Alloy"},
            {"id": "echo", "name": "Echo"},
            {"id": "fable", "name": "Fable"},
            {"id": "onyx", "name": "Onyx (Deep Male)"},
            {"id": "nova", "name": "Nova (Female)"},
            {"id": "shimmer", "name": "Shimmer (Soft Female)"}
        ]
    }


# ──────────────────────────────────────────────────────────────────────────────
# Memory CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/memory")
async def get_memories(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all stored memory facts, optionally filtered by category."""
    from memory.memory_engine import memory_engine
    return await memory_engine.get_all_memories(category)


@router.post("/memory")
async def save_memory(data: MemoryFactRequest) -> Dict[str, str]:
    """Save a new memory fact."""
    from memory.memory_engine import memory_engine
    result = await memory_engine.save_memory_fact(data.key, data.value, data.category)
    return {"status": "success", "message": result}


@router.delete("/memory/{key}")
async def delete_memory(key: str) -> Dict[str, str]:
    """Delete a stored memory fact by key."""
    from memory.memory_engine import memory_engine
    result = await memory_engine.delete_memory(key)
    return {"status": "success", "message": result}


@router.get("/memory/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics for the UI dashboard."""
    from memory.memory_engine import memory_engine
    return await memory_engine.get_memory_stats()


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/scheduler")
async def list_scheduled_tasks() -> List[Dict[str, Any]]:
    """List all scheduled automation tasks."""
    try:
        from automation.scheduler import jarvis_scheduler
        return jarvis_scheduler.list_tasks()
    except Exception as e:
        logger.error(f"Scheduler list error: {e}")
        return []


@router.post("/scheduler")
async def create_scheduled_task(data: ScheduledTaskRequest) -> Dict[str, str]:
    """Create a new scheduled task."""
    try:
        from automation.scheduler import jarvis_scheduler
        import uuid

        task_id = str(uuid.uuid4())[:8]
        trigger_type = data.trigger_type

        if trigger_type == "interval":
            config = {"seconds": data.interval_seconds or 3600}
        elif trigger_type == "cron":
            expr = (data.cron_expression or "0 9 * * *").strip().split()
            config = {
                "minute": expr[0], "hour": expr[1],
                "day": expr[2], "month": expr[3], "day_of_week": expr[4]
            }
        elif trigger_type == "date":
            if not data.run_at:
                raise HTTPException(status_code=400, detail="run_at is required for date trigger")
            config = {"run_date": data.run_at}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown trigger type: {trigger_type}")

        result = jarvis_scheduler.add_task(
            task_id=task_id,
            name=data.name,
            command=data.command,
            trigger_type=trigger_type,
            trigger_config=config
        )
        return {"status": "success", "message": result, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduler/{task_id}")
async def delete_scheduled_task(task_id: str) -> Dict[str, str]:
    """Remove a scheduled task."""
    from automation.scheduler import jarvis_scheduler
    result = jarvis_scheduler.remove_task(task_id)
    return {"status": "success", "message": result}


# ──────────────────────────────────────────────────────────────────────────────
# Plugins
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/plugins")
async def list_plugins() -> List[Dict[str, Any]]:
    """List all loaded plugins with their metadata."""
    from plugins.loader import plugin_loader
    return plugin_loader.get_plugin_info()


# ──────────────────────────────────────────────────────────────────────────────
# Clipboard History
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/clipboard")
async def get_clipboard_history() -> List[Dict[str, Any]]:
    """Returns the clipboard history tracked by JARVIS."""
    from tools.clipboard_tool import clipboard_tool
    return clipboard_tool.get_history()


# ──────────────────────────────────────────────────────────────────────────────
# Folder Watcher
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/watchers")
async def list_watchers() -> List[Dict[str, Any]]:
    """List all active folder watchers."""
    from automation.folder_watcher import folder_watcher
    return folder_watcher.list_watched()


@router.post("/watchers")
async def start_watcher(data: FolderWatchRequest) -> Dict[str, str]:
    """Start watching a folder for new files."""
    from automation.folder_watcher import folder_watcher
    result = folder_watcher.watch(data.folder_path, data.auto_organize)
    return {"status": "success", "message": result}


@router.delete("/watchers")
async def stop_watcher(folder_path: str) -> Dict[str, str]:
    """Stop watching a folder."""
    from automation.folder_watcher import folder_watcher
    result = folder_watcher.unwatch(folder_path)
    return {"status": "success", "message": result}
