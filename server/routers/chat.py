#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat API Router
Endpoints for text chat with Qwen3 model.

Author: Generated with love by Harei-chan
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from server.models.schemas import (
    ChatRequest,
    ChatResponse,
    StatusResponse,
)
from server.services.chat_service import chat_service


router = APIRouter()


@router.post("/", summary="Send a chat message")
async def chat(request: ChatRequest):
    """
    Send a message and get a response from Qwen3.

    - **message**: The user's message
    - **conversation_id**: Optional ID to maintain conversation context
    - **stream**: If True, returns SSE stream; otherwise returns JSON
    - **enable_thinking**: If True, enables deep reasoning mode (shows thinking process)

    SSE Stream Events:
    - `thinking`: Model's thinking process (only when enable_thinking=True)
    - `thinking_stream`: Real-time thinking content (only when enable_thinking=True)
    - `response`: Generated response content
    - `done`: Generation complete with conversation_id
    - `error`: Error occurred
    """
    try:
        if request.stream:
            return StreamingResponse(
                chat_service.stream_response(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    enable_thinking=request.enable_thinking
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                }
            )
        else:
            result = await chat_service.get_response(
                message=request.message,
                conversation_id=request.conversation_id,
                enable_thinking=request.enable_thinking
            )
            return ChatResponse(**result)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/{conversation_id}", summary="Get conversation history")
async def get_conversation(conversation_id: str):
    """
    Get the conversation history for a specific conversation ID.

    - **conversation_id**: The conversation ID to retrieve
    """
    history = chat_service.get_conversation(conversation_id)

    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "conversation_id": conversation_id,
        "messages": history
    }


@router.delete("/{conversation_id}", response_model=StatusResponse, summary="Clear conversation")
async def clear_conversation(conversation_id: str):
    """
    Clear the conversation history for a specific conversation ID.

    - **conversation_id**: The conversation ID to clear
    """
    success = chat_service.clear_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StatusResponse(
        status="Conversation cleared",
        success=True
    )


@router.get("/status/model", summary="Get chat model status")
async def get_model_status():
    """Check if the chat model is loaded."""
    return {
        "loaded": chat_service.is_loaded,
        "model_path": chat_service._llm.model_path if chat_service.is_loaded else None
    }
