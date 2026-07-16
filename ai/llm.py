import logging
import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any, Union
from openai import OpenAI as SyncOpenAI
from google import genai
from google.genai import types
from config.config import settings

logger = logging.getLogger("jarvis.ai.llm")

class LLMManager:
    def __init__(self):
        self._openai_client = None
        self._ollama_client = None
        self._gemini_client = None

    def _get_openai_client(self) -> SyncOpenAI:
        if not self._openai_client:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API Key is missing. Please configure it in your settings or .env file.")
            self._openai_client = SyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    def _get_ollama_client(self) -> SyncOpenAI:
        if not self._ollama_client:
            self._ollama_client = SyncOpenAI(
                base_url=f"{settings.OLLAMA_HOST}/v1",
                api_key="ollama"
            )
        return self._ollama_client

    def _get_gemini_client(self) -> genai.Client:
        if not self._gemini_client:
            if not settings.GEMINI_API_KEY:
                raise ValueError("Gemini API Key is missing. Please configure it in your settings or .env file.")
            self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_client

    async def stream_chat_with_tools(
        self, 
        history: List[Dict[str, Any]], 
        tools: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        """Runs the LLM completion model and supports tool calls.
        
        Returns a dictionary:
            {
                "type": "text" | "tool_call",
                "content": str (text content) or list of tool call dicts: [{"name": name, "args": args, "id": id}]
            }
        """
        provider = settings.AI_PROVIDER.lower()
        logger.info(f"Running LLM with provider: {provider}")

        try:
            if provider == "openai":
                return await self._run_openai_tools(history, tools, system_prompt)
            elif provider == "ollama":
                return await self._run_ollama_tools(history, tools, system_prompt)
            else:
                # Default to gemini
                return await self._run_gemini_tools(history, tools, system_prompt)
        except Exception as e:
            logger.error(f"Error during LLM tool run with {provider}: {e}")
            return {
                "type": "text",
                "content": f"Error: I encountered a disruption in my thinking matrix. Details: {str(e)}"
            }

    async def _run_gemini_tools(
        self, 
        history: List[Dict[str, Any]], 
        tools: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        client = self._get_gemini_client()
        
        # Convert history into Gemini contents format
        gemini_contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            
            # Reconstruct content with tool results if present
            if msg.get("tool_calls"):
                # Append tool calls output
                parts = []
                for tc in msg["tool_calls"]:
                    parts.append(types.Part.from_function_call(
                        name=tc["name"],
                        args=tc["args"]
                    ))
                gemini_contents.append(types.Content(role=role, parts=parts))
            elif msg.get("role") == "tool":
                # This is a tool response
                gemini_contents.append(types.Content(
                    role="user", # Gemini represents tool results as user messages containing FunctionResponse parts
                    parts=[types.Part.from_function_response(
                        name=msg["name"],
                        response={"result": msg["content"]}
                    )]
                ))
            else:
                gemini_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

        # Convert schemas to Gemini format
        gemini_tools = []
        if tools:
            # Map standard JSON schemas to Gemini API Declarations
            declarations = []
            for t in tools:
                declarations.append(types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            k: types.Schema(
                                type=v["type"].upper(),
                                description=v.get("description", ""),
                                enum=v.get("enum")
                            ) for k, v in t["parameters"]["properties"].items()
                        },
                        required=t["parameters"].get("required", [])
                    )
                ))
            gemini_tools.append(types.Tool(function_declarations=declarations))

        # Invoke Gemini async
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                tools=gemini_tools if gemini_tools else None,
                system_instruction=system_prompt
            )
        )

        # Check for function calls
        if response.function_calls:
            calls = []
            for call in response.function_calls:
                calls.append({
                    "id": call.name, # Use name as ID for Gemini matching
                    "name": call.name,
                    "args": dict(call.args)
                })
            return {"type": "tool_call", "content": calls}
            
        return {"type": "text", "content": response.text or ""}

    async def _run_openai_tools(
        self, 
        history: List[Dict[str, Any]], 
        tools: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        client = self._get_openai_client()
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            m = {"role": msg["role"], "content": msg.get("content")}
            if msg.get("tool_calls"):
                m["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}
                    } for tc in msg["tool_calls"]
                ]
            if msg.get("tool_call_id"):
                m["tool_call_id"] = msg["tool_call_id"]
                m["name"] = msg.get("name")
            messages.append(m)

        # Format schemas for OpenAI
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": t
            })

        def _call():
            return client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None
            )

        response = await asyncio.to_thread(_call)
        msg_resp = response.choices[0].message
        
        if msg_resp.tool_calls:
            calls = []
            for tc in msg_resp.tool_calls:
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments)
                })
            return {"type": "tool_call", "content": calls}
            
        return {"type": "text", "content": msg_resp.content or ""}

    async def _run_ollama_tools(
        self, 
        history: List[Dict[str, Any]], 
        tools: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        client = self._get_ollama_client()
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            m = {"role": msg["role"], "content": msg.get("content")}
            if msg.get("tool_calls"):
                m["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}
                    } for tc in msg["tool_calls"]
                ]
            if msg.get("tool_call_id"):
                m["tool_call_id"] = msg["tool_call_id"]
                m["name"] = msg.get("name")
            messages.append(m)

        # Format schemas for Ollama
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": t
            })

        def _call():
            return client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=messages,
                tools=openai_tools if openai_tools else None
            )

        try:
            response = await asyncio.to_thread(_call)
            msg_resp = response.choices[0].message
            
            if msg_resp.tool_calls:
                calls = []
                for tc in msg_resp.tool_calls:
                    calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments)
                    })
                return {"type": "tool_call", "content": calls}
                
            return {"type": "text", "content": msg_resp.content or ""}
        except Exception as e:
            logger.error(f"Ollama tool calling error: {e}")
            raise RuntimeError(f"Ollama tool execution failed. Verify your Ollama instance at {settings.OLLAMA_HOST} is online.") from e

llm_manager = LLMManager()
