import logging
import re
import datetime
import base64
import asyncio
import json
from typing import AsyncGenerator, Dict, List, Any, Callable
from sqlalchemy.future import select

from database.database import AsyncSessionLocal
from database.models import ChatHistory, MemoryEntry
from ai.llm import llm_manager
from speech.tts import tts_manager
from core.tool_registry import tool_registry
from memory.memory_engine import memory_engine
from config.config import settings

logger = logging.getLogger("jarvis.core.agent")

class AgentOrchestrator:
    def __init__(self):
        pass

    async def get_recent_history(self, session_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieves recent chat history from SQLite database including tool traces."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatHistory)
                .filter(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.timestamp.asc())
            )
            histories = result.scalars().all()
            
            # Reconstruct conversational history with tool payloads if present
            formatted = []
            for h in histories[-limit:]:
                try:
                    payload = json.loads(h.content) if h.content.startswith("{") or h.content.startswith("[") else h.content
                except Exception:
                    payload = h.content
                
                # Setup proper schema dictionaries
                if h.role == "tool":
                    formatted.append({
                        "role": "tool",
                        "name": h.model, # Use model column temporarily to store tool name
                        "tool_call_id": h.provider, # Use provider column to store tool call ID
                        "content": payload
                    })
                elif h.role == "assistant" and isinstance(payload, dict) and "tool_calls" in payload:
                    formatted.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": payload["tool_calls"]
                    })
                else:
                    formatted.append({
                        "role": h.role,
                        "content": payload
                    })
            return formatted

    async def save_message(self, role: str, content: str, session_id: str = "default", provider: str = None, model: str = None):
        """Saves a message or tool execution trace to the SQLite chat history."""
        async with AsyncSessionLocal() as session:
            try:
                msg = ChatHistory(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider,
                    model=model
                )
                session.add(msg)
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to save message to history: {e}")
                await session.rollback()

    async def process_user_input(
        self, 
        user_text: str, 
        websocket_broadcast_fn: Callable[[dict], Any],
        session_id: str = "default"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Processes user input recursively. Handles database recall, memory injection, tool calls, and text streaming."""
        # 1. Save user text
        await self.save_message("user", user_text, session_id)
        
        # 2. Retrieve memories & inject into system prompt
        memories = await memory_engine.get_relevant_memories(user_text)
        system_prompt = settings.SYSTEM_PROMPT
        if memories:
            memory_context = "\n\n[MEMORIES RECALLED]:\n" + "\n".join(
                [f"- Fact: {m['key']} = {m['value']} (Category: {m['category']})" for m in memories]
            )
            system_prompt += memory_context
            logger.info("Injected relevant memories into system prompt.")

        # 3. Pull chat history
        history = await self.get_recent_history(session_id)
        
        # Recursive Tool Execution Loop
        tool_loop_limit = 5
        loop_count = 0
        
        # Tools definitions schema
        tools_schema = tool_registry.get_tool_schemas()

        while loop_count < tool_loop_limit:
            loop_count += 1
            yield {"type": "state", "content": "thinking"}
            
            # Query LLM
            llm_result = await llm_manager.stream_chat_with_tools(history, tools_schema, system_prompt)
            
            if llm_result["type"] == "tool_call":
                tool_calls = llm_result["content"]
                logger.info(f"LLM triggered tool calls: {tool_calls}")
                
                # Save assistant function request payload to DB history
                await self.save_message(
                    role="assistant", 
                    content=json.dumps({"tool_calls": tool_calls}), 
                    session_id=session_id
                )
                
                # Notify UI about active tool run
                for call in tool_calls:
                    yield {
                        "type": "text", 
                        "content": f"[Commanding system: {call['name']} ({list(call['args'].values())})]...\n"
                    }
                
                # Execute all requested tool calls
                for call in tool_calls:
                    # Run tool
                    tool_output = await tool_registry.execute_tool(
                        name=call["name"], 
                        args=call["args"], 
                        websocket_broadcast_fn=websocket_broadcast_fn
                    )
                    
                    # Log result
                    logger.info(f"Tool {call['name']} returned output: '{tool_output}'")
                    yield {
                        "type": "text", 
                        "content": f"[System returns]: {tool_output}\n\n"
                    }
                    
                    # Save tool result in DB history
                    await self.save_message(
                        role="tool", 
                        content=tool_output, 
                        session_id=session_id,
                        provider=call["id"], # Store tool call ID in provider
                        model=call["name"]   # Store tool name in model
                    )
                    
                # Re-fetch updated history including the tool inputs/outputs and continue loop
                history = await self.get_recent_history(session_id)
                continue
                
            else:
                # Text generation completed, streaming verbal synthesis to user
                text_response = llm_result["content"]
                yield {"type": "state", "content": "speaking"}
                
                # Stream the final text response out to the client
                sentence_buffer = ""
                sentence_end = re.compile(r'([.!?])\s*')
                
                # Stream words and speak segments on the fly
                words = text_response.split(" ")
                for word in words:
                    chunk = f"{word} "
                    sentence_buffer += chunk
                    
                    # Stream token
                    yield {"type": "text", "content": chunk}
                    await asyncio.sleep(0.02) # Typing delay
                    
                    matches = list(sentence_end.finditer(sentence_buffer))
                    if matches:
                        last_match_end = matches[-1].end()
                        sentence_to_speak = sentence_buffer[:last_match_end].strip()
                        sentence_buffer = sentence_buffer[last_match_end:]
                        
                        if sentence_to_speak and len(sentence_to_speak) > 2:
                            audio_bytes = await tts_manager.synthesize(sentence_to_speak)
                            if audio_bytes:
                                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                                yield {"type": "audio", "content": audio_b64}
                                
                # Handle remaining buffer
                remaining = sentence_buffer.strip()
                if remaining:
                    audio_bytes = await tts_manager.synthesize(remaining)
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                        yield {"type": "audio", "content": audio_b64}
                
                # Save assistant text message to DB history
                await self.save_message("assistant", text_response, session_id)
                break
        
        yield {"type": "state", "content": "idle"}

agent_orchestrator = AgentOrchestrator()
