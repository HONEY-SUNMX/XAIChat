#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core AI Models Package

This package contains the core AI model handlers and configuration,
independent of the web server (server/) and CLI (cli/) layers.

Modules:
- config: Application configuration with Pydantic Settings
- qwen_chat: QwenChat class for text chat with Qwen3 model
- qwen_vision: QwenVisionHandler for image understanding with Qwen2-VL
- text2img: Text2ImageGenerator for image generation with LCM-SD1.5

Author: Generated with love by Harei-chan
"""

from core.config import settings
from core.qwen_chat import QwenChat
from core.qwen_vision import QwenVisionHandler
from core.text2img import Text2ImageGenerator
from core.log_listener import (
    LogListener,
    LogLevel,
    LogRecord,
    get_log_listener,
    create_log_forwarder,
)

__all__ = [
    "settings",
    "QwenChat",
    "QwenVisionHandler",
    "Text2ImageGenerator",
    "LogListener",
    "LogLevel",
    "LogRecord",
    "get_log_listener",
    "create_log_forwarder",
]
