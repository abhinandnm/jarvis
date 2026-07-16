import base64
import json
import logging
import tempfile
import os
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Set
from core.agent import agent_orchestrator
from speech.stt import stt_manager
from core.tool_registry import pending_permissions

logger = logging.getLogger("jarvis.api.websockets")
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining: {len(self.active_connections)}")

    async def send_json(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        logger.debug(f"Broadcasting message: {message['type']}")
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to a connection: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from the React frontend
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "chat":
                text = message.get("text", "")
                await handle_chat_query(text, websocket)
                
            elif msg_type == "audio":
                # User sent base64 encoded audio file (e.g. WAV format recorded on frontend)
                audio_b64 = message.get("data", "")
                if audio_b64:
                    await handle_audio_query(audio_b64, websocket)
                    
            elif msg_type == "interrupt":
                # Frontend requested to stop talking
                logger.info("Interrupt received: stopping assistant speech.")
                # The frontend will cancel its own audio player, but we also broadcast an idle state
                await manager.broadcast({"type": "state", "content": "idle"})
                
            elif msg_type == "permission_response":
                req_id = message.get("id")
                approved = message.get("approved", False)
                logger.info(f"Received permission response for request {req_id}: approved={approved}")
                if req_id in pending_permissions:
                    pending_permissions[req_id].set_result(approved)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket loop exception: {e}")
        manager.disconnect(websocket)

async def handle_chat_query(text: str, websocket: WebSocket):
    """Processes a text query and streams back the responses."""
    if not text.strip():
        return
        
    logger.info(f"Received chat query: '{text}'")
    
    # Process text using agent_orchestrator
    async for response in agent_orchestrator.process_user_input(
        text, 
        websocket_broadcast_fn=manager.broadcast
    ):
        await manager.send_json(response, websocket)

async def handle_audio_query(audio_b64: str, websocket: WebSocket):
    """Decodes audio base64 data, transcribes it, and triggers chat processing."""
    # 1. State: Thinking (while transcribing)
    await manager.send_json({"type": "state", "content": "thinking"}, websocket)
    
    try:
        # Decode base64 to binary WAV audio
        audio_bytes = base64.b64decode(audio_b64)
        
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_name = tmp_file.name
            tmp_file.write(audio_bytes)
            
        try:
            logger.info(f"Saved incoming audio to {tmp_name}, transcribing...")
            # Transcribe
            transcription = await asyncio.to_thread(stt_manager.transcribe_file, tmp_name)
            logger.info(f"Audio transcribed: '{transcription}'")
            
            # Send the transcription back to the user
            await manager.send_json({"type": "transcript", "content": transcription}, websocket)
            
            if transcription.strip():
                # Process the transcribed text as a chat query
                await handle_chat_query(transcription, websocket)
            else:
                # Idle if we didn't understand anything
                await manager.send_json({"type": "state", "content": "idle"}, websocket)
                
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
                
    except Exception as e:
        logger.error(f"Failed to process incoming audio: {e}")
        await manager.send_json({"type": "state", "content": "idle"}, websocket)
        await manager.send_json({"type": "text", "content": f"Error transcribing speech: {str(e)}"}, websocket)
