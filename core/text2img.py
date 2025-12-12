#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text-to-Image Generator using LCM-SD1.5
Optimized for CPU inference on systems without GPU.

Author: Generated with love by Harei-chan (￣▽￣)ノ
"""

import os
import gc
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any

# Try to import config (will set environment variables automatically)
# If running as standalone script, use fallback defaults
try:
    from core.config import settings  # noqa: F401
except ImportError:
    # Standalone script mode: set environment variables with defaults
    os.environ.setdefault("DIFFUSERS_VERBOSITY", "error")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TQDM_DISABLE", "1")

try:
    import torch
    # Explicitly disable CUDA to avoid NVML warning
    import os
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from diffusers import DiffusionPipeline, LCMScheduler
    from diffusers.utils import logging as diffusers_logging
    from PIL import Image
    HAS_DIFFUSERS = True
    # Disable diffusers progress bar
    diffusers_logging.set_verbosity_error()
    diffusers_logging.disable_progress_bar()
except ImportError:
    HAS_DIFFUSERS = False
    torch = None
    Image = None


class Text2ImageGenerator:
    """
    LCM-SD1.5 based text-to-image generator optimized for CPU.

    Features:
    - Lazy loading: Model is loaded only when first generation is requested
    - Memory optimization: Attention slicing reduces peak memory usage
    - Progress callback: Support for displaying generation progress
    - Automatic saving: Images are saved with timestamps

    Recommended settings for CPU:
    - num_inference_steps: 4-8 (LCM is designed for few-step inference)
    - guidance_scale: 1.0-2.0 (LCM works best with low guidance)
    - Image size: 512x512 (larger sizes significantly increase time and memory)
    """

    DEFAULT_MODEL = "SimianLuo/LCM_Dreamshaper_v7"
    DEFAULT_STEPS = 6
    DEFAULT_GUIDANCE = 1.5

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        num_inference_steps: int = DEFAULT_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE,
        cache_dir: str = "./models/diffusion",
        enable_attention_slicing: bool = True,
    ):
        """
        Initialize the text-to-image generator.

        Args:
            model_id: HuggingFace model ID for LCM model
            num_inference_steps: Number of denoising steps (4-8 recommended for LCM)
            guidance_scale: Classifier-free guidance scale (1.0-2.0 for LCM)
            cache_dir: Directory to cache downloaded models
            enable_attention_slicing: Enable attention slicing to reduce memory usage
        """
        if not HAS_DIFFUSERS:
            raise ImportError(
                "Required libraries not installed!\n"
                "Please run: pip install diffusers transformers accelerate pillow torch"
            )

        self.model_id = model_id
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.cache_dir = cache_dir
        self.enable_attention_slicing = enable_attention_slicing

        self._pipeline = None
        self._is_loading = False

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._pipeline is not None

    def _load_pipeline(self) -> None:
        """
        Load the diffusion pipeline.

        This method implements lazy loading - the model is only loaded
        when this method is called, not at initialization.
        """
        if self._pipeline is not None or self._is_loading:
            return

        self._is_loading = True

        try:
            # Disable tqdm progress bar from diffusers/transformers/huggingface_hub
            import logging as _logging
            _logging.getLogger("diffusers").setLevel(_logging.WARNING)
            _logging.getLogger("transformers").setLevel(_logging.WARNING)
            _logging.getLogger("huggingface_hub").setLevel(_logging.WARNING)

            print(f"Loading image generation model: {self.model_id}")
            print("This may take several minutes on first run (downloading ~2GB model)...")

            # Create cache directory if not exists
            os.makedirs(self.cache_dir, exist_ok=True)

            # Load the pipeline
            self._pipeline = DiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float32,  # CPU requires float32
                cache_dir=self.cache_dir,
                safety_checker=None,  # Disable safety checker for faster inference
            )

            # Configure LCM scheduler for fast inference
            self._pipeline.scheduler = LCMScheduler.from_config(
                self._pipeline.scheduler.config
            )

            # Memory optimization for CPU
            if self.enable_attention_slicing:
                self._pipeline.enable_attention_slicing(slice_size="auto")

            # Move to CPU explicitly
            self._pipeline.to("cpu")

            print("Image generation model loaded successfully!")

        except Exception as e:
            self._is_loading = False
            raise RuntimeError(f"Failed to load model: {e}")

        self._is_loading = False

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, Any], None]] = None,
    ) -> "Image.Image":
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the desired image
            negative_prompt: Things to avoid in the generated image
            width: Output image width (should be multiple of 8)
            height: Output image height (should be multiple of 8)
            seed: Random seed for reproducibility (None for random)
            progress_callback: Callback function(step, total, latents) for progress updates

        Returns:
            PIL.Image.Image: Generated image

        Raises:
            RuntimeError: If model loading or generation fails
        """
        # Ensure pipeline is loaded
        self._load_pipeline()

        # Set up random generator for reproducibility
        if seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(seed)
        else:
            # Use current timestamp as seed for variety
            seed = int(time.time() * 1000) % (2**32)
            generator = torch.Generator(device="cpu").manual_seed(seed)

        # Callback wrapper to match diffusers API
        def callback_wrapper(pipe, step, timestep, callback_kwargs):
            if progress_callback:
                progress_callback(step, self.num_inference_steps, callback_kwargs.get("latents"))
            return callback_kwargs

        # Generate image
        result = self._pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt if negative_prompt else None,
            width=width,
            height=height,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
            generator=generator,
            callback_on_step_end=callback_wrapper if progress_callback else None,
        )

        return result.images[0]

    def generate_and_save(
        self,
        prompt: str,
        output_dir: str = "./outputs",
        filename_prefix: str = "img",
        **kwargs
    ) -> str:
        """
        Generate an image and save it to disk.

        Args:
            prompt: Text description of the desired image
            output_dir: Directory to save the generated image
            filename_prefix: Prefix for the generated filename
            **kwargs: Additional arguments passed to generate()

        Returns:
            str: Path to the saved image file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate the image
        image = self.generate(prompt, **kwargs)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        # Save the image
        image.save(output_path, "PNG")

        return output_path

    def unload(self) -> None:
        """
        Unload the model from memory.

        Call this method to free up memory when image generation
        is no longer needed.
        """
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None

            # Force garbage collection
            gc.collect()

            if torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()


# Convenience function for quick generation
def generate_image(
    prompt: str,
    output_dir: str = "./outputs",
    **kwargs
) -> str:
    """
    Quick function to generate and save an image.

    Args:
        prompt: Text description of the desired image
        output_dir: Directory to save the image
        **kwargs: Additional arguments for generation

    Returns:
        str: Path to the saved image
    """
    generator = Text2ImageGenerator()
    return generator.generate_and_save(prompt, output_dir, **kwargs)


if __name__ == "__main__":
    # Simple test
    print("Text2Image Generator Test")
    print("=" * 40)

    gen = Text2ImageGenerator()

    test_prompt = "a beautiful sunset over mountains, digital art, high quality"
    print(f"Generating image for: {test_prompt}")

    def progress_cb(step, total, latents):
        progress = (step + 1) / total * 100
        print(f"\rProgress: {progress:.0f}%", end="", flush=True)

    start = time.time()
    path = gen.generate_and_save(test_prompt, progress_callback=progress_cb)
    elapsed = time.time() - start

    print(f"\nImage saved to: {path}")
    print(f"Time elapsed: {elapsed:.1f}s")
