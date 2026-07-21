import uvicorn
import logging
import asyncio
import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.config import settings, BASE_DIR
from database.database import init_db
from api.routes import router as api_router
from api.websockets import router as ws_router, manager
from speech.wake_word import WakeWordDetector


# ──────────────────────────────────────────────────────────────────────────────
# .env File Management — read/write API keys persistently
# ──────────────────────────────────────────────────────────────────────────────

ENV_FILE = BASE_DIR / ".env"


def read_env_dict() -> dict:
    """Reads the .env file into a dict preserving order and comments."""
    data = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip()
    return data


def write_env_dict(data: dict):
    """Writes the dict back to the .env file."""
    lines = []
    for key, value in data.items():
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_env_value(key: str, value: str):
    """Sets a single key in the .env file (creates the file if missing)."""
    data = read_env_dict()
    data[key] = value
    write_env_dict(data)


def reload_settings_from_env():
    """Reloads settings attributes from the current .env file."""
    data = read_env_dict()
    if data.get("AI_PROVIDER"):
        settings.AI_PROVIDER = data["AI_PROVIDER"]
    if data.get("GEMINI_API_KEY"):
        settings.GEMINI_API_KEY = data["GEMINI_API_KEY"]
    if data.get("OPENAI_API_KEY"):
        settings.OPENAI_API_KEY = data["OPENAI_API_KEY"]
    if data.get("GITHUB_TOKEN"):
        settings.GITHUB_TOKEN = data["GITHUB_TOKEN"]


PLACEHOLDER_KEYS = {
    "your_gemini_api_key_here", "your_openai_api_key_here",
    "your-api-key-here", "sk-xxx", "", "none", "null"
}


def _is_valid_key(key: str | None) -> bool:
    """Returns True only if the key is a real, non-placeholder value."""
    if not key:
        return False
    return key.strip().lower() not in PLACEHOLDER_KEYS and len(key.strip()) > 8


def _type_slow(text: str, delay: float = 0.02):
    """Prints text character-by-character for a cinematic effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def _print_stark_banner():
    """Prints the Stark Industries boot banner."""
    banner = r"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║         ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗              ║
    ║         ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝              ║
    ║         ██║███████║██████╔╝██║   ██║██║███████╗              ║
    ║    ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║              ║
    ║    ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║              ║
    ║     ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝              ║
    ║                                                               ║
    ║       Just A Rather Very Intelligent System  v1.0.0           ║
    ║                  STARK INDUSTRIES                             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def pre_boot_setup():
    """Interactive pre-boot setup — ALWAYS runs on every start.
    Checks API configuration, prompts for keys if missing/placeholder,
    then waits for user confirmation before booting."""

    os.system("cls" if os.name == "nt" else "clear")
    _print_stark_banner()

    provider = settings.AI_PROVIDER or "gemini"
    gemini_ok = _is_valid_key(settings.GEMINI_API_KEY)
    openai_ok = _is_valid_key(settings.OPENAI_API_KEY)

    # Determine if current provider has a valid key
    current_key_ok = (
        (provider == "gemini" and gemini_ok) or
        (provider == "openai" and openai_ok) or
        (provider == "ollama")
    )

    if not current_key_ok:
        # ── API Key Setup ─────────────────────────────────────────
        print("  ┌─────────────────────────────────────────────────┐")
        print("  │         SYSTEM CONFIGURATION REQUIRED           │")
        print("  │     No valid AI API key detected, Sir.          │")
        print("  └─────────────────────────────────────────────────┘")
        print()
        print("  Which AI provider shall I connect to?")
        print()
        print("    [1]  Google Gemini   ─  recommended, free tier")
        print("    [2]  OpenAI GPT      ─  GPT-4o, requires paid key")
        print("    [3]  Ollama          ─  fully local, no key needed")
        print()

        while True:
            choice = input("  Select provider [1/2/3]: ").strip()
            if choice in ("1", "2", "3"):
                break
            print("  Invalid selection. Please enter 1, 2, or 3.")

        if choice == "1":
            print()
            print("  ╭─ Get a free Gemini API key at:")
            print("  │  https://aistudio.google.com/apikey")
            print("  ╰────────────────────────────────────")
            print()
            api_key = input("  Enter your Gemini API key: ").strip()
            if api_key and api_key.lower() not in PLACEHOLDER_KEYS:
                set_env_value("AI_PROVIDER", "gemini")
                set_env_value("GEMINI_API_KEY", api_key)
                settings.AI_PROVIDER = "gemini"
                settings.GEMINI_API_KEY = api_key
                print("  ✓ Gemini API key saved.")
            else:
                print("  ✗ No valid key entered. You can set it later: set api key")

        elif choice == "2":
            print()
            print("  ╭─ Get an OpenAI API key at:")
            print("  │  https://platform.openai.com/api-keys")
            print("  ╰────────────────────────────────────")
            print()
            api_key = input("  Enter your OpenAI API key: ").strip()
            if api_key and api_key.lower() not in PLACEHOLDER_KEYS:
                set_env_value("AI_PROVIDER", "openai")
                set_env_value("OPENAI_API_KEY", api_key)
                settings.AI_PROVIDER = "openai"
                settings.OPENAI_API_KEY = api_key
                print("  ✓ OpenAI API key saved.")
            else:
                print("  ✗ No valid key entered. You can set it later: set api key")

        elif choice == "3":
            set_env_value("AI_PROVIDER", "ollama")
            settings.AI_PROVIDER = "ollama"
            print("  ✓ Ollama selected. Ensure Ollama is running on localhost:11434")

        print()
    else:
        # Key is valid — show current config
        provider_display = settings.AI_PROVIDER.upper()
        if settings.AI_PROVIDER == "gemini":
            masked = f"...{settings.GEMINI_API_KEY[-6:]}"
        elif settings.AI_PROVIDER == "openai":
            masked = f"...{settings.OPENAI_API_KEY[-6:]}"
        else:
            masked = "N/A (local)"

        print(f"  AI Provider:  {provider_display}")
        print(f"  API Key:      {masked}")
        print(f"  Model:        {getattr(settings, f'{settings.AI_PROVIDER.upper()}_MODEL', 'default')}")
        print()

    # ── Press Enter to Boot ────────────────────────────────────
    print("  ─" * 30)
    input("\n  Press ENTER to initialize J.A.R.V.I.S. ...\n")


def cinematic_boot_sequence():
    """Plays an Iron Man cinematic boot sequence in the terminal."""
    os.system("cls" if os.name == "nt" else "clear")

    # Arc Reactor power-up
    _type_slow("  [STARK INDUSTRIES — CLASSIFIED]")
    print()
    time.sleep(0.3)

    _type_slow("  Initializing Arc Reactor core.............. ", 0.015)
    time.sleep(0.2)
    print("  ████████████████████████████████ 100%")
    time.sleep(0.3)

    boot_steps = [
        ("Neural interface calibration",       0.25),
        ("Holographic display matrices",       0.20),
        ("Repulsor systems diagnostics",       0.15),
        ("Voice recognition module",           0.20),
        ("Long-term memory banks",             0.15),
        ("Agent orchestrator framework",       0.20),
        ("Tool registry integration",          0.15),
        ("Threat assessment protocols",        0.10),
        ("Communication arrays",              0.15),
    ]

    print()
    for step_name, delay in boot_steps:
        sys.stdout.write(f"  ► {step_name:<40s}")
        sys.stdout.flush()
        time.sleep(delay)
        print("[  OK  ]")

    print()
    time.sleep(0.3)
    _type_slow("  ╔═══════════════════════════════════════════════╗", 0.008)
    _type_slow("  ║                                               ║", 0.008)
    _type_slow("  ║    All systems operational, Sir.              ║", 0.008)
    _type_slow("  ║    J.A.R.V.I.S. is at your service.           ║", 0.008)
    _type_slow("  ║                                               ║", 0.008)
    _type_slow("  ╚═══════════════════════════════════════════════╝", 0.008)
    print()
    time.sleep(0.5)

    _type_slow("  \"Good evening, Sir. All systems are nominal.")
    _type_slow("   I've prepared a full diagnostic of your environment.")
    _type_slow("   Shall we begin?\"")
    print()
    time.sleep(0.5)

# Setup log formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("jarvis.main")

# Keep a reference to the main event loop for threadsafe callbacks
main_loop = None

def on_wake_word_detected():
    """Callback triggered from the background wake word thread."""
    logger.info("Wake word callback invoked! Triggering listening state in client.")
    if main_loop and main_loop.is_running():
        # Broadcast the listening state to the frontend
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "state", "content": "listening"}),
            main_loop
        )

# Initialize wake word detector
wake_detector = WakeWordDetector(on_wake_callback=on_wake_word_detected)

async def console_input_loop():
    """Reads user directives from the server terminal console asynchronously."""
    await asyncio.sleep(3.0)  # Wait for startup print logs to quiet down
    print("\n" + "="*60)
    print("  J.A.R.V.I.S. INTERACTIVE CONSOLE ONLINE")
    print("  Type your commands/queries below, Sir.")
    print("  Console commands:")
    print("    voice mode      — Hands-free voice operation")
    print("    set api key     — Change your AI API key")
    print("    set provider    — Switch AI provider")
    print("    show config     — Show current configuration")
    print("    exit / quit     — Disconnect console")
    print("="*60 + "\n")
    
    from core.agent import agent_orchestrator
    
    while True:
        try:
            user_input = await asyncio.to_thread(input, "Sir > ")
            user_input = user_input.strip()
            if not user_input:
                continue

            lower = user_input.lower()

            # ── Console Meta Commands ─────────────────────────────────
            if lower in ["exit", "quit"]:
                print("Deactivating console input link...")
                break

            elif lower == "set api key":
                await _handle_set_api_key()
                continue

            elif lower == "set provider":
                await _handle_set_provider()
                continue

            elif lower == "show config":
                _handle_show_config()
                continue

            elif lower in ["voice mode", "voice", "listen"]:
                await _voice_mode_loop()
                continue

            # ── Normal AI Query ───────────────────────────────────────
            print("Communicating with agent orchestrator...")
            print("Jarvis: ", end="", flush=True)
            
            full_response = []
            async def dummy_broadcast(msg):
                pass
                
            async for response in agent_orchestrator.process_user_input(
                user_input,
                websocket_broadcast_fn=dummy_broadcast
            ):
                if response["type"] == "text":
                    print(response["content"], end="", flush=True)
                    full_response.append(response["content"])
            print("\n")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\nDirective execution failure: {e}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Voice Mode — Fully hands-free voice operation
# ──────────────────────────────────────────────────────────────────────────────

async def _play_tts_audio(text: str):
    """Synthesizes speech and plays it through system speakers."""
    if not text.strip():
        return
    try:
        from speech.tts import tts_manager
        audio_data = await tts_manager.synthesize(text)
        if not audio_data:
            return

        # Save to temp file and play
        suffix = ".mp3" if settings.TTS_PROVIDER != "local" else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=str(BASE_DIR / "cache")) as f:
            f.write(audio_data)
            tmp_path = f.name

        try:
            # Use Windows Media Player (built-in, zero dependencies)
            if os.name == "nt":
                # PowerShell media player — plays and waits
                ps_cmd = (
                    f'powershell -NoProfile -Command "'
                    f'Add-Type -AssemblyName PresentationCore; '
                    f'$p = New-Object System.Windows.Media.MediaPlayer; '
                    f'$p.Open([Uri]\'{tmp_path}\'); '
                    f'$p.Play(); '
                    f'Start-Sleep -Milliseconds 500; '
                    f'while ($p.NaturalDuration.HasTimeSpan -and $p.Position -lt $p.NaturalDuration.TimeSpan) {{ Start-Sleep -Milliseconds 100 }}; '
                    f'Start-Sleep -Milliseconds 200; '
                    f'$p.Close()"'
                )
                await asyncio.to_thread(os.system, ps_cmd)
            else:
                # Linux/Mac fallback
                await asyncio.to_thread(os.system, f'ffplay -nodisp -autoexit "{tmp_path}" 2>/dev/null')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.error(f"TTS playback error: {e}")


async def _listen_once() -> str:
    """Listens to the microphone once and returns the transcribed text.
    Uses sounddevice for recording (no PyAudio dependency needed)."""
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    import speech_recognition as sr
    import io
    import wave

    SAMPLE_RATE = 16000
    CHANNELS = 1
    SILENCE_THRESHOLD = 0.01  # RMS threshold to detect silence
    SILENCE_DURATION = 1.5    # Seconds of silence before stopping
    MAX_DURATION = 15         # Max recording seconds
    MIN_SPEECH_DURATION = 0.5 # Min seconds of audio to consider valid

    def _blocking_listen():
        print("  🎤 Listening...", end="", flush=True)

        try:
            # Record with voice activity detection
            frames = []
            silence_frames = 0
            speech_started = False
            frames_per_check = int(SAMPLE_RATE * 0.1)  # 100ms chunks
            silence_limit = int(SILENCE_DURATION / 0.1)
            max_chunks = int(MAX_DURATION / 0.1)

            for i in range(max_chunks):
                chunk = sd.rec(frames_per_check, samplerate=SAMPLE_RATE,
                             channels=CHANNELS, dtype='int16', blocking=True)
                frames.append(chunk)

                # Check RMS energy
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0

                if rms > SILENCE_THRESHOLD:
                    speech_started = True
                    silence_frames = 0
                elif speech_started:
                    silence_frames += 1
                    if silence_frames >= silence_limit:
                        break  # User stopped speaking

            if not speech_started:
                print(" (no speech)")
                return ""

            total_audio = np.concatenate(frames, axis=0)
            duration = len(total_audio) / SAMPLE_RATE
            if duration < MIN_SPEECH_DURATION:
                print(" (too short)")
                return ""

            print(" Processing...", end="", flush=True)

            # Convert to WAV bytes in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(total_audio.tobytes())

            wav_buffer.seek(0)

            # Feed to speech_recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio)
                return text.strip()
            except sr.UnknownValueError:
                print(" (couldn't understand)")
                return ""
            except sr.RequestError as e:
                print(f" (API error: {e})")
                return ""

        except Exception as e:
            print(f" (mic error: {e})")
            return ""

    result = await asyncio.to_thread(_blocking_listen)
    return result


async def _voice_mode_loop():
    """Continuous voice interaction loop — fully hands-free."""
    print()
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║         VOICE MODE ACTIVATED                  ║")
    print("  ║                                               ║")
    print("  ║   Speak naturally. I'm listening, Sir.        ║")
    print("  ║   Say 'exit voice mode' to return to console. ║")
    print("  ║   Press Ctrl+C to force stop.                 ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print()

    # Announce voice mode activation via TTS
    await _play_tts_audio("Voice mode activated. I'm listening, Sir.")

    from core.agent import agent_orchestrator

    while True:
        try:
            # 1. Listen for speech
            transcription = await _listen_once()

            if not transcription:
                print("  (no speech detected)")
                continue

            print(f"  You: {transcription}")

            # Check for exit command
            if any(phrase in transcription.lower() for phrase in [
                "exit voice mode", "stop voice mode", "quit voice mode",
                "deactivate voice", "stop listening", "switch to text"
            ]):
                print("\n  Voice mode deactivated. Returning to console.\n")
                await _play_tts_audio("Voice mode deactivated, Sir. Returning to console.")
                break

            # 2. Send to AI agent
            print("  Jarvis: ", end="", flush=True)
            full_response = []

            async def dummy_broadcast(msg):
                pass

            async for response in agent_orchestrator.process_user_input(
                transcription,
                websocket_broadcast_fn=dummy_broadcast
            ):
                if response["type"] == "text":
                    print(response["content"], end="", flush=True)
                    full_response.append(response["content"])

            response_text = "".join(full_response).strip()
            print("\n")

            # 3. Speak the response
            if response_text:
                await _play_tts_audio(response_text)

        except KeyboardInterrupt:
            print("\n  Voice mode interrupted. Returning to console.\n")
            break
        except Exception as e:
            print(f"\n  Voice mode error: {e}")
            continue


async def _handle_set_api_key():
    """Interactive API key changer from the console."""
    provider = settings.AI_PROVIDER
    print(f"\n  Current provider: {provider}")
    if provider == "gemini":
        key_label = "Gemini API key"
        env_key = "GEMINI_API_KEY"
        current = settings.GEMINI_API_KEY
    elif provider == "openai":
        key_label = "OpenAI API key"
        env_key = "OPENAI_API_KEY"
        current = settings.OPENAI_API_KEY
    else:
        print("  Ollama does not require an API key.")
        return

    masked = f"...{current[-6:]}" if current and len(current) > 6 else "(not set)"
    print(f"  Current {key_label}: {masked}")
    new_key = await asyncio.to_thread(input, f"  Enter new {key_label} (blank to cancel): ")
    new_key = new_key.strip()
    if new_key:
        set_env_value(env_key, new_key)
        setattr(settings, env_key, new_key)
        print(f"  ✓ {key_label} updated and saved to .env\n")
    else:
        print("  Cancelled.\n")


async def _handle_set_provider():
    """Switch AI provider from the console."""
    print(f"\n  Current provider: {settings.AI_PROVIDER}")
    print("    1) gemini")
    print("    2) openai")
    print("    3) ollama")
    choice = await asyncio.to_thread(input, "  Select [1/2/3]: ")
    choice = choice.strip()
    provider_map = {"1": "gemini", "2": "openai", "3": "ollama"}
    if choice in provider_map:
        new_provider = provider_map[choice]
        set_env_value("AI_PROVIDER", new_provider)
        settings.AI_PROVIDER = new_provider
        print(f"  ✓ Provider switched to '{new_provider}' and saved to .env")

        # If switching to a key-based provider, offer to set the key
        if new_provider in ("gemini", "openai"):
            env_key = "GEMINI_API_KEY" if new_provider == "gemini" else "OPENAI_API_KEY"
            existing = getattr(settings, env_key, None)
            if not existing:
                key = await asyncio.to_thread(input, f"  Enter your {new_provider} API key: ")
                key = key.strip()
                if key:
                    set_env_value(env_key, key)
                    setattr(settings, env_key, key)
                    print(f"  ✓ API key saved.")
    else:
        print("  Invalid choice.")
    print()


def _handle_show_config():
    """Prints current configuration to the console."""
    gemini_masked = f"...{settings.GEMINI_API_KEY[-6:]}" if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 6 else "(not set)"
    openai_masked = f"...{settings.OPENAI_API_KEY[-6:]}" if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 6 else "(not set)"
    gh_token = getattr(settings, 'GITHUB_TOKEN', None)
    gh_masked = f"...{gh_token[-6:]}" if gh_token and len(gh_token) > 6 else "(not set)"

    print(f"""
  ┌─────────────────────────────────────┐
  │  J.A.R.V.I.S. CONFIGURATION        │
  ├─────────────────────────────────────┤
  │  AI Provider:    {settings.AI_PROVIDER:<18s}│
  │  Gemini Model:   {settings.GEMINI_MODEL:<18s}│
  │  Gemini Key:     {gemini_masked:<18s}│
  │  OpenAI Model:   {settings.OPENAI_MODEL:<18s}│
  │  OpenAI Key:     {openai_masked:<18s}│
  │  Ollama Model:   {settings.OLLAMA_MODEL:<18s}│
  │  TTS Provider:   {settings.TTS_PROVIDER:<18s}│
  │  TTS Voice:      {settings.TTS_VOICE:<18s}│
  │  STT Provider:   {settings.STT_PROVIDER:<18s}│
  │  Wake Word:      {settings.WAKE_WORD:<18s}│
  │  GitHub Token:   {gh_masked:<18s}│
  │  .env Location:  {str(ENV_FILE)[:18]:<18s}│
  └─────────────────────────────────────┘
""")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # 1. Initialize SQLite Database
    await init_db()
    
    # 1b. Initialize Automation Scheduler and Folder Watcher
    logger.info("Initializing Automation Scheduler...")
    from automation.scheduler import jarvis_scheduler
    from automation.folder_watcher import folder_watcher
    jarvis_scheduler.initialize(broadcast_fn=manager.broadcast)
    folder_watcher.initialize(broadcast_fn=manager.broadcast, loop=main_loop)
    
    # 1c. Start Console Input Reader Task
    cli_task = asyncio.create_task(console_input_loop())
    
    # 2. Start the wake word detector
    logger.info("Starting background wake-word listener...")
    wake_detector.start()
    
    yield
    
    # 3. Shutdown background task
    logger.info("Stopping background wake-word listener...")
    wake_detector.stop()
    
    # 3b. Shutdown scheduler and folder watcher
    logger.info("Stopping Automation Scheduler and Folder Watchers...")
    jarvis_scheduler.shutdown()
    folder_watcher.shutdown()
    
    # 3c. Cancel Console input link
    cli_task.cancel()
    try:
        await cli_task
    except asyncio.CancelledError:
        pass

# Create FastAPI app
app = FastAPI(
    title="J.A.R.V.I.S. Local API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Electron local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Ensure cache directory exists
if not os.path.exists("cache"):
    os.makedirs("cache")

# Add routes
app.include_router(api_router)
app.include_router(ws_router)
app.mount("/cache", StaticFiles(directory="cache"), name="cache")

if __name__ == "__main__":
    # Phase 1: Pre-boot config check — always runs
    pre_boot_setup()

    # Phase 2: Cinematic Iron Man boot sequence
    cinematic_boot_sequence()

    # Phase 3: Launch the server
    uvicorn.run(
        "main.py:app" if os.getenv("DEV") else app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False  # Re-loading can cause multi-thread audio issues
    )
