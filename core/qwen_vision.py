#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen2-VL Vision Handler
A vision processing module based on transformers, optimized for CPU inference.

Author: Generated with love by Harei-chan (￣▽￣)ノ
"""

import gc
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Generator, List, Dict, Any, TYPE_CHECKING

# Setup logger for non-interactive output
logger = logging.getLogger(__name__)

# Check if running in interactive CLI mode (not as a web service)
# When running as uvicorn/FastAPI, __name__ will be imported as a module
# When running directly (python qwen_vision.py), __name__ will be "__main__"
def _check_interactive() -> bool:
    """Check if running in interactive CLI mode."""
    # Check if stdout is a terminal
    if not sys.stdout.isatty():
        return False
    # Check if running under uvicorn (web server mode)
    if "uvicorn" in sys.modules:
        return False
    return True

_is_interactive = _check_interactive()

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    from qwen_vl_utils import process_vision_info
    HAS_QWEN_VL_UTILS = True
except ImportError:
    HAS_QWEN_VL_UTILS = False

try:
    from colorama import Fore, Style
except ImportError:
    class Fore:
        CYAN = YELLOW = GREEN = RED = MAGENTA = BLUE = WHITE = ""
    class Style:
        RESET_ALL = DIM = BRIGHT = ""


class QwenVisionHandler:
    """
    Qwen2-VL Vision Handler for image understanding.

    Features:
    - Lazy loading: Model is loaded only when first used
    - CPU optimized: Uses float32 and memory-efficient settings
    - Multi-turn conversation: Maintains conversation context for follow-up questions
    - Image preprocessing: Automatically resizes large images for faster inference

    Usage:
        handler = QwenVisionHandler()
        handler.load_model()
        handler.set_image("./photo.jpg")
        response = handler.ask("What's in this image?")
    """

    DEFAULT_MODEL = "Qwen/Qwen2-VL-2B-Instruct"
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        device: str = "cpu",
        max_image_size: int = 1280,
        min_image_size: int = 224,
        max_new_tokens: int = 512,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the vision handler.

        Args:
            model_id: HuggingFace model ID or local path
            device: Device to run inference on ("cpu" or "cuda")
            max_image_size: Maximum image dimension (larger images will be resized)
            min_image_size: Minimum image dimension (smaller images will be upscaled)
            max_new_tokens: Maximum tokens to generate in response
            cache_dir: Directory to cache downloaded models
        """
        self._check_dependencies()

        self.model_id = model_id
        self.device = device
        self.max_image_size = max_image_size
        self.min_image_size = min_image_size
        self.max_new_tokens = max_new_tokens
        self.cache_dir = cache_dir

        # Model components (lazy loaded)
        self._model = None
        self._processor = None
        self._is_loading = False

        # Current state
        self._current_image: Optional[Image.Image] = None
        self._current_image_path: Optional[str] = None
        self._conversation: List[Dict[str, Any]] = []

    def _check_dependencies(self) -> None:
        """Check if all required dependencies are installed."""
        missing = []

        if not HAS_TORCH:
            missing.append("torch")
        if not HAS_PIL:
            missing.append("pillow")
        if not HAS_TRANSFORMERS:
            missing.append("transformers>=4.37.0")
        if not HAS_QWEN_VL_UTILS:
            missing.append("qwen-vl-utils")

        if missing:
            raise ImportError(
                f"Missing required dependencies: {', '.join(missing)}\n"
                f"Please install: pip install {' '.join(missing)}"
            )

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._model is not None and self._processor is not None

    @property
    def has_image(self) -> bool:
        """Check if an image is currently loaded."""
        return self._current_image is not None

    @property
    def current_image_path(self) -> Optional[str]:
        """Get the path of the currently loaded image."""
        return self._current_image_path

    def load_model(self) -> None:
        """
        Load the Qwen2-VL model and processor.

        This method implements lazy loading - the model is only loaded
        when this method is called, not at initialization.
        """
        if self._model is not None or self._is_loading:
            return

        self._is_loading = True

        try:
            logger.info(f"Loading vision model: {self.model_id}")
            if _is_interactive:
                print(f"{Fore.CYAN}Loading vision model: {self.model_id}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}This may take 2-3 minutes on first run...{Style.RESET_ALL}")

            start_time = time.time()

            # Set up CPU optimizations
            if HAS_TORCH:
                torch.set_grad_enabled(False)
                torch.set_num_threads(os.cpu_count() or 4)
                # Explicitly disable CUDA to avoid NVML warning
                os.environ["CUDA_VISIBLE_DEVICES"] = ""

            # Load model with CPU-optimized settings
            model_kwargs = {
                "torch_dtype": torch.float32,  # CPU requires float32
                "device_map": self.device,
                "low_cpu_mem_usage": True,
            }

            if self.cache_dir:
                model_kwargs["cache_dir"] = self.cache_dir

            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_id,
                **model_kwargs
            )

            # Load processor
            processor_kwargs = {}
            if self.cache_dir:
                processor_kwargs["cache_dir"] = self.cache_dir

            self._processor = AutoProcessor.from_pretrained(
                self.model_id,
                **processor_kwargs
            )

            elapsed = time.time() - start_time
            logger.info(f"Vision model loaded successfully! ({elapsed:.1f}s)")
            if _is_interactive:
                print(f"{Fore.GREEN}Vision model loaded successfully! ({elapsed:.1f}s){Style.RESET_ALL}")

        except Exception as e:
            self._is_loading = False
            raise RuntimeError(f"Failed to load vision model: {e}")

        self._is_loading = False

    def _preprocess_image(self, image_path: str) -> Image.Image:
        """
        Load and preprocess an image.

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed PIL Image
        """
        # Validate file exists
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Validate file format
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported image format: {suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Load image
        image = Image.open(image_path).convert("RGB")

        # Upscale if too small (improves recognition accuracy)
        # For text recognition, ensure MINIMUM dimension is at least min_image_size
        # This is critical for images with extreme aspect ratios (e.g., text banners)
        min_dim = min(image.size)
        if min_dim < self.min_image_size:
            scale = self.min_image_size / min_dim
            new_width = int(image.size[0] * scale)
            new_height = int(image.size[1] * scale)
            image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            logger.info(f"Image upscaled to {image.size} for better recognition (min dimension was {min_dim}px)")
            if _is_interactive:
                print(f"{Fore.YELLOW}Image upscaled to {image.size} for better recognition{Style.RESET_ALL}")

        # Resize if too large (improves inference speed)
        elif max(image.size) > self.max_image_size:
            image.thumbnail(
                (self.max_image_size, self.max_image_size),
                Image.Resampling.LANCZOS
            )
            logger.info(f"Image resized to {image.size} for faster inference")
            if _is_interactive:
                print(f"{Fore.YELLOW}Image resized to {image.size} for faster inference{Style.RESET_ALL}")

        return image

    def set_image(self, image_path: str) -> bool:
        """
        Set the current image for conversation.

        Args:
            image_path: Path to the image file

        Returns:
            True if image was loaded successfully
        """
        try:
            # Ensure model is loaded
            if not self.is_loaded:
                self.load_model()

            # Preprocess and store image
            self._current_image = self._preprocess_image(image_path)
            self._current_image_path = str(Path(image_path).resolve())

            # Clear previous conversation when loading new image
            self._conversation = []

            return True

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            if _is_interactive:
                print(f"{Fore.RED}Failed to load image: {e}{Style.RESET_ALL}")
            return False

    def ask(self, question: str, stream: bool = False) -> str:
        """
        Ask a question about the current image.

        Args:
            question: The question to ask about the image
            stream: Whether to stream the response (not yet implemented)

        Returns:
            The model's response as a string
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not self.has_image:
            raise RuntimeError("No image loaded. Call set_image() first.")

        # Build messages with image and question
        messages = self._build_messages(question)

        try:
            # Prepare inputs
            text = self._processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            # Process vision info if available
            if HAS_QWEN_VL_UTILS:
                image_inputs, video_inputs = process_vision_info(messages)
            else:
                image_inputs = [self._current_image]
                video_inputs = None

            # Create model inputs
            inputs = self._processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )

            # Move to device
            inputs = inputs.to(self.device)

            # Generate response
            with torch.inference_mode():
                output_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.8,
                )

            # Decode response (only the generated part)
            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(inputs.input_ids, output_ids)
            ]

            response = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )[0]

            # Store in conversation history
            self._conversation.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": question}
                ]
            })
            self._conversation.append({
                "role": "assistant",
                "content": response
            })

            return response.strip()

        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {e}")

    def _build_messages(self, question: str) -> List[Dict[str, Any]]:
        """
        Build the message list for the model.

        Args:
            question: The current question

        Returns:
            List of message dictionaries
        """
        messages = []

        # First message includes the image
        if not self._conversation:
            # First question about this image
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": self._current_image_path,
                    },
                    {
                        "type": "text",
                        "text": question
                    }
                ]
            })
        else:
            # Follow-up questions - include conversation history
            # First message with image
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": self._current_image_path,
                    },
                    {
                        "type": "text",
                        "text": self._conversation[0]["content"][0]["text"]
                        if isinstance(self._conversation[0]["content"], list)
                        else self._conversation[0]["content"]
                    }
                ]
            })

            # Add rest of conversation history
            for msg in self._conversation[1:]:
                if msg["role"] == "assistant":
                    messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": msg["content"][0]["text"]
                             if isinstance(msg["content"], list) else msg["content"]}
                        ]
                    })

            # Add current question
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": question}
                ]
            })

        return messages

    def clear(self) -> None:
        """Clear the current image and conversation history."""
        self._current_image = None
        self._current_image_path = None
        self._conversation = []

        # Force garbage collection
        gc.collect()

    def unload(self) -> None:
        """
        Unload the model from memory.

        Call this method to free up memory when vision processing
        is no longer needed.
        """
        if self._model is not None:
            del self._model
            self._model = None

        if self._processor is not None:
            del self._processor
            self._processor = None

        self.clear()

        # Force garbage collection
        gc.collect()

        if HAS_TORCH and torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Vision model unloaded")
        if _is_interactive:
            print(f"{Fore.YELLOW}Vision model unloaded.{Style.RESET_ALL}")

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the current conversation history.

        Returns:
            List of conversation messages
        """
        return self._conversation.copy()


# =============================================================================
# Convenience Functions
# =============================================================================

def describe_image(image_path: str, model_id: str = QwenVisionHandler.DEFAULT_MODEL) -> str:
    """
    Quick function to describe an image.

    Args:
        image_path: Path to the image file
        model_id: HuggingFace model ID

    Returns:
        Description of the image
    """
    handler = QwenVisionHandler(model_id=model_id)
    handler.load_model()
    handler.set_image(image_path)
    return handler.ask("Please describe this image in detail.")


def ask_about_image(
    image_path: str,
    question: str,
    model_id: str = QwenVisionHandler.DEFAULT_MODEL
) -> str:
    """
    Quick function to ask a question about an image.

    Args:
        image_path: Path to the image file
        question: Question to ask about the image
        model_id: HuggingFace model ID

    Returns:
        Answer to the question
    """
    handler = QwenVisionHandler(model_id=model_id)
    handler.load_model()
    handler.set_image(image_path)
    return handler.ask(question)


# =============================================================================
# Main Entry Point (for testing)
# =============================================================================

if __name__ == "__main__":
    print("Qwen2-VL Vision Handler Test")
    print("=" * 40)

    if len(sys.argv) < 2:
        print("Usage: python qwen_vision.py <image_path> [question]")
        print("Example: python qwen_vision.py ./photo.jpg 'What is in this image?'")
        sys.exit(1)

    image_path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else "Please describe this image in detail."

    print(f"Image: {image_path}")
    print(f"Question: {question}")
    print()

    try:
        handler = QwenVisionHandler()
        handler.load_model()

        if handler.set_image(image_path):
            print(f"\n{Fore.CYAN}Generating response...{Style.RESET_ALL}")
            start_time = time.time()

            response = handler.ask(question)

            elapsed = time.time() - start_time
            print(f"\n{Fore.GREEN}Response ({elapsed:.1f}s):{Style.RESET_ALL}")
            print(response)

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
