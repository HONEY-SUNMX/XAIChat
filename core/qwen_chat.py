#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3 Chat Handler - llama-cpp-python version
A chat handler class with thinking mode and streaming output.

This module provides the QwenChat class for text-based chat functionality.
For CLI interface, use cli/main.py instead.

Author: Generated with love by Harei-chan (￣▽￣)ノ
"""

import logging
import os
import sys
import re
import time
from pathlib import Path
from typing import Optional, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from core.text2img import Text2ImageGenerator
    from core.qwen_vision import QwenVisionHandler

# Setup logger for non-interactive output
logger = logging.getLogger(__name__)

# Check if running in interactive CLI mode (not as a web service)
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
    from llama_cpp import Llama
except ImportError:
    logger.error("llama-cpp-python not installed! Please run: pip install llama-cpp-python")
    sys.exit(1)

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # Fallback: define empty color codes
    class Fore:
        CYAN = YELLOW = GREEN = RED = MAGENTA = BLUE = WHITE = ""
    class Style:
        RESET_ALL = DIM = BRIGHT = ""


# ============================================================================
# Configuration
# ============================================================================

# Sampling parameters for thinking mode
SAMPLING_PARAMS = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "repeat_penalty": 1.1,
    "max_tokens": 8192,
}

# Qwen3 chat template
CHAT_TEMPLATE = """<|im_start|>system
You are Qwen, a helpful assistant. You should think step by step before answering.<|im_end|>
{history}<|im_start|>user
{user_input}<|im_end|>
<|im_start|>assistant
<think>
"""


# ============================================================================
# QwenChat Class
# ============================================================================

class QwenChat:
    """Interactive chat with Qwen3 using llama-cpp-python."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 8192,
        n_threads: Optional[int] = None,
        n_gpu_layers: int = 0,
        verbose: bool = False,
    ):
        """
        Initialize the chat model.

        Args:
            model_path: Path to the GGUF model file
            n_ctx: Context window size
            n_threads: Number of CPU threads (None = auto)
            n_gpu_layers: Number of layers to offload to GPU (0 = CPU only)
            verbose: Whether to show llama.cpp logs
        """
        self.model_path = model_path
        self.messages: list[dict] = []
        self.verbose = verbose

        # Text-to-image generator (lazy loaded)
        self.text2img: Optional["Text2ImageGenerator"] = None
        self.image_enabled: bool = True
        self.image_config: dict = {
            "model_id": "SimianLuo/LCM_Dreamshaper_v7",
            "num_inference_steps": 6,
            "image_size": 512,
        }

        # Vision (image understanding) handler (lazy loaded)
        self.vision_handler: Optional["QwenVisionHandler"] = None
        self.vision_enabled: bool = True
        self.vision_config: dict = {
            "model_id": "Qwen/Qwen2-VL-2B-Instruct",
        }
        self.in_vision_mode: bool = False
        self.startup_image: Optional[str] = None

        logger.info(f"Loading model: {model_path}")
        if _is_interactive:
            print(f"{Fore.CYAN}Loading model: {model_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}This may take a moment...{Style.RESET_ALL}\n")

        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads or os.cpu_count(),
                n_gpu_layers=n_gpu_layers,
                verbose=verbose,
            )
            logger.info("Model loaded successfully!")
            if _is_interactive:
                print(f"{Fore.GREEN}Model loaded successfully!{Style.RESET_ALL}\n")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            if _is_interactive:
                print(f"{Fore.RED}Failed to load model: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def _build_prompt(self, user_input: str) -> str:
        """Build the full prompt with chat history."""
        history = ""
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                history += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                history += f"<|im_start|>assistant\n{content}<|im_end|>\n"

        return CHAT_TEMPLATE.format(history=history, user_input=user_input)

    def _parse_thinking(self, text: str) -> tuple[str, str]:
        """
        Parse thinking content and final answer from model output.

        Returns:
            (thinking_content, final_answer)
        """
        # Pattern to match <think>...</think> or just </think>
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        match = think_pattern.search(text)

        if match:
            thinking = match.group(1).strip()
            # Get content after </think>
            answer = text[match.end():].strip()
            return thinking, answer

        # If no think tags found, check if text starts with thinking content
        # (since we add <think> in the prompt)
        if "</think>" in text:
            parts = text.split("</think>", 1)
            thinking = parts[0].strip()
            answer = parts[1].strip() if len(parts) > 1 else ""
            return thinking, answer

        # No thinking detected
        return "", text.strip()

    def generate_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        Generate response with streaming output.

        Yields:
            Chunks of generated text
        """
        prompt = self._build_prompt(user_input)

        if self.verbose:
            print(f"\n{Fore.MAGENTA}[DEBUG] Prompt:{Style.RESET_ALL}\n{prompt}\n")

        stream = self.llm(
            prompt,
            max_tokens=SAMPLING_PARAMS["max_tokens"],
            temperature=SAMPLING_PARAMS["temperature"],
            top_p=SAMPLING_PARAMS["top_p"],
            top_k=SAMPLING_PARAMS["top_k"],
            repeat_penalty=SAMPLING_PARAMS["repeat_penalty"],
            stop=["<|im_end|>", "<|endoftext|>"],
            stream=True,
        )

        for output in stream:
            chunk = output["choices"][0]["text"]
            yield chunk

    def chat_once(self, user_input: str) -> str:
        """
        Process a single chat turn with streaming output.

        Args:
            user_input: User's input message

        Returns:
            The assistant's full response
        """
        full_response = ""
        thinking_content = ""
        answer_content = ""
        in_thinking = True
        thinking_printed = False

        print(f"\n{Fore.YELLOW}💭 Thinking...{Style.RESET_ALL}")

        buffer = ""
        for chunk in self.generate_stream(user_input):
            buffer += chunk
            full_response += chunk

            # Check if we've exited thinking mode
            if in_thinking and "</think>" in buffer:
                in_thinking = False
                # Split at </think>
                parts = buffer.split("</think>", 1)
                thinking_content = parts[0]
                remaining = parts[1] if len(parts) > 1 else ""

                # Print thinking content (dimmed)
                if thinking_content.strip():
                    print(f"\n{Style.DIM}{Fore.WHITE}{thinking_content.strip()}{Style.RESET_ALL}")

                print(f"\n{Fore.GREEN}🤖 Qwen:{Style.RESET_ALL} ", end="", flush=True)
                thinking_printed = True

                # Print any remaining content after </think>
                if remaining:
                    print(remaining, end="", flush=True)
                    answer_content = remaining

                buffer = ""
            elif not in_thinking:
                # We're in answer mode, print directly
                print(chunk, end="", flush=True)
                answer_content += chunk

        # Handle case where </think> was never found
        if in_thinking:
            thinking_content, answer_content = self._parse_thinking(full_response)
            if thinking_content:
                print(f"\n{Style.DIM}{Fore.WHITE}{thinking_content}{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}🤖 Qwen:{Style.RESET_ALL} {answer_content}")
        else:
            print()  # Final newline

        # Store in history (only the answer, not thinking)
        self.messages.append({"role": "user", "content": user_input})

        # Clean up the response for history
        _, clean_answer = self._parse_thinking(full_response)
        self.messages.append({"role": "assistant", "content": clean_answer})

        return full_response

    def clear_history(self):
        """Clear conversation history."""
        self.messages = []
        print(f"{Fore.YELLOW}Conversation history cleared.{Style.RESET_ALL}")

    def show_help(self):
        """Display help information."""
        help_text = f"""
{Fore.CYAN}╭─────────────────────────────────────────╮
│         Available Commands              │
╰─────────────────────────────────────────╯{Style.RESET_ALL}

{Fore.CYAN}General:{Style.RESET_ALL}
  {Fore.GREEN}/quit{Style.RESET_ALL}, {Fore.GREEN}/exit{Style.RESET_ALL}    - Exit the program
  {Fore.GREEN}/clear{Style.RESET_ALL}           - Clear conversation history
  {Fore.GREEN}/help{Style.RESET_ALL}            - Show this help message
  {Fore.GREEN}/history{Style.RESET_ALL}         - Show conversation history

{Fore.CYAN}Image Generation (Text → Image):{Style.RESET_ALL}
  {Fore.GREEN}/image <prompt>{Style.RESET_ALL}   - Generate image from text

{Fore.CYAN}Vision (Image → Text):{Style.RESET_ALL}
  {Fore.GREEN}/vision <path>{Style.RESET_ALL}    - Load image for visual Q&A
  {Fore.GREEN}/ask <question>{Style.RESET_ALL}   - Ask about the loaded image
  {Fore.GREEN}/clear_vision{Style.RESET_ALL}     - Clear image, back to text mode

{Fore.CYAN}Tips:{Style.RESET_ALL}
  - The model will think step-by-step before answering
  - Thinking process is shown in dimmed text
  - Press Ctrl+C to interrupt generation
  - Image generation takes ~30-60 seconds on CPU
  - Vision Q&A takes ~1-2 minutes on CPU
"""
        print(help_text)

    def show_history(self):
        """Display conversation history."""
        if not self.messages:
            print(f"{Fore.YELLOW}No conversation history.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}=== Conversation History ==={Style.RESET_ALL}\n")
        for i, msg in enumerate(self.messages):
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                print(f"{Fore.BLUE}[You]{Style.RESET_ALL}: {content}\n")
            else:
                # Truncate long responses
                display = content[:200] + "..." if len(content) > 200 else content
                print(f"{Fore.GREEN}[Qwen]{Style.RESET_ALL}: {display}\n")
        print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

    def generate_image(self, prompt: str) -> None:
        """
        Generate an image from text prompt.

        Args:
            prompt: Text description for image generation
        """
        if not self.image_enabled:
            print(f"{Fore.RED}Image generation is disabled.{Style.RESET_ALL}")
            return

        # Lazy import and initialization
        if self.text2img is None:
            print(f"\n{Fore.CYAN}Initializing image generation model...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}First-time setup may take several minutes.{Style.RESET_ALL}\n")

            try:
                from core.text2img import Text2ImageGenerator
                self.text2img = Text2ImageGenerator(
                    model_id=self.image_config["model_id"],
                    num_inference_steps=self.image_config["num_inference_steps"],
                )
            except ImportError as e:
                logger.error(f"Import error: {e}")
                if _is_interactive:
                    print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                    print("Please install: pip install diffusers transformers accelerate pillow torch")
                return
            except Exception as e:
                logger.error(f"Failed to initialize image generator: {e}")
                if _is_interactive:
                    print(f"{Fore.RED}Failed to initialize image generator: {e}{Style.RESET_ALL}")
                return

        print(f"\n{Fore.CYAN}Generating image...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Prompt: {prompt}{Style.RESET_ALL}\n")

        start_time = time.time()

        try:
            output_path = self.text2img.generate_and_save(
                prompt=prompt,
                width=self.image_config["image_size"],
                height=self.image_config["image_size"],
                progress_callback=self._image_progress_callback,
            )

            elapsed = time.time() - start_time
            print()  # New line after progress bar
            print(f"\n{Fore.GREEN}Image saved: {output_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Time: {elapsed:.1f}s{Style.RESET_ALL}")

        except KeyboardInterrupt:
            logger.info("Image generation interrupted by user")
            if _is_interactive:
                print(f"\n{Fore.YELLOW}[Image generation interrupted]{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            if _is_interactive:
                print(f"\n{Fore.RED}Image generation failed: {e}{Style.RESET_ALL}")

    def _image_progress_callback(self, step: int, total: int, latents) -> None:
        """Progress callback for image generation."""
        progress = (step + 1) / total * 100
        bar_len = 30
        filled = int(bar_len * (step + 1) / total)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\r{Fore.CYAN}Progress: [{bar}] {progress:.0f}% (Step {step+1}/{total}){Style.RESET_ALL}",
              end='', flush=True)

    # =========================================================================
    # Vision (Image Understanding) Methods
    # =========================================================================

    def load_vision_image(self, image_path: str) -> None:
        """
        Load an image for visual Q&A.

        Args:
            image_path: Path to the image file
        """
        if not self.vision_enabled:
            print(f"{Fore.RED}Vision feature is disabled.{Style.RESET_ALL}")
            return

        # Lazy load vision handler
        if self.vision_handler is None:
            print(f"\n{Fore.CYAN}Loading vision model...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}First-time setup may take 2-3 minutes.{Style.RESET_ALL}\n")

            try:
                from core.qwen_vision import QwenVisionHandler
                self.vision_handler = QwenVisionHandler(
                    model_id=self.vision_config["model_id"],
                )
                self.vision_handler.load_model()
            except ImportError as e:
                logger.error(f"Import error: {e}")
                if _is_interactive:
                    print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                    print("Please install: pip install transformers qwen-vl-utils accelerate")
                return
            except Exception as e:
                logger.error(f"Failed to initialize vision model: {e}")
                if _is_interactive:
                    print(f"{Fore.RED}Failed to initialize vision model: {e}{Style.RESET_ALL}")
                return

        # Load the image
        print(f"\n{Fore.CYAN}Loading image: {image_path}{Style.RESET_ALL}")

        if self.vision_handler.set_image(image_path):
            self.in_vision_mode = True
            print(f"{Fore.GREEN}✅ Image loaded successfully!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Use /ask <question> to ask about the image.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to load image.{Style.RESET_ALL}")

    def ask_about_image(self, question: str) -> None:
        """
        Ask a question about the currently loaded image.

        Args:
            question: The question to ask
        """
        if not self.vision_enabled:
            print(f"{Fore.RED}Vision feature is disabled.{Style.RESET_ALL}")
            return

        if not self.in_vision_mode or self.vision_handler is None:
            print(f"{Fore.RED}No image loaded. Use /vision <path> first.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}🤔 Analyzing image...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}This may take 1-2 minutes on CPU.{Style.RESET_ALL}\n")

        try:
            start_time = time.time()
            response = self.vision_handler.ask(question)
            elapsed = time.time() - start_time

            print(f"{Fore.GREEN}🤖 Qwen-VL:{Style.RESET_ALL} {response}")
            print(f"\n{Style.DIM}(Response time: {elapsed:.1f}s){Style.RESET_ALL}")

        except KeyboardInterrupt:
            logger.info("Vision query interrupted by user")
            if _is_interactive:
                print(f"\n{Fore.YELLOW}[Interrupted]{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"Vision query error: {e}")
            if _is_interactive:
                print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")

    def clear_vision_mode(self) -> None:
        """Clear the current image and exit vision mode."""
        if self.vision_handler:
            self.vision_handler.clear()

        self.in_vision_mode = False
        print(f"{Fore.GREEN}✅ Vision mode cleared. Back to text chat.{Style.RESET_ALL}")

    def run(self):
        """Main chat loop."""
        self._print_banner()

        # Load startup image if specified
        if self.startup_image:
            self.load_vision_image(self.startup_image)

        while True:
            try:
                user_input = input(f"\n{Fore.BLUE}You:{Style.RESET_ALL} ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower()
                    if cmd in ["/quit", "/exit"]:
                        print(f"\n{Fore.YELLOW}Goodbye! (￣▽￣)ノ{Style.RESET_ALL}")
                        break
                    elif cmd == "/clear":
                        self.clear_history()
                    elif cmd == "/help":
                        self.show_help()
                    elif cmd == "/history":
                        self.show_history()
                    elif cmd.startswith("/image"):
                        # Parse the /image command
                        parts = user_input.split(maxsplit=1)
                        if len(parts) < 2 or not parts[1].strip():
                            print(f"{Fore.RED}Usage: /image <prompt>{Style.RESET_ALL}")
                            print(f"Example: /image a beautiful sunset over mountains")
                        else:
                            image_prompt = parts[1].strip()
                            self.generate_image(image_prompt)
                    elif cmd.startswith("/vision"):
                        # Load image for visual Q&A
                        parts = user_input.split(maxsplit=1)
                        if len(parts) < 2 or not parts[1].strip():
                            print(f"{Fore.RED}Usage: /vision <image_path>{Style.RESET_ALL}")
                            print(f"Example: /vision ./photo.jpg")
                        else:
                            image_path = parts[1].strip()
                            self.load_vision_image(image_path)
                    elif cmd.startswith("/ask"):
                        # Ask about the loaded image
                        parts = user_input.split(maxsplit=1)
                        if len(parts) < 2 or not parts[1].strip():
                            print(f"{Fore.RED}Usage: /ask <question>{Style.RESET_ALL}")
                            print(f"Example: /ask What is in this image?")
                        else:
                            question = parts[1].strip()
                            self.ask_about_image(question)
                    elif cmd == "/clear_vision":
                        self.clear_vision_mode()
                    else:
                        print(f"{Fore.RED}Unknown command: {cmd}{Style.RESET_ALL}")
                        print(f"Type {Fore.GREEN}/help{Style.RESET_ALL} for available commands.")
                    continue

                # Generate response
                self.chat_once(user_input)

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}[Interrupted]{Style.RESET_ALL}")
                continue
            except EOFError:
                print(f"\n{Fore.YELLOW}Goodbye! (￣▽￣)ノ{Style.RESET_ALL}")
                break

    def _print_banner(self):
        """Print welcome banner."""
        image_status = f"{Fore.GREEN}Enabled{Style.RESET_ALL}" if self.image_enabled else f"{Fore.RED}Disabled{Style.RESET_ALL}"
        vision_status = f"{Fore.GREEN}Enabled{Style.RESET_ALL}" if self.vision_enabled else f"{Fore.RED}Disabled{Style.RESET_ALL}"
        banner = f"""
{Fore.CYAN}╭─────────────────────────────────────────────────╮
│  🤖 Qwen3 Interactive Chat (Thinking Mode)       │
│     Powered by llama-cpp-python                  │
│  🎨 Text-to-Image: LCM-SD1.5 [{image_status}{Fore.CYAN}]              │
│  👁️ Vision: Qwen2-VL [{vision_status}{Fore.CYAN}]                    │
╰─────────────────────────────────────────────────╯{Style.RESET_ALL}

{Fore.YELLOW}Model:{Style.RESET_ALL} {self.model_path}
{Fore.YELLOW}Commands:{Style.RESET_ALL} /quit, /clear, /help, /history, /image, /vision

{Style.DIM}Thinking process will be shown in dimmed text.{Style.RESET_ALL}
{Style.DIM}Use /image <prompt> to generate images.{Style.RESET_ALL}
{Style.DIM}Use /vision <path> to analyze images.{Style.RESET_ALL}
"""
        print(banner)
