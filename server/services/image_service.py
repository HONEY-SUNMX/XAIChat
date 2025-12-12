#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Generation Service
Handles text-to-image generation with LCM-Dreamshaper.

Author: Generated with love by Harei-chan
Performance optimized by Harei-chan (￣▽￣)ノ
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ImageService:
    """
    Image generation service using LCM-Dreamshaper.

    Features:
    - Lazy model loading
    - Progress streaming during generation
    - Automatic file naming and storage
    """

    def __init__(self):
        self._generator = None
        self._is_loading = False

    @property
    def is_loaded(self) -> bool:
        """Check if the image generation model is loaded."""
        return self._generator is not None and self._generator.is_loaded

    def _load_model(self) -> None:
        """Load the image generation model."""
        if self._generator is not None or self._is_loading:
            return

        self._is_loading = True
        logger.info("=" * 50)
        logger.info("Starting to load image generation model...")

        try:
            from core.text2img import Text2ImageGenerator

            logger.info(f"Model ID: {settings.image_model_id}")
            logger.info(f"Inference steps: {settings.image_inference_steps}")
            logger.info(f"Guidance scale: {settings.image_guidance_scale}")
            logger.info(f"Cache directory: {settings.model_cache_dir}")
            logger.info(f"Output directory: {settings.output_dir}")

            load_start = time.time()

            self._generator = Text2ImageGenerator(
                model_id=settings.image_model_id,
                num_inference_steps=settings.image_inference_steps,
                guidance_scale=settings.image_guidance_scale,
                cache_dir=settings.model_cache_dir,
            )

            # Trigger model loading
            self._generator._load_pipeline()

            load_time = time.time() - load_start
            logger.info(f"✅ Image model loaded successfully! (took {load_time:.2f}s)")
            logger.info("=" * 50)

        except ImportError as e:
            self._is_loading = False
            logger.error(f"❌ Image generation dependencies not installed: {e}")
            raise RuntimeError(
                f"Image generation dependencies not installed: {e}. "
                "Please run: pip install diffusers transformers accelerate"
            )
        except Exception as e:
            self._is_loading = False
            logger.error(f"❌ Failed to load image model: {e}")
            raise RuntimeError(f"Failed to load image model: {e}")

        self._is_loading = False

    def _get_generator(self):
        """Get the generator instance, loading if necessary."""
        if self._generator is None:
            self._load_model()
        return self._generator

    async def generate_with_progress(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        seed: Optional[int] = None,
        num_steps: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate image with streaming progress updates.

        Yields:
            SSE formatted events with progress and result
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info(f"🎨 [REQUEST] New image generation request")
        # Replace newlines with spaces for cleaner log output
        prompt_oneline = prompt.replace('\n', ' ').replace('\r', '').strip()
        logger.info(f"   Prompt: {prompt_oneline[:80]}{'...' if len(prompt_oneline) > 80 else ''}")
        if negative_prompt:
            negative_oneline = negative_prompt.replace('\n', ' ').replace('\r', '').strip()
            logger.info(f"   Negative: {negative_oneline[:50]}{'...' if len(negative_oneline) > 50 else ''}")
        logger.info(f"   Size: {width}x{height}")

        try:
            # Get generator instance
            logger.info("   Loading generator...")
            gen_start = time.time()
            generator = self._get_generator()
            logger.info(f"   Generator ready (took {time.time() - gen_start:.2f}s)")

            # Use provided steps or default
            steps = num_steps or settings.image_inference_steps

            # Determine seed
            if seed is None:
                seed = int(time.time() * 1000) % (2**32)

            logger.info(f"   Seed: {seed}")
            logger.info(f"   Steps: {steps}")
            logger.info("-" * 60)
            logger.info("🚀 [GENERATION] Starting image generation...")

            # Progress tracking
            current_step = 0
            first_step_time = None

            def progress_callback(step, total, latents):
                nonlocal current_step, first_step_time
                current_step = step
                # Log first step latency
                if first_step_time is None and step > 0:
                    first_step_time = time.time()
                    latency = first_step_time - start_time
                    logger.info(f"   ⚡ First step latency: {latency:.2f}s")
                # Log progress every 2 steps or at completion
                if step % 2 == 0 or step == total:
                    elapsed = time.time() - start_time
                    logger.info(f"   📊 Progress: step {step}/{total}, {elapsed:.1f}s elapsed")

            # Start generation in a thread to not block
            import torch
            from concurrent.futures import ThreadPoolExecutor

            def generate_sync():
                return generator.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    seed=seed,
                    progress_callback=progress_callback,
                )

            # Send initial progress
            yield f"data: {json.dumps({'type': 'progress', 'step': 0, 'total': steps})}\n\n"

            # Run generation in executor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(generate_sync)

                # Poll for progress updates
                last_step = -1
                while not future.done():
                    if current_step != last_step:
                        last_step = current_step
                        yield f"data: {json.dumps({'type': 'progress', 'step': current_step + 1, 'total': steps})}\n\n"
                    await asyncio.sleep(0.1)

                # Get result
                image = future.result()

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gen_{timestamp}_{seed}.png"
            output_path = Path(settings.output_dir) / filename

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            image.save(str(output_path), "PNG")

            # Get file size
            file_size = output_path.stat().st_size / 1024  # KB

            # Final stats
            elapsed = time.time() - start_time
            logger.info("-" * 60)
            logger.info(f"✅ [COMPLETE] Image generation finished!")
            logger.info(f"   📁 Output: {filename}")
            logger.info(f"   📐 Size: {width}x{height}")
            logger.info(f"   💾 File size: {file_size:.1f} KB")
            logger.info(f"   🌱 Seed: {seed}")
            logger.info(f"   ⏱️  Total time: {elapsed:.2f}s")
            logger.info("=" * 60)

            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'image_url': f'/outputs/{filename}', 'filename': filename, 'seed': seed})}\n\n"

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [ERROR] Image generation failed after {elapsed:.2f}s")
            logger.error(f"   Error: {str(e)}")
            logger.error("=" * 60)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        seed: Optional[int] = None,
        num_steps: Optional[int] = None,
    ) -> dict:
        """
        Generate image without streaming (returns final result).

        Returns:
            Dictionary with image_url, filename, and seed
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info(f"🎨 [REQUEST] New image generation request (non-streaming)")
        # Replace newlines with spaces for cleaner log output
        prompt_oneline = prompt.replace('\n', ' ').replace('\r', '').strip()
        logger.info(f"   Prompt: {prompt_oneline[:80]}{'...' if len(prompt_oneline) > 80 else ''}")
        if negative_prompt:
            negative_oneline = negative_prompt.replace('\n', ' ').replace('\r', '').strip()
            logger.info(f"   Negative: {negative_oneline[:50]}{'...' if len(negative_oneline) > 50 else ''}")
        logger.info(f"   Size: {width}x{height}")

        try:
            generator = self._get_generator()

            steps = num_steps or settings.image_inference_steps

            if seed is None:
                seed = int(time.time() * 1000) % (2**32)

            logger.info(f"   Seed: {seed}")
            logger.info(f"   Steps: {steps}")
            logger.info("-" * 60)
            logger.info("🚀 [GENERATION] Starting image generation...")

            # Generate image
            image = generator.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=seed,
            )

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gen_{timestamp}_{seed}.png"
            output_path = Path(settings.output_dir) / filename

            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output_path), "PNG")

            # Get file size
            file_size = output_path.stat().st_size / 1024  # KB

            # Final stats
            elapsed = time.time() - start_time
            logger.info("-" * 60)
            logger.info(f"✅ [COMPLETE] Image generation finished!")
            logger.info(f"   📁 Output: {filename}")
            logger.info(f"   📐 Size: {width}x{height}")
            logger.info(f"   💾 File size: {file_size:.1f} KB")
            logger.info(f"   🌱 Seed: {seed}")
            logger.info(f"   ⏱️  Total time: {elapsed:.2f}s")
            logger.info("=" * 60)

            return {
                "image_url": f"/outputs/{filename}",
                "filename": filename,
                "seed": seed
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [ERROR] Image generation failed after {elapsed:.2f}s")
            logger.error(f"   Error: {str(e)}")
            logger.error("=" * 60)
            raise

    def unload_model(self) -> None:
        """Unload the image generation model to free memory."""
        if self._generator:
            self._generator.unload()
            self._generator = None


# Global service instance
image_service = ImageService()
