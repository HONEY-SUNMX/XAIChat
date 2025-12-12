#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic Models for API Request/Response
Data validation and serialization schemas.

Author: Generated with love by Harei-chan
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Chat Models
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    stream: bool = Field(True, description="Enable streaming response")
    enable_thinking: bool = Field(True, description="Enable thinking mode (deep reasoning)")


class ChatMessage(BaseModel):
    """Single chat message."""
    role: Literal["user", "assistant", "thinking"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    response: str = Field(..., description="Assistant response")
    thinking: Optional[str] = Field(None, description="Thinking process")
    conversation_id: str = Field(..., description="Conversation ID")


class ChatStreamEvent(BaseModel):
    """Streaming chat event."""
    type: Literal["thinking", "response", "done", "error"] = Field(..., description="Event type")
    content: Optional[str] = Field(None, description="Event content")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")


# =============================================================================
# Vision Models
# =============================================================================

class VisionUploadResponse(BaseModel):
    """Vision image upload response."""
    image_id: str = Field(..., description="Unique image identifier")
    filename: str = Field(..., description="Original filename")
    size: List[int] = Field(..., description="Image dimensions [width, height]")
    message: str = Field("Image uploaded successfully", description="Status message")


class VisionAskRequest(BaseModel):
    """Vision question request."""
    image_id: str = Field(..., description="Image ID to ask about")
    question: str = Field(..., min_length=1, description="Question about the image")
    stream: bool = Field(True, description="Enable streaming response")


class VisionResponse(BaseModel):
    """Non-streaming vision response."""
    response: str = Field(..., description="Vision model response")
    image_id: str = Field(..., description="Image ID")


class VisionStreamEvent(BaseModel):
    """Streaming vision event."""
    type: Literal["response", "done", "error"] = Field(..., description="Event type")
    content: Optional[str] = Field(None, description="Event content")


# =============================================================================
# Image Generation Models
# =============================================================================

class ImageGenerateRequest(BaseModel):
    """Image generation request."""
    prompt: str = Field(..., min_length=1, description="Image description prompt")
    negative_prompt: str = Field("", description="Negative prompt")
    width: int = Field(512, ge=256, le=1024, description="Image width")
    height: int = Field(512, ge=256, le=1024, description="Image height")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    num_steps: int = Field(6, ge=1, le=50, description="Number of inference steps")


class ImageGenerateResponse(BaseModel):
    """Non-streaming image generation response."""
    image_url: str = Field(..., description="URL to download the generated image")
    filename: str = Field(..., description="Generated image filename")
    seed: int = Field(..., description="Seed used for generation")


class ImageProgressEvent(BaseModel):
    """Image generation progress event."""
    type: Literal["progress", "done", "error"] = Field(..., description="Event type")
    step: Optional[int] = Field(None, description="Current step")
    total: Optional[int] = Field(None, description="Total steps")
    image_url: Optional[str] = Field(None, description="Generated image URL")
    filename: Optional[str] = Field(None, description="Generated image filename")
    error: Optional[str] = Field(None, description="Error message")


# =============================================================================
# Common Models
# =============================================================================

class StatusResponse(BaseModel):
    """Generic status response."""
    status: str = Field(..., description="Status message")
    success: bool = Field(True, description="Operation success flag")


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("healthy", description="Service status")
    version: str = Field(..., description="API version")
    models: dict = Field(..., description="Model status")
