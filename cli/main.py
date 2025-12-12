#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen Chat CLI
Interactive command-line interface for Qwen AI models.

Usage:
    # Use default model from config (auto-download if not exists)
    python -m cli.main

    # Use a specific local GGUF model
    python -m cli.main --model ./models/custom-model.gguf

    # Start with an image for visual Q&A
    python -m cli.main --input-image ./photo.jpg

Author: Generated with love by Harei-chan (￣▽￣)ノ
"""

import os
import argparse
import sys
from pathlib import Path

# Explicitly disable CUDA before any imports to avoid NVML warnings
# This must be set at the very beginning
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from core module (single source of truth)
from core.config import settings

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        CYAN = YELLOW = GREEN = RED = MAGENTA = BLUE = WHITE = ""
    class Style:
        RESET_ALL = DIM = BRIGHT = ""


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Qwen3 Interactive Chat with Thinking Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Use default model (auto-download if not exists)
  python -m cli.main

  # Use a specific local GGUF model
  python -m cli.main --model ./models/custom-model.gguf

  # Adjust context size and threads
  python -m cli.main --ctx 4096 --threads 8

  # Start with an image for visual Q&A
  python -m cli.main --input-image ./photo.jpg

Default model: {settings.chat_model_filename}
Model directory: {settings.chat_model_dir}
        """
    )

    # Model options
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Path to the GGUF model file (default: use config settings)"
    )

    # Performance options
    parser.add_argument(
        "--ctx", "-c",
        type=int,
        default=settings.chat_context_length,
        help=f"Context window size (default: {settings.chat_context_length})"
    )
    parser.add_argument(
        "--threads", "-t",
        type=int,
        default=settings.chat_n_threads if settings.chat_n_threads > 0 else None,
        help="Number of CPU threads (default: auto)"
    )
    parser.add_argument(
        "--gpu-layers", "-g",
        type=int,
        default=settings.chat_n_gpu_layers,
        help=f"Number of layers to offload to GPU (default: {settings.chat_n_gpu_layers})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    # Image generation options
    image_group = parser.add_argument_group('Image Generation Options')

    image_group.add_argument(
        "--image-model",
        type=str,
        default=settings.image_model_id,
        help=f"Text-to-image model ID (default: {settings.image_model_id})"
    )
    image_group.add_argument(
        "--image-steps",
        type=int,
        default=settings.image_inference_steps,
        help=f"Number of inference steps for image generation (default: {settings.image_inference_steps})"
    )
    image_group.add_argument(
        "--image-size",
        type=int,
        default=settings.default_image_size,
        choices=[256, 384, 512, 640, 768],
        help=f"Generated image size in pixels (default: {settings.default_image_size})"
    )
    image_group.add_argument(
        "--no-image",
        action="store_true",
        help="Disable text-to-image feature"
    )

    # Vision (image understanding) options
    vision_group = parser.add_argument_group('Vision Options (Image Understanding)')

    vision_group.add_argument(
        "--input-image", "-i",
        type=str,
        default=None,
        help="Load an image at startup for visual Q&A"
    )
    vision_group.add_argument(
        "--vision-model",
        type=str,
        default=settings.vision_model_id,
        help=f"Vision model ID (default: {settings.vision_model_id})"
    )
    vision_group.add_argument(
        "--no-vision",
        action="store_true",
        help="Disable image understanding feature"
    )

    args = parser.parse_args()

    # Determine model path
    if args.model:
        # User specified a custom model path
        model_path = args.model
        if not Path(model_path).exists():
            print(f"{Fore.RED}Error: Model file not found: {model_path}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        # Use default model from config (auto-download if not exists)
        try:
            print(f"{Fore.CYAN}Loading model from config...{Style.RESET_ALL}")
            model_path = settings.get_chat_model_path()
            print(f"{Fore.GREEN}Model ready: {model_path}{Style.RESET_ALL}")
        except RuntimeError as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            sys.exit(1)

    # Import QwenChat from core module
    from core.qwen_chat import QwenChat

    # Create chat instance
    chat = QwenChat(
        model_path=model_path,
        n_ctx=args.ctx,
        n_threads=args.threads,
        n_gpu_layers=args.gpu_layers,
        verbose=args.verbose,
    )

    # Configure image generation
    chat.image_enabled = not args.no_image
    chat.image_config = {
        "model_id": args.image_model,
        "num_inference_steps": args.image_steps,
        "image_size": args.image_size,
    }

    # Configure vision (image understanding)
    chat.vision_enabled = not args.no_vision
    chat.vision_config = {
        "model_id": args.vision_model,
    }

    # Load image at startup if specified
    if args.input_image:
        chat.startup_image = args.input_image
    else:
        chat.startup_image = None

    # Start the interactive chat loop
    chat.run()


if __name__ == "__main__":
    main()
