import uvicorn
import logging
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.config import settings
from database.database import init_db
from api.routes import router as api_router
from api.websockets import router as ws_router, manager
from speech.wake_word import WakeWordDetector

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
    print("  Type your commands/queries directly into the console, Sir.")
    print("="*60 + "\n")
    
    from core.agent import agent_orchestrator
    
    while True:
        try:
            # Read input in a separate thread so as not to block the event loop
            user_input = await asyncio.to_thread(input, "Sir > ")
            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Deactivating console input link...")
                break
                
            print("Communicating with agent orchestrator...")
            print("Jarvis: ", end="", flush=True)
            
            async def dummy_broadcast(msg):
                # Dummy handler for websocket messages
                pass
                
            async for response in agent_orchestrator.process_user_input(
                user_input,
                websocket_broadcast_fn=dummy_broadcast
            ):
                if response["type"] == "text":
                    # Stream the text output directly to the console
                    print(response["content"], end="", flush=True)
            print("\n")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\nDirective execution failure: {e}\n")

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
    uvicorn.run(
        "main.py:app" if os.getenv("DEV") else app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False  # Re-loading can cause multi-thread audio issues, better to run static
    )
