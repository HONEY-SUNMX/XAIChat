#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision Service
Handles image understanding with Qwen2-VL model.

Author: Generated with love by Harei-chan
Performance optimized by Harei-chan (￣▽￣)ノ
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
import shutil
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict

from fastapi import UploadFile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class VisionService:
    """
    Vision service for image understanding with Qwen2-VL.

    Features:
    - Lazy model loading
    - Image upload and management
    - Multi-turn conversation per image
    - Streaming response generation
    """

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    def __init__(self):
        self._handler = None
        self._is_loading = False
        self._images: Dict[str, dict] = {}  # image_id -> {path, conversations}

    @property
    def is_loaded(self) -> bool:
        """Check if the vision model is loaded."""
        return self._handler is not None and self._handler.is_loaded

    def _load_model(self) -> None:
        """Load the Qwen2-VL vision model."""
        if self._handler is not None or self._is_loading:
            return

        self._is_loading = True
        logger.info("=" * 60)
        logger.info("👁️ [LOAD] Starting to load vision model...")

        try:
            from core.qwen_vision import QwenVisionHandler

            logger.info(f"   Model ID: {settings.vision_model_id}")
            logger.info(f"   Max tokens: {settings.vision_max_tokens}")
            logger.info(f"   Min image size: {settings.vision_min_image_size}px")
            logger.info(f"   Max image size: {settings.vision_max_image_size}px")
            logger.info(f"   Device: cpu")

            load_start = time.time()

            self._handler = QwenVisionHandler(
                model_id=settings.vision_model_id,
                device="cpu",
                max_new_tokens=settings.vision_max_tokens,
                min_image_size=settings.vision_min_image_size,
                max_image_size=settings.vision_max_image_size,
            )
            self._handler.load_model()

            load_time = time.time() - load_start
            logger.info(f"✅ Vision model loaded successfully! (took {load_time:.2f}s)")
            logger.info("=" * 60)

        except ImportError as e:
            self._is_loading = False
            logger.error(f"❌ Vision dependencies not installed: {e}")
            logger.error("=" * 60)
            raise RuntimeError(
                f"Vision dependencies not installed: {e}. "
                "Please run: pip install transformers qwen-vl-utils"
            )
        except Exception as e:
            self._is_loading = False
            logger.error(f"❌ Failed to load vision model: {e}")
            logger.error("=" * 60)
            raise RuntimeError(f"Failed to load vision model: {e}")

        self._is_loading = False

    def _get_handler(self):
        """Get the vision handler, loading if necessary."""
        if self._handler is None:
            self._load_model()
        return self._handler

    async def upload_image(self, file: UploadFile) -> dict:
        """
        Upload and store an image for processing.

        Args:
            file: Uploaded file from FastAPI

        Returns:
            Dictionary with image_id, filename, and dimensions
        """
        start_time = time.time()
        filename = file.filename or "image"
        ext = Path(filename).suffix.lower()

        logger.info("=" * 60)
        logger.info("📤 [UPLOAD] New image upload request")
        logger.info(f"   Filename: {filename}")

        # Validate file extension
        if ext not in self.SUPPORTED_FORMATS:
            logger.error(f"❌ Unsupported format: {ext}")
            logger.error("=" * 60)
            raise ValueError(
                f"Unsupported format: {ext}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Validate file size
        content = await file.read()
        file_size_kb = len(content) / 1024
        logger.info(f"   File size: {file_size_kb:.1f} KB")

        if len(content) > settings.max_upload_size:
            logger.error(f"❌ File too large: {file_size_kb:.1f} KB > {settings.max_upload_size / 1024:.1f} KB")
            logger.error("=" * 60)
            raise ValueError(
                f"File too large. Max size: {settings.max_upload_size / 1024 / 1024:.1f}MB"
            )

        # Generate unique ID and save file
        image_id = str(uuid.uuid4())
        save_path = Path(settings.upload_dir) / f"{image_id}{ext}"

        # Ensure upload directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the file
        with open(save_path, "wb") as f:
            f.write(content)

        # Get image dimensions
        try:
            from PIL import Image
            with Image.open(save_path) as img:
                width, height = img.size
        except Exception:
            width, height = 0, 0

        # Store image info
        self._images[image_id] = {
            "path": str(save_path),
            "filename": filename,
            "size": [width, height],
            "conversations": []
        }

        # Complete logging
        elapsed = time.time() - start_time
        logger.info("-" * 60)
        logger.info("✅ [COMPLETE] Image uploaded successfully!")
        logger.info(f"   📁 Saved as: {image_id}{ext}")
        logger.info(f"   📐 Dimensions: {width}x{height}")
        logger.info(f"   💾 File size: {file_size_kb:.1f} KB")
        logger.info(f"   ⏱️  Time: {elapsed:.2f}s")
        logger.info("=" * 60)

        return {
            "image_id": image_id,
            "filename": filename,
            "size": [width, height],
            "message": "Image uploaded successfully"
        }

    async def stream_response(
        self,
        image_id: str,
        question: str
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for an image question.

        Yields:
            SSE formatted events with response content
        """
        start_time = time.time()

        # Log request
        logger.info("=" * 60)
        logger.info("❓ [REQUEST] New vision question")
        question_oneline = question.replace('\n', ' ').replace('\r', '').strip()
        logger.info(f"   Question: {question_oneline[:80]}{'...' if len(question_oneline) > 80 else ''}")
        logger.info(f"   Image ID: {image_id[:8]}...")

        # Validate image exists
        if image_id not in self._images:
            logger.error(f"❌ Image not found: {image_id[:8]}...")
            logger.error("=" * 60)
            yield f"data: {json.dumps({'type': 'error', 'content': 'Image not found'})}\n\n"
            return

        image_info = self._images[image_id]
        image_path = image_info["path"]

        try:
            logger.info("-" * 60)
            logger.info("🚀 [INFERENCE] Starting vision inference...")

            # Get handler
            handler_start = time.time()
            handler = self._get_handler()
            logger.info(f"   Handler ready (took {time.time() - handler_start:.2f}s)")

            # Set the image if not already set or different
            if handler.current_image_path != image_path:
                logger.info("   Setting image...")
                if not handler.set_image(image_path):
                    logger.error("❌ Failed to load image")
                    logger.error("=" * 60)
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Failed to load image'})}\n\n"
                    return

            # Generate response (non-streaming for now, as Qwen2-VL doesn't easily stream)
            inference_start = time.time()
            response = handler.ask(question)
            inference_time = time.time() - inference_start
            logger.info(f"   ⚡ Inference time: {inference_time:.2f}s")

            # Send response in chunks for better UX
            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'response', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for streaming effect

            # Store conversation
            image_info["conversations"].append({
                "question": question,
                "answer": response
            })

            # Complete logging
            elapsed = time.time() - start_time
            logger.info("-" * 60)
            logger.info("✅ [COMPLETE] Vision inference finished!")
            logger.info(f"   📝 Response length: {len(response)} chars")
            logger.info(f"   ⏱️  Total time: {elapsed:.2f}s")
            logger.info("=" * 60)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [ERROR] Vision inference failed after {elapsed:.2f}s")
            logger.error(f"   Error: {str(e)}")
            logger.error("=" * 60)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    async def get_response(self, image_id: str, question: str) -> dict:
        """
        Generate non-streaming response for an image question.

        Returns:
            Dictionary with response and image_id
        """
        start_time = time.time()

        # Log request
        logger.info("=" * 60)
        logger.info("❓ [REQUEST] New vision question (non-streaming)")
        question_oneline = question.replace('\n', ' ').replace('\r', '').strip()
        logger.info(f"   Question: {question_oneline[:80]}{'...' if len(question_oneline) > 80 else ''}")
        logger.info(f"   Image ID: {image_id[:8]}...")

        if image_id not in self._images:
            logger.error(f"❌ Image not found: {image_id[:8]}...")
            logger.error("=" * 60)
            raise ValueError("Image not found")

        image_info = self._images[image_id]
        image_path = image_info["path"]

        try:
            logger.info("-" * 60)
            logger.info("🚀 [INFERENCE] Starting vision inference...")

            handler_start = time.time()
            handler = self._get_handler()
            logger.info(f"   Handler ready (took {time.time() - handler_start:.2f}s)")

            # Set the image if not already set or different
            if handler.current_image_path != image_path:
                logger.info("   Setting image...")
                if not handler.set_image(image_path):
                    logger.error("❌ Failed to load image")
                    logger.error("=" * 60)
                    raise RuntimeError("Failed to load image")

            # Generate response
            inference_start = time.time()
            response = handler.ask(question)
            inference_time = time.time() - inference_start
            logger.info(f"   ⚡ Inference time: {inference_time:.2f}s")

            # Store conversation
            image_info["conversations"].append({
                "question": question,
                "answer": response
            })

            # Complete logging
            elapsed = time.time() - start_time
            logger.info("-" * 60)
            logger.info("✅ [COMPLETE] Vision inference finished!")
            logger.info(f"   📝 Response length: {len(response)} chars")
            logger.info(f"   ⏱️  Total time: {elapsed:.2f}s")
            logger.info("=" * 60)

            return {
                "response": response,
                "image_id": image_id
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [ERROR] Vision inference failed after {elapsed:.2f}s")
            logger.error(f"   Error: {str(e)}")
            logger.error("=" * 60)
            raise

    def get_image_info(self, image_id: str) -> Optional[dict]:
        """Get image information by ID."""
        return self._images.get(image_id)

    def clear_image(self, image_id: str) -> bool:
        """
        Clear an image and its conversation history.

        Also deletes the uploaded file.
        """
        if image_id not in self._images:
            logger.warning(f"🗑️ [CLEAR] Image not found: {image_id[:8]}...")
            return False

        logger.info(f"🗑️ [CLEAR] Clearing image: {image_id[:8]}...")

        image_info = self._images[image_id]

        # Delete the file
        try:
            os.remove(image_info["path"])
            logger.info(f"   Deleted file: {image_info['path']}")
        except OSError as e:
            logger.warning(f"   Failed to delete file: {e}")

        # Remove from storage
        del self._images[image_id]

        # Clear handler's current image if it was this one
        if self._handler and self._handler.current_image_path == image_info["path"]:
            self._handler.clear()
            logger.info("   Cleared handler's current image")

        logger.info("✅ Image cleared successfully")
        return True

    def unload_model(self) -> None:
        """Unload the vision model to free memory."""
        if self._handler:
            self._handler.unload()
            self._handler = None


# Global service instance
vision_service = VisionService()
