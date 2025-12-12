#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision API Router
Endpoints for image understanding with Qwen2-VL.

Author: Generated with love by Harei-chan
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from server.models.schemas import (
    VisionUploadResponse,
    VisionAskRequest,
    VisionResponse,
    StatusResponse,
)
from server.services.vision_service import vision_service


router = APIRouter()


@router.post("/upload", response_model=VisionUploadResponse, summary="Upload an image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image for visual Q&A.

    - **file**: Image file (JPG, PNG, GIF, BMP, WEBP supported)

    Returns image_id for subsequent questions.
    """
    try:
        result = await vision_service.upload_image(file)
        return VisionUploadResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/ask", summary="Ask a question about an image")
async def ask_about_image(request: VisionAskRequest):
    """
    Ask a question about a previously uploaded image.

    - **image_id**: ID of the uploaded image
    - **question**: Question about the image
    - **stream**: If True, returns SSE stream; otherwise returns JSON

    SSE Stream Events:
    - `response`: Generated response content
    - `done`: Generation complete
    - `error`: Error occurred
    """
    try:
        if request.stream:
            return StreamingResponse(
                vision_service.stream_response(
                    image_id=request.image_id,
                    question=request.question
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            result = await vision_service.get_response(
                image_id=request.image_id,
                question=request.question
            )
            return VisionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision query failed: {str(e)}")


@router.get("/{image_id}", summary="Get image information")
async def get_image_info(image_id: str):
    """
    Get information about an uploaded image.

    - **image_id**: ID of the uploaded image
    """
    info = vision_service.get_image_info(image_id)

    if info is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "image_id": image_id,
        "filename": info["filename"],
        "size": info["size"],
        "conversations": info["conversations"]
    }


@router.delete("/{image_id}", response_model=StatusResponse, summary="Delete an image")
async def delete_image(image_id: str):
    """
    Delete an uploaded image and its conversation history.

    - **image_id**: ID of the image to delete
    """
    success = vision_service.clear_image(image_id)

    if not success:
        raise HTTPException(status_code=404, detail="Image not found")

    return StatusResponse(
        status="Image deleted",
        success=True
    )


@router.get("/status/model", summary="Get vision model status")
async def get_model_status():
    """Check if the vision model is loaded."""
    return {
        "loaded": vision_service.is_loaded,
        "model_id": vision_service._handler.model_id if vision_service.is_loaded else None
    }


@router.post("/unload", response_model=StatusResponse, summary="Unload vision model")
async def unload_model():
    """Unload the vision model to free memory."""
    vision_service.unload_model()
    return StatusResponse(
        status="Vision model unloaded",
        success=True
    )
