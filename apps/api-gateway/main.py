from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# import models
# from database import engine
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Enterprise AI Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to NextChat's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api-gateway"}

# from auth.router import router as auth_router
# app.include_router(auth_router)
# from auth.router import get_current_user

class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list = []
    stream: bool = False

import httpx

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "meta-llama/Meta-Llama-3-8B-Instruct", "object": "model", "created": 1677610602, "owned_by": "huggingface"},
            {"id": "HuggingFaceH4/zephyr-7b-beta", "object": "model", "created": 1677610602, "owned_by": "huggingface"},
            {"id": "mistralai/Mistral-7B-Instruct-v0.2", "object": "model", "created": 1677610602, "owned_by": "huggingface"}
        ]
    }

from fastapi.responses import StreamingResponse

@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    # Determine user and role (Depends would go here if we enforced auth for this route)
    
    import os
    # Forward the request to HuggingFace OpenAI-compatible Inference API
    hf_api_key = os.environ.get("HF_API_KEY", "")
    
    # We will use the user's local Ollama via localtunnel
    model = "qwen2.5:latest"
    hf_url = "https://common-months-shine.loca.lt/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "bypass-tunnel-reminder": "true" # Required by localtunnel to bypass the warning page
    }
    
    # Override the model in the payload
    request["model"] = model
    
    # Strip parameters that HuggingFace might reject
    allowed_keys = {"model", "messages", "stream", "temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens"}
    clean_request = {k: v for k, v in request.items() if k in allowed_keys}
    # -------------------------------------------------------------
    # RAG AGENT LOGIC
    # -------------------------------------------------------------
    import rag_agent
    
    # Get the last user message to fetch context
    user_message = ""
    messages = request.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
            
    # Fetch context from local files
    print(f"Invoking RAG Agent to fetch context...", flush=True)
    context = rag_agent.get_rag_context(user_message)
    if context:
        # Inject context into the user's prompt
        augmented_prompt = f"You have access to the following local documents from the user's Downloads folder:\n\n<context>\n{context}\n</context>\n\nAnswer the user's question using the context above if relevant. If the provided documents are not relevant, just answer normally.\n\nQuestion: {user_message}"
        # Update the last user message in the request payload
        for msg in reversed(request.get("messages", [])):
            if msg.get("role") == "user":
                msg["content"] = augmented_prompt
                break
    else:
        print(f"No local context found. Proceeding normally.", flush=True)
        
    # -------------------------------------------------------------
    # END RAG AGENT LOGIC
    # -------------------------------------------------------------

    is_stream = request.get("stream", False)
    
    try:
        if is_stream:
            # We must use a background client for streaming that stays alive during the generator
            async def stream_generator():
                try:
                    print(f"Sending request to Ollama: {clean_request}", flush=True)
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", hf_url, headers=headers, json=clean_request, timeout=30.0) as response:
                            response.raise_for_status()
                            async for chunk in response.aiter_bytes():
                                yield chunk
                except httpx.HTTPStatusError as e:
                    import json
                    try:
                        await e.response.aread()
                        error_details = e.response.text
                    except Exception:
                        error_details = "Stream closed or unreadable"
                    error_msg = f"\n\n**[API Gateway Error]**: Ollama returned HTTP {e.response.status_code}.\nDetails: {error_details}"
                    yield f'data: {json.dumps({"id": "err", "object": "chat.completion.chunk", "model": model, "choices": [{"index": 0, "delta": {"content": error_msg}}]})}\n\n'.encode('utf-8')
                    yield b"data: [DONE]\n\n"
                except Exception as e:
                    import json
                    error_msg = f"\n\n**[API Gateway Error]**: {str(e)}"
                    yield f'data: {json.dumps({"id": "err", "object": "chat.completion.chunk", "model": model, "choices": [{"index": 0, "delta": {"content": error_msg}}]})}\n\n'.encode('utf-8')
                    yield b"data: [DONE]\n\n"
                    
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(hf_url, headers=headers, json=clean_request, timeout=30.0)
                response.raise_for_status()
                return response.json()
    except httpx.HTTPStatusError as e:
        error_details = e.response.text
        user_message = request.get("messages", [])[-1].get("content", "") if request.get("messages") else ""
        return {
            "id": "chatcmpl-fallback",
            "object": "chat.completion",
            "created": 1677652288,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[HF API Error]: {str(e)} - {error_details}\n\nOriginal message: {user_message}"
                },
                "finish_reason": "stop"
            }]
        }
    except Exception as e:
        user_message = request.get("messages", [])[-1].get("content", "") if request.get("messages") else ""
        return {
            "id": "chatcmpl-fallback",
            "object": "chat.completion",
            "created": 1677652288,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[HF API Error]: {str(e)}\n\nOriginal message: {user_message}"
                },
                "finish_reason": "stop"
            }]
        }
