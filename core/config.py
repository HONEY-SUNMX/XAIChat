#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Configuration
Centralized configuration management using Pydantic Settings.

Author: Generated with love by Harei-chan
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application info
    app_name: str = "Qwen Chat API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Model paths
    # Chat model: supports both local path and HuggingFace model ID
    # If local file exists, use it directly; otherwise download from HuggingFace
    chat_model_id: str = "unsloth/Qwen3-1.7B-GGUF"  # HuggingFace repo ID
    chat_model_filename: str = "Qwen3-1.7B-Q4_K_M.gguf"  # GGUF filename (case-sensitive on Linux)
    chat_model_dir: str = "./models"  # Local model directory

    # Vision and image models (auto-download from HuggingFace)
    vision_model_id: str = "Qwen/Qwen2-VL-2B-Instruct"
    image_model_id: str = "SimianLuo/LCM_Dreamshaper_v7"

    # Model settings
    chat_context_length: int = 8192
    chat_max_tokens: int = 8192  # Same as CLI version for consistency
    chat_n_threads: int = 0  # 0 = auto (use os.cpu_count())
    chat_n_gpu_layers: int = 0  # 0 = CPU only
    vision_max_tokens: int = 512
    vision_min_image_size: int = 30  # Minimum image dimension for OCR (upscale smaller images)
    vision_max_image_size: int = 1280  # Maximum image dimension (downscale larger images)
    image_inference_steps: int = 6
    image_guidance_scale: float = 1.5
    default_image_size: int = 512

    # Model cache directory
    model_cache_dir: str = "./models/diffusion"

    # Streaming optimization
    stream_batch_size: int = 10  # Send response every N tokens
    thinking_stream_batch_size: int = 5  # Send thinking content every N tokens
    log_progress_interval: int = 50  # Log progress every N tokens

    # File storage
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Timeouts (in seconds)
    chat_timeout: int = 300
    vision_timeout: int = 300
    image_timeout: int = 300

    # Third-party library logging control
    diffusers_verbosity: str = "error"
    transformers_verbosity: str = "error"
    disable_tqdm: bool = True

    # HuggingFace mirror (default to China mirror for faster downloads)
    # Set to empty string "" to use official HuggingFace (https://huggingface.co)
    hf_endpoint: str = "https://hf-mirror.com"

    # Uvicorn settings
    uvicorn_access_log: bool = False  # Disable HTTP access log (GET/POST requests)

    class Config:
        env_prefix = "QWEN_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def configure_environment(self) -> None:
        """Configure environment variables for third-party libraries.

        Must be called before importing diffusers/transformers.
        """
        os.environ["DIFFUSERS_VERBOSITY"] = self.diffusers_verbosity
        os.environ["TRANSFORMERS_VERBOSITY"] = self.transformers_verbosity
        if self.disable_tqdm:
            os.environ["TQDM_DISABLE"] = "1"
        # Set HuggingFace mirror endpoint (useful for China users)
        if self.hf_endpoint:
            os.environ["HF_ENDPOINT"] = self.hf_endpoint
        # Explicitly disable CUDA to avoid NVML initialization warnings
        # This is important for CPU-only inference
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    def get_chat_model_path(self) -> str:
        """Get the chat model path, downloading from HuggingFace if not present locally.

        Returns:
            str: Path to the GGUF model file

        Raises:
            RuntimeError: If model cannot be found or downloaded
        """
        import logging
        logger = logging.getLogger(__name__)

        # Construct local path
        local_path = Path(self.chat_model_dir) / self.chat_model_filename

        # Check if model exists locally
        if local_path.exists():
            logger.info(f"📦 Using local chat model: {local_path}")
            return str(local_path)

        # Model not found locally, download from HuggingFace
        logger.info(f"📥 Chat model not found locally, downloading from HuggingFace...")
        logger.info(f"   Model ID: {self.chat_model_id}")
        logger.info(f"   Filename: {self.chat_model_filename}")

        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            raise RuntimeError(
                "huggingface_hub not installed! "
                "Please run: pip install huggingface-hub"
            )

        # Ensure model directory exists
        Path(self.chat_model_dir).mkdir(parents=True, exist_ok=True)

        try:
            downloaded_path = hf_hub_download(
                repo_id=self.chat_model_id,
                filename=self.chat_model_filename,
                local_dir=self.chat_model_dir,
            )
            logger.info(f"✅ Chat model downloaded: {downloaded_path}")
            return downloaded_path
        except Exception as e:
            raise RuntimeError(f"Failed to download chat model: {e}")


# Global settings instance
settings = Settings()
# Configure environment variables immediately on import
settings.configure_environment()
