#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multimodal Chat API Router"""

import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pathlib import Path
import shutil

from server.services.multimodal_service import multimodal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multimodal", tags=["Multimodal Chat"])

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class MultimodalChatRequest(BaseModel):
    """Multimodal chat request (for JSON payload without file upload)"""
    message: str = Field(..., description="User's text message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID to maintain context")
    enable_thinking: bool = Field(True, description="Enable deep reasoning mode")
    stream: bool = Field(True, description="Enable streaming response")


class MultimodalChatResponse(BaseModel):
    """Multimodal chat response (non-streaming)"""
    response: str
    conversation_id: str
    thinking: Optional[str] = None
    image_url: Optional[str] = None


@router.post("/chat", summary="Multimodal chat - text only")
async def multimodal_chat(request: MultimodalChatRequest):
    """
    Multimodal chat with text input only.

    - **message**: User's message
    - **conversation_id**: Optional ID to maintain conversation context
    - **stream**: If True, returns SSE stream; otherwise returns JSON
    - **enable_thinking**: If True, enables deep reasoning mode

    The service will automatically detect if user wants to:
    - Have a normal text conversation
    - Generate an image (keywords: "画", "生成图片", "draw", etc.)

    SSE Stream Events:
    - `thinking`: Model's thinking process (only when enable_thinking=True)
    - `thinking_stream`: Real-time thinking content (only when enable_thinking=True)
    - `response`: Text response content
    - `image_generated`: Generated image info (when image generation is triggered)
    - `progress`: Image generation progress
    - `done`: Generation complete with conversation_id
    - `error`: Error occurred
    """
    try:
        if request.stream:
            return StreamingResponse(
                multimodal_service.stream_response(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    image_path=None,
                    enable_thinking=request.enable_thinking
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            result = await multimodal_service.get_response(
                message=request.message,
                conversation_id=request.conversation_id,
                image_path=None,
                enable_thinking=request.enable_thinking
            )
            return MultimodalChatResponse(**result)

    except Exception as e:
        logger.error(f"[Multimodal] Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/chat-with-image", summary="Multimodal chat - with image upload")
async def multimodal_chat_with_image(
    message: str = Form(..., description="User's text message"),
    file: UploadFile = File(..., description="Image file to analyze"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID"),
    enable_thinking: bool = Form(True, description="Enable deep reasoning mode"),
):
    """
    Multimodal chat with image upload and text message.

    This endpoint allows users to upload an image and ask questions about it
    within an ongoing conversation.

    Form Data:
    - **message**: Question or comment about the image
    - **file**: Image file (JPEG, PNG, etc.)
    - **conversation_id**: Optional conversation ID
    - **enable_thinking**: Enable deep reasoning mode

    Returns SSE stream with:
    - `response`: AI's analysis and answer
    - `done`: Complete with conversation_id
    - `error`: Error occurred
    """
    try:
        # Import vision service
        from server.services.vision_service import vision_service
        
        # Upload image through vision_service to register it
        upload_result = await vision_service.upload_image(file)
        image_id = upload_result['image_id']
        
        logger.info(f"[Multimodal] Image registered with ID: {image_id}")

        # Stream response - pass image_id instead of path
        return StreamingResponse(
            multimodal_service.stream_response(
                message=message,
                conversation_id=conversation_id,
                image_id=image_id,
                enable_thinking=enable_thinking
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Multimodal] Chat with image failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat with image failed: {str(e)}")


@router.get("/conversation/{conversation_id}", summary="Get conversation history")
async def get_conversation(conversation_id: str):
    """
    Get multimodal conversation history.

    Returns:
        List of messages with type annotations (text/image_analysis/generated_image)
    """
    try:
        history = multimodal_service.get_conversation(conversation_id)
        return {"conversation_id": conversation_id, "messages": history}

    except Exception as e:
        logger.error(f"[Multimodal] Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.delete("/conversation/{conversation_id}", summary="Clear conversation")
async def clear_conversation(conversation_id: str):
    """
    Clear multimodal conversation history.
    """
    try:
        multimodal_service.clear_conversation(conversation_id)
        return {"message": "Conversation cleared", "conversation_id": conversation_id}

    except Exception as e:
        logger.error(f"[Multimodal] Failed to clear conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation: {str(e)}")
