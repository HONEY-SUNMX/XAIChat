#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multimodal Chat Service - Unified service for text, vision, and image generation"""

import logging
from typing import Dict, List, AsyncGenerator, Optional, Any
from pathlib import Path
import uuid

from server.services.chat_service import chat_service
from server.services.vision_service import vision_service
from server.services.image_service import image_service

logger = logging.getLogger(__name__)


class MultimodalService:
    """
    Unified multimodal service that coordinates chat, vision, and image generation.

    Message Types:
    - text: Pure text message
    - image_analysis: User uploads image with question
    - generated_image: AI generates an image

    This service follows the Open/Closed Principle by composing existing services
    rather than modifying them.
    """

    def __init__(self):
        # Conversation history: {conversation_id: [messages]}
        self._conversations: Dict[str, List[dict]] = {}

    def _detect_image_generation_intent(self, text: str) -> Optional[str]:
        """
        Detect if user wants to generate an image and extract the prompt.

        Uses fast string matching instead of regex for better performance.

        Returns:
            Optional[str]: Extracted image generation prompt, or None if no intent detected
        """
        text = text.strip()

        # Quick check: if text is too short, skip
        if len(text) < 3:
            return None

        # Chinese keywords detection (fast string matching)
        if text.startswith('画'):
            # "画一只猫" -> "一只猫" -> "只猫" -> return "只猫"
            prompt = text[1:].lstrip('一个张 ')
            return self._clean_prompt(prompt) if prompt else None

        if text.startswith('生成'):
            # "生成一张图片猫咪" -> "一张图片猫咪" -> "猫咪"
            prompt = text[2:].lstrip('一张个 ')
            prompt = prompt.rstrip('图片图画 ')
            return self._clean_prompt(prompt) if prompt else None

        if text.startswith('帮我画'):
            prompt = text[3:].strip()
            return self._clean_prompt(prompt) if prompt else None

        if text.startswith('请画'):
            prompt = text[2:].strip()
            return self._clean_prompt(prompt) if prompt else None

        if text.startswith('创作'):
            prompt = text[2:].rstrip('图片图画 ')
            return self._clean_prompt(prompt) if prompt else None

        # English keywords detection (case-insensitive)
        lower_text = text.lower()

        if lower_text.startswith('draw '):
            prompt = text[5:].strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('generate image'):
            # "generate image of a cat" -> "of a cat" -> "a cat"
            prompt = text[14:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('generate an image'):
            prompt = text[17:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('generate a image'):
            prompt = text[16:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('create image'):
            prompt = text[12:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('create an image'):
            prompt = text[15:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        if lower_text.startswith('create a image'):
            prompt = text[14:].lstrip(' of').strip()
            return self._clean_prompt(prompt) if prompt else None

        return None

    def _clean_prompt(self, prompt: str) -> str:
        """
        Clean up the extracted prompt by removing trailing punctuation.

        Args:
            prompt: Raw extracted prompt

        Returns:
            Cleaned prompt
        """
        # Remove trailing Chinese punctuation
        while prompt and prompt[-1] in '。,!?;:、，！？；：':
            prompt = prompt[:-1]

        return prompt.strip()

    async def stream_response(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        image_path: Optional[str] = None,
        image_id: Optional[str] = None,
        enable_thinking: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Stream multimodal response.

        Args:
            message: User's text message
            conversation_id: Optional conversation ID to maintain context
            image_path: Optional path to uploaded image (deprecated, use image_id)
            image_id: Optional image ID for vision analysis
            enable_thinking: Enable deep reasoning mode for text chat

        Yields:
            SSE formatted events:
            - thinking: Model's thinking process
            - thinking_stream: Real-time thinking content
            - response: Text response content
            - image_generated: Generated image info
            - done: Generation complete with conversation_id
            - error: Error occurred
        """
        try:
            # Generate or use existing conversation ID
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            # Route to appropriate service based on input
            if image_id or image_path:
                # Vision mode: analyze image
                # Use image_id if provided, otherwise extract from path
                final_image_id = image_id or Path(image_path).stem
                logger.info(f"[Multimodal] Vision mode - image_id: {final_image_id}")

                async for event in vision_service.stream_response(
                    image_id=final_image_id,
                    question=message
                ):
                    yield event

                # Save assistant response to history
                # (vision service already handles the response)

            else:
                # Check if user wants to generate an image
                image_prompt = self._detect_image_generation_intent(message)

                if image_prompt:
                    # Image generation mode
                    logger.info(f"[Multimodal] Image generation mode - prompt: {image_prompt}")

                    # Send a text response first
                    yield f"event: response\ndata: 好的,本小姐正在为你绘制: {image_prompt} 🎨\n\n"
                    yield f"event: response\ndata: (这可是需要一点时间的精细工作呢～)\n\n"

                    # Generate image
                    import json
                    async for event in image_service.generate_with_progress(
                        prompt=image_prompt,
                        negative_prompt="",
                        width=512,
                        height=512,
                        seed=None,
                        num_steps=6,
                    ):
                        # image_service returns "data: {json}\n\n" format
                        # Parse the JSON data
                        if event.startswith('data: '):
                            try:
                                data_str = event[6:].strip()
                                data = json.loads(data_str)
                                event_type = data.get('type')
                                
                                if event_type == 'progress':
                                    # Forward progress with preview
                                    yield event
                                elif event_type == 'done':
                                    # Image generation complete - send as image_generated event
                                    yield f"data: {json.dumps({'type': 'image_generated', 'image_url': data.get('image_url'), 'filename': data.get('filename'), 'seed': data.get('seed')})}\n\n"
                                elif event_type == 'error':
                                    yield event
                                    return
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse image service event: {e}")
                                continue

                    # Send final text response
                    yield f"event: response\ndata: \n\n"
                    yield f"event: response\ndata: 完成了！怎么样,本小姐的作品还不错吧~ (￣▽￣)／\n\n"

                else:
                    # Text chat mode
                    logger.info(f"[Multimodal] Text chat mode")

                    # Build prompt with conversation history
                    # Use the existing chat service's conversation management
                    async for event in chat_service.stream_response(
                        message=message,
                        conversation_id=conversation_id,
                        enable_thinking=enable_thinking
                    ):
                        yield event

            # Send done event
            yield f"event: done\ndata: {conversation_id}\n\n"

        except Exception as e:
            logger.error(f"[Multimodal] Error: {e}", exc_info=True)
            yield f"event: error\ndata: {str(e)}\n\n"

    async def get_response(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        image_path: Optional[str] = None,
        image_id: Optional[str] = None,
        enable_thinking: bool = True,
    ) -> dict:
        """
        Get complete multimodal response (non-streaming).

        Returns:
            dict with keys:
            - response: Text response
            - conversation_id: Conversation ID
            - thinking: Optional thinking content
            - image_url: Optional generated image URL
        """
        result = {
            'response': '',
            'conversation_id': conversation_id or str(uuid.uuid4()),
            'thinking': None,
            'image_url': None,
        }

        thinking_parts = []
        response_parts = []

        async for event_str in self.stream_response(
            message=message,
            conversation_id=conversation_id,
            image_path=image_path,
            image_id=image_id,
            enable_thinking=enable_thinking
        ):
            # Parse SSE event
            lines = event_str.strip().split('\n')
            event_type = None
            event_data = None

            for line in lines:
                if line.startswith('event: '):
                    event_type = line[7:].strip()
                elif line.startswith('data: '):
                    event_data = line[6:].strip()

            if event_type == 'thinking':
                thinking_parts.append(event_data or '')
            elif event_type == 'response':
                response_parts.append(event_data or '')
            elif event_type == 'image_generated':
                import json
                img_data = json.loads(event_data)
                result['image_url'] = img_data.get('image_url')
            elif event_type == 'done':
                result['conversation_id'] = event_data
            elif event_type == 'error':
                raise RuntimeError(event_data)

        result['thinking'] = ''.join(thinking_parts) if thinking_parts else None
        result['response'] = ''.join(response_parts)

        return result

    def get_conversation(self, conversation_id: str) -> List[dict]:
        """Get conversation history."""
        return self._conversations.get(conversation_id, [])

    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"[Multimodal] Cleared conversation: {conversation_id}")


# Global singleton instance
multimodal_service = MultimodalService()
