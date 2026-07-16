import uvicorn
import logging
import asyncio
import os
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


def first_run_setup():
    """Interactive first-run setup — asks for API key if none found in .env."""
    has_gemini = bool(settings.GEMINI_API_KEY)
    has_openai = bool(settings.OPENAI_API_KEY)

    if has_gemini or has_openai:
        # Keys already configured, skip setup
        return

    print()
    print("=" * 60)
    print("  J.A.R.V.I.S. FIRST-TIME SETUP")
    print("  No AI API key detected. Let's configure one now.")
    print("=" * 60)
    print()
    print("  Which AI provider would you like to use?")
    print("    1) Google Gemini  (recommended, free tier available)")
    print("    2) OpenAI GPT")
    print("    3) Ollama  (local, no API key needed)")
    print()

    while True:
        choice = input("  Select provider [1/2/3]: ").strip()
        if choice in ("1", "2", "3"):
            break
        print("  Please enter 1, 2, or 3.")

    if choice == "1":
        provider = "gemini"
        print()
        print("  Get a free Gemini API key at: https://aistudio.google.com/apikey")
        api_key = input("  Enter your Gemini API key: ").strip()
        if api_key:
            set_env_value("AI_PROVIDER", "gemini")
            set_env_value("GEMINI_API_KEY", api_key)
            settings.AI_PROVIDER = "gemini"
            settings.GEMINI_API_KEY = api_key
            print(f"  ✓ Gemini API key saved to {ENV_FILE}")
        else:
            print("  ✗ No key entered. You can set it later with: set api key")

    elif choice == "2":
        provider = "openai"
        print()
        print("  Get an OpenAI API key at: https://platform.openai.com/api-keys")
        api_key = input("  Enter your OpenAI API key: ").strip()
        if api_key:
            set_env_value("AI_PROVIDER", "openai")
            set_env_value("OPENAI_API_KEY", api_key)
            settings.AI_PROVIDER = "openai"
            settings.OPENAI_API_KEY = api_key
            print(f"  ✓ OpenAI API key saved to {ENV_FILE}")
        else:
            print("  ✗ No key entered. You can set it later with: set api key")

    elif choice == "3":
        set_env_value("AI_PROVIDER", "ollama")
        settings.AI_PROVIDER = "ollama"
        print("  ✓ Ollama selected. Make sure Ollama is running on localhost:11434")

    # Optional: ask for GitHub token
    print()
    gh_token = input("  (Optional) Enter GitHub token for plugin [press Enter to skip]: ").strip()
    if gh_token:
        set_env_value("GITHUB_TOKEN", gh_token)
        print("  ✓ GitHub token saved.")

    print()
    print("  Setup complete! Starting J.A.R.V.I.S...")
    print("=" * 60)
    print()

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

            # ── Normal AI Query ───────────────────────────────────────
            print("Communicating with agent orchestrator...")
            print("Jarvis: ", end="", flush=True)
            
            async def dummy_broadcast(msg):
                pass
                
            async for response in agent_orchestrator.process_user_input(
                user_input,
                websocket_broadcast_fn=dummy_broadcast
            ):
                if response["type"] == "text":
                    print(response["content"], end="", flush=True)
            print("\n")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\nDirective execution failure: {e}\n")


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
    # Run first-time interactive setup if no API key found
    first_run_setup()

    uvicorn.run(
        "main.py:app" if os.getenv("DEV") else app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False  # Re-loading can cause multi-thread audio issues, better to run static
    )
