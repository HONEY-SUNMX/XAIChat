#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Generation API Router
Endpoints for text-to-image generation with LCM-Dreamshaper.

Author: Generated with love by Harei-chan
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from server.models.schemas import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    StatusResponse,
)
from server.services.image_service import image_service
from core.config import settings


router = APIRouter()


@router.post("/generate", summary="Generate an image from text")
async def generate_image(request: ImageGenerateRequest):
    """
    Generate an image from a text prompt.

    - **prompt**: Text description of the desired image
    - **negative_prompt**: Things to avoid in the image
    - **width**: Image width (256-1024, default 512)
    - **height**: Image height (256-1024, default 512)
    - **seed**: Random seed for reproducibility
    - **num_steps**: Number of inference steps (1-50, default 6)

    Returns SSE stream with progress updates.

    SSE Stream Events:
    - `progress`: Generation progress (step, total)
    - `done`: Generation complete (image_url, filename, seed)
    - `error`: Error occurred
    """
    try:
        return StreamingResponse(
            image_service.generate_with_progress(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                seed=request.seed,
                num_steps=request.num_steps,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/generate/sync", response_model=ImageGenerateResponse, summary="Generate image (non-streaming)")
async def generate_image_sync(request: ImageGenerateRequest):
    """
    Generate an image without streaming (waits for completion).

    Same parameters as /generate but returns JSON response.
    """
    try:
        result = await image_service.generate(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            seed=request.seed,
            num_steps=request.num_steps,
        )
        return ImageGenerateResponse(**result)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/download/{filename}", summary="Download a generated image")
async def download_image(filename: str):
    """
    Download a generated image by filename.

    - **filename**: The filename of the generated image
    """
    file_path = Path(settings.output_dir) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Security check: ensure the path is within output_dir
    try:
        file_path.resolve().relative_to(Path(settings.output_dir).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="image/png"
    )


@router.get("/list", summary="List generated images")
async def list_images(limit: int = 20, offset: int = 0):
    """
    List recently generated images.

    - **limit**: Maximum number of images to return (default 20)
    - **offset**: Number of images to skip (for pagination)
    """
    output_dir = Path(settings.output_dir)

    if not output_dir.exists():
        return {"images": [], "total": 0}

    # Get all PNG files sorted by modification time (newest first)
    files = sorted(
        output_dir.glob("*.png"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    total = len(files)
    files = files[offset:offset + limit]

    images = []
    for f in files:
        images.append({
            "filename": f.name,
            "url": f"/outputs/{f.name}",
            "created_at": f.stat().st_mtime
        })

    return {
        "images": images,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.delete("/{filename}", response_model=StatusResponse, summary="Delete a generated image")
async def delete_image(filename: str):
    """
    Delete a generated image.

    - **filename**: The filename of the image to delete
    """
    file_path = Path(settings.output_dir) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Security check
    try:
        file_path.resolve().relative_to(Path(settings.output_dir).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        os.remove(file_path)
        return StatusResponse(status="Image deleted", success=True)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.get("/status/model", summary="Get image generation model status")
async def get_model_status():
    """Check if the image generation model is loaded."""
    return {
        "loaded": image_service.is_loaded,
        "model_id": settings.image_model_id
    }


@router.post("/unload", response_model=StatusResponse, summary="Unload image model")
async def unload_model():
    """Unload the image generation model to free memory."""
    image_service.unload_model()
    return StatusResponse(
        status="Image generation model unloaded",
        success=True
    )
