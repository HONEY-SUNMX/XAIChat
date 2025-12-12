#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat Service
Handles text chat with Qwen3 model using llama-cpp-python.

Author: Generated with love by Harei-chan
Performance optimized by Harei-chan (￣▽￣)ノ
"""

import asyncio
import json
import logging
import time
import uuid
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ChatService:
    """
    Chat service for managing conversations with Qwen3 model.

    Features:
    - Lazy model loading (only loads when first request comes in)
    - Conversation history management
    - Streaming response generation
    - Thinking mode support (extracts <think> tags)
    """

    def __init__(self):
        self._llm = None
        self._is_loading = False
        self._conversations: Dict[str, List[dict]] = {}

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._llm is not None

    def _load_model(self) -> None:
        """Load the Qwen3 model using llama-cpp-python."""
        if self._llm is not None or self._is_loading:
            return

        self._is_loading = True
        logger.info("=" * 50)
        logger.info("Starting to load chat model...")

        try:
            from llama_cpp import Llama

            # Use smart model loading: local first, download if not present
            model_path = settings.get_chat_model_path()

            # Determine thread count (0 = auto)
            n_threads = settings.chat_n_threads if settings.chat_n_threads > 0 else (os.cpu_count() or 4)

            logger.info(f"Model path: {model_path}")
            logger.info(f"Context length: {settings.chat_context_length}")
            logger.info(f"CPU threads: {n_threads}")
            logger.info(f"GPU layers: {settings.chat_n_gpu_layers}")

            self._llm = Llama(
                model_path=model_path,
                n_ctx=settings.chat_context_length,
                n_threads=n_threads,
                n_gpu_layers=settings.chat_n_gpu_layers,
                verbose=False,
            )

            logger.info("✅ Chat model loaded successfully!")
            logger.info("=" * 50)

        except Exception as e:
            self._is_loading = False
            logger.error(f"❌ Failed to load chat model: {e}")
            raise RuntimeError(f"Failed to load chat model: {e}")

        self._is_loading = False

    def _get_llm(self):
        """Get the LLM instance, loading if necessary."""
        if self._llm is None:
            self._load_model()
        return self._llm

    def _build_prompt(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        enable_thinking: bool = True
    ) -> str:
        """Build the prompt with conversation history."""
        history = ""

        if conversation_id and conversation_id in self._conversations:
            for msg in self._conversations[conversation_id]:
                if msg["role"] == "user":
                    history += f"<|im_start|>user\n{msg['content']}<|im_end|>\n"
                elif msg["role"] == "assistant":
                    history += f"<|im_start|>assistant\n{msg['content']}<|im_end|>\n"

        # Choose system prompt and assistant start based on thinking mode
        # Default to Chinese output, but respect user's language preference if specified
        base_instruction = (
            "You are Qwen, a helpful assistant. "
            "默认使用简体中文回复用户，包括思考过程也使用中文。"
            "如果用户明确要求使用其他语言，则按照用户要求的语言进行思考和回复。"
        )
        if enable_thinking:
            system_prompt = f"{base_instruction} 请用中文一步一步思考后再回答。"
            assistant_start = "<think>\n"
        else:
            system_prompt = base_instruction
            assistant_start = ""

        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
{history}<|im_start|>user
{message}<|im_end|>
<|im_start|>assistant
{assistant_start}"""
        return prompt

    def _parse_thinking_simple(self, text: str) -> tuple[str, str]:
        """
        Parse thinking content using simple string operations (optimized).

        Returns:
            Tuple of (thinking_content, response_content)
        """
        # Use simple split instead of regex for performance
        if "</think>" in text:
            parts = text.split("</think>", 1)
            thinking = parts[0].strip()
            response = parts[1].strip() if len(parts) > 1 else ""
            # Clean up response
            response = response.replace('<|im_end|>', '').strip()
            return thinking, response

        # No </think> found yet - still in thinking mode
        return text.strip(), ""

    async def stream_response(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        enable_thinking: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for a chat message.
        Optimized for performance with real-time streaming.

        Args:
            message: User message
            conversation_id: Optional conversation ID for context
            enable_thinking: Whether to enable thinking mode (deep reasoning)

        Yields:
            SSE formatted events with thinking and response content
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info(f"📨 [REQUEST] New chat request received")
        logger.info(f"   User message: {message[:80]}{'...' if len(message) > 80 else ''}")
        logger.info(f"   Thinking mode: {'enabled' if enable_thinking else 'disabled'}")

        # Get LLM instance
        logger.info("   Loading LLM...")
        llm_start = time.time()
        llm = self._get_llm()
        logger.info(f"   LLM ready (took {time.time() - llm_start:.2f}s)")

        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        logger.info(f"   Conversation ID: {conversation_id[:8]}...")

        # Initialize conversation history
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            logger.info("   New conversation started")
        else:
            logger.info(f"   Continuing conversation ({len(self._conversations[conversation_id])} messages)")

        prompt = self._build_prompt(message, conversation_id, enable_thinking)
        logger.info(f"   Prompt built: {len(prompt)} chars")

        # State tracking
        full_response = ""
        in_thinking = enable_thinking  # Only track thinking state if enabled
        last_sent_thinking_len = 0
        last_sent_response_len = 0
        token_count = 0
        first_token_time = None

        logger.info("-" * 60)
        logger.info("🚀 [GENERATION] Starting token generation...")

        try:
            # Stream tokens from the model
            for output in llm(
                prompt,
                max_tokens=settings.chat_max_tokens,
                temperature=0.6,
                top_p=0.95,
                top_k=20,
                repeat_penalty=1.1,
                stream=True,
                stop=["<|im_end|>", "<|im_start|>"],
            ):
                token = output["choices"][0]["text"]
                full_response += token
                token_count += 1

                # Log first token latency
                if first_token_time is None:
                    first_token_time = time.time()
                    latency = first_token_time - start_time
                    logger.info(f"   ⚡ First token latency: {latency:.2f}s")

                # Log progress periodically
                if token_count % settings.log_progress_interval == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"   📊 Progress: {token_count} tokens, {elapsed:.1f}s elapsed")

                # Check for </think> tag transition
                if in_thinking and "</think>" in full_response:
                    in_thinking = False
                    thinking_time = time.time() - start_time
                    logger.info(f"   💭 Thinking phase complete ({thinking_time:.2f}s)")

                    # Parse and send thinking content
                    thinking, response = self._parse_thinking_simple(full_response)
                    if thinking:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"
                        last_sent_thinking_len = len(thinking)
                        logger.info(f"   📤 Sent thinking: {len(thinking)} chars")

                    # Send any initial response content
                    if response:
                        yield f"data: {json.dumps({'type': 'response', 'content': response})}\n\n"
                        last_sent_response_len = len(response)

                    await asyncio.sleep(0)

                # Stream thinking content in real-time (every N tokens during thinking)
                elif in_thinking and token_count % settings.thinking_stream_batch_size == 0:
                    current_thinking = full_response.strip()
                    if len(current_thinking) > last_sent_thinking_len:
                        new_thinking = current_thinking[last_sent_thinking_len:]
                        yield f"data: {json.dumps({'type': 'thinking_stream', 'content': new_thinking})}\n\n"
                        last_sent_thinking_len = len(current_thinking)
                        await asyncio.sleep(0)

                # Stream response content (every batch_size tokens after thinking)
                elif not in_thinking and token_count % settings.stream_batch_size == 0:
                    _, response = self._parse_thinking_simple(full_response)
                    if response and len(response) > last_sent_response_len:
                        new_content = response[last_sent_response_len:]
                        yield f"data: {json.dumps({'type': 'response', 'content': new_content})}\n\n"
                        last_sent_response_len = len(response)
                        await asyncio.sleep(0)

            # Final content
            thinking, response = self._parse_thinking_simple(full_response)

            # Send any remaining thinking (if </think> was never found)
            if in_thinking and thinking:
                yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"
                logger.info(f"   📤 Sent final thinking: {len(thinking)} chars")

            # Send remaining response content
            if response and len(response) > last_sent_response_len:
                new_content = response[last_sent_response_len:]
                yield f"data: {json.dumps({'type': 'response', 'content': new_content})}\n\n"

            # Store in conversation history
            self._conversations[conversation_id].append({
                "role": "user",
                "content": message
            })
            self._conversations[conversation_id].append({
                "role": "assistant",
                "content": response
            })

            # Final stats
            elapsed = time.time() - start_time
            speed = token_count / elapsed if elapsed > 0 else 0
            logger.info("-" * 60)
            logger.info(f"✅ [COMPLETE] Generation finished!")
            logger.info(f"   📊 Total tokens: {token_count}")
            logger.info(f"   📝 Response length: {len(response)} chars")
            logger.info(f"   ⏱️  Total time: {elapsed:.2f}s")
            logger.info(f"   🚀 Speed: {speed:.1f} tokens/s")
            logger.info("=" * 60)

            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [ERROR] Generation failed after {elapsed:.2f}s")
            logger.error(f"   Error: {str(e)}")
            logger.error("=" * 60)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    async def get_response(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        enable_thinking: bool = True
    ) -> dict:
        """
        Generate non-streaming response for a chat message.

        Args:
            message: User message
            conversation_id: Optional conversation ID for context
            enable_thinking: Whether to enable thinking mode (deep reasoning)

        Returns:
            Dictionary with response, thinking, and conversation_id
        """
        llm = self._get_llm()

        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        prompt = self._build_prompt(message, conversation_id, enable_thinking)

        # Generate complete response
        output = llm(
            prompt,
            max_tokens=settings.chat_max_tokens,
            temperature=0.6,
            top_p=0.95,
            top_k=20,
            repeat_penalty=1.1,
            stop=["<|im_end|>", "<|im_start|>"],
        )

        full_response = output["choices"][0]["text"]
        thinking, response = self._parse_thinking_simple(full_response)

        # Store in conversation history
        self._conversations[conversation_id].append({
            "role": "user",
            "content": message
        })
        self._conversations[conversation_id].append({
            "role": "assistant",
            "content": response
        })

        return {
            "response": response,
            "thinking": thinking if thinking else None,
            "conversation_id": conversation_id
        }

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a specific conversation history."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    def get_conversation(self, conversation_id: str) -> Optional[List[dict]]:
        """Get conversation history by ID."""
        return self._conversations.get(conversation_id)


# Global service instance
chat_service = ChatService()
