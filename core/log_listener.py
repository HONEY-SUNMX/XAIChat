#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Listener Module

A standalone, reusable log listening module that intercepts logs from
third-party libraries (uvicorn, watchfiles, etc.) and triggers callbacks.

Features:
- Intercept any logger (including uvicorn, watchfiles, etc.)
- Register callbacks by log level or keyword
- Chain-style API for fluent configuration
- Thread-safe callback dispatch
- Does not affect original log output

Author: Generated with love by Harei-chan

Usage:
    from core.log_listener import get_log_listener, LogLevel, LogRecord

    listener = get_log_listener()

    def my_callback(record: LogRecord) -> None:
        print(f"Captured: {record.message}")

    listener.watch("uvicorn.error") \\
            .on_keyword("reload", my_callback) \\
            .on_level(LogLevel.ERROR, my_callback) \\
            .start()
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogRecord:
    """Data structure for log records."""
    logger_name: str
    level: int
    level_name: str
    message: str
    timestamp: float
    pathname: str
    lineno: int
    func_name: str
    extra: Dict[str, Any] = field(default_factory=dict)


# Callback function type
LogCallback = Callable[[LogRecord], None]


class CallbackHandler(logging.Handler):
    """
    Custom Handler that intercepts logs and triggers callbacks.
    Does not affect the original log output behavior.
    """

    def __init__(self, listener: "LogListener"):
        super().__init__()
        self._listener = listener

    def emit(self, record: logging.LogRecord) -> None:
        """Process log record and trigger corresponding callbacks."""
        log_record = LogRecord(
            logger_name=record.name,
            level=record.levelno,
            level_name=record.levelname,
            message=record.getMessage(),
            timestamp=record.created,
            pathname=record.pathname,
            lineno=record.lineno,
            func_name=record.funcName,
        )
        self._listener._dispatch_callbacks(log_record)


class LogListener:
    """
    Log Listener - Singleton pattern for global log interception.

    Features:
    - Intercept any logger (including uvicorn, watchfiles, etc.)
    - Register callbacks by log level
    - Register callbacks by keyword matching (supports regex)
    - Does not affect original log output
    - Thread-safe

    Usage:
        listener = LogListener()

        # Watch specific loggers
        listener.watch("uvicorn.error")
        listener.watch("watchfiles.main")

        # Register level callbacks
        listener.on_level(LogLevel.ERROR, my_error_callback)

        # Register keyword callbacks
        listener.on_keyword("reload", my_reload_callback)

        # Start listening
        listener.start()
    """

    _instance: Optional["LogListener"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LogListener":
        """Singleton pattern ensures only one listener instance globally."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._watched_loggers: Set[str] = set()
        self._handlers: Dict[str, CallbackHandler] = {}

        # Intercept mode settings
        self._intercept_settings: Dict[str, bool] = {}
        self._original_handlers: Dict[str, List[logging.Handler]] = {}
        self._original_propagate: Dict[str, bool] = {}

        # Callback registries
        self._level_callbacks: Dict[int, List[LogCallback]] = {}
        self._keyword_callbacks: Dict[str, List[tuple]] = {}  # (callback, case_sensitive)
        self._global_callbacks: List[LogCallback] = []

        # Running state
        self._running = False
        self._callback_lock = threading.Lock()

        self._initialized = True

    # =========================================================================
    # Public API - Watch Configuration
    # =========================================================================

    def watch(self, logger_name: str, intercept: bool = False) -> "LogListener":
        """
        Add a logger to watch.

        Args:
            logger_name: Logger name, e.g., "uvicorn.error", "watchfiles.main"
            intercept: If True, block original output and let callbacks handle it.
                       If False (default), only listen without affecting original output.

        Returns:
            self for method chaining
        """
        self._watched_loggers.add(logger_name)
        self._intercept_settings[logger_name] = intercept
        # If already running, attach handler immediately
        if self._running and logger_name not in self._handlers:
            self._attach_handler(logger_name)
        return self

    def unwatch(self, logger_name: str) -> "LogListener":
        """
        Remove a logger from watch list.

        Args:
            logger_name: Logger name

        Returns:
            self for method chaining
        """
        self._watched_loggers.discard(logger_name)
        if logger_name in self._handlers:
            self._detach_handler(logger_name)
        self._intercept_settings.pop(logger_name, None)
        return self

    def watch_all_uvicorn(self, intercept: bool = False) -> "LogListener":
        """
        Convenience method: watch all uvicorn-related logs.

        Args:
            intercept: If True, block original output and let callbacks handle it.
        """
        return self.watch("uvicorn", intercept) \
                   .watch("uvicorn.error", intercept) \
                   .watch("uvicorn.access", intercept)

    def watch_all_watchfiles(self, intercept: bool = False) -> "LogListener":
        """
        Convenience method: watch all watchfiles-related logs.

        Args:
            intercept: If True, block original output and let callbacks handle it.
        """
        return self.watch("watchfiles", intercept) \
                   .watch("watchfiles.main", intercept)

    # =========================================================================
    # Public API - Callback Registration
    # =========================================================================

    def on_level(
        self,
        level: LogLevel,
        callback: LogCallback
    ) -> "LogListener":
        """
        Register a callback triggered by log level.

        Args:
            level: Log level
            callback: Callback function with signature (LogRecord) -> None

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            if level.value not in self._level_callbacks:
                self._level_callbacks[level.value] = []
            self._level_callbacks[level.value].append(callback)
        return self

    def on_keyword(
        self,
        keyword: str,
        callback: LogCallback,
        case_sensitive: bool = False
    ) -> "LogListener":
        """
        Register a callback triggered by keyword matching.

        Args:
            keyword: Keyword to match (supports regex)
            callback: Callback function
            case_sensitive: Whether to match case-sensitively

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            if keyword not in self._keyword_callbacks:
                self._keyword_callbacks[keyword] = []
            self._keyword_callbacks[keyword].append((callback, case_sensitive))
        return self

    def on_any(self, callback: LogCallback) -> "LogListener":
        """
        Register a global callback that triggers for all captured logs.

        Args:
            callback: Callback function

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            self._global_callbacks.append(callback)
        return self

    def off_level(
        self,
        level: LogLevel,
        callback: Optional[LogCallback] = None
    ) -> "LogListener":
        """
        Unregister a level callback.

        Args:
            level: Log level
            callback: Callback to remove, None removes all callbacks for this level

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            if level.value in self._level_callbacks:
                if callback is None:
                    self._level_callbacks[level.value] = []
                else:
                    self._level_callbacks[level.value] = [
                        cb for cb in self._level_callbacks[level.value]
                        if cb != callback
                    ]
        return self

    def off_keyword(
        self,
        keyword: str,
        callback: Optional[LogCallback] = None
    ) -> "LogListener":
        """
        Unregister a keyword callback.

        Args:
            keyword: Keyword
            callback: Callback to remove, None removes all callbacks for this keyword

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            if keyword in self._keyword_callbacks:
                if callback is None:
                    self._keyword_callbacks[keyword] = []
                else:
                    self._keyword_callbacks[keyword] = [
                        (cb, cs) for cb, cs in self._keyword_callbacks[keyword]
                        if cb != callback
                    ]
        return self

    def off_any(self, callback: Optional[LogCallback] = None) -> "LogListener":
        """
        Unregister a global callback.

        Args:
            callback: Callback to remove, None removes all global callbacks

        Returns:
            self for method chaining
        """
        with self._callback_lock:
            if callback is None:
                self._global_callbacks = []
            else:
                self._global_callbacks = [
                    cb for cb in self._global_callbacks if cb != callback
                ]
        return self

    def clear_callbacks(self) -> "LogListener":
        """Clear all registered callbacks."""
        with self._callback_lock:
            self._level_callbacks.clear()
            self._keyword_callbacks.clear()
            self._global_callbacks.clear()
        return self

    # =========================================================================
    # Public API - Lifecycle Management
    # =========================================================================

    def start(self) -> "LogListener":
        """
        Start log listening.
        Attaches handlers to all registered loggers.

        Returns:
            self for method chaining
        """
        if self._running:
            return self

        for logger_name in self._watched_loggers:
            if logger_name not in self._handlers:
                self._attach_handler(logger_name)

        self._running = True
        return self

    def stop(self) -> "LogListener":
        """
        Stop log listening.
        Removes all attached handlers and restores original handlers if intercepted.

        Returns:
            self for method chaining
        """
        if not self._running:
            return self

        for logger_name in list(self._handlers.keys()):
            self._detach_handler(logger_name)

        self._handlers.clear()
        self._running = False
        return self

    @property
    def is_running(self) -> bool:
        """Check if the listener is currently running."""
        return self._running

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _attach_handler(self, logger_name: str) -> None:
        """Attach a callback handler to the specified logger."""
        logger = logging.getLogger(logger_name)
        handler = CallbackHandler(self)
        handler.setLevel(logging.DEBUG)  # Capture all levels

        # Check if intercept mode is enabled for this logger
        if self._intercept_settings.get(logger_name, False):
            # Save original propagate setting
            self._original_propagate[logger_name] = logger.propagate
            # Disable propagation to parent loggers
            logger.propagate = False
            # Save and remove original handlers
            self._original_handlers[logger_name] = list(logger.handlers)
            for h in self._original_handlers[logger_name]:
                logger.removeHandler(h)

        logger.addHandler(handler)
        self._handlers[logger_name] = handler

    def _detach_handler(self, logger_name: str) -> None:
        """Detach callback handler and restore original handlers if intercepted."""
        if logger_name not in self._handlers:
            return

        logger = logging.getLogger(logger_name)
        # Remove our callback handler
        logger.removeHandler(self._handlers[logger_name])
        del self._handlers[logger_name]

        # Restore original handlers if we intercepted
        if logger_name in self._original_handlers:
            for h in self._original_handlers[logger_name]:
                logger.addHandler(h)
            del self._original_handlers[logger_name]

        # Restore original propagate setting
        if logger_name in self._original_propagate:
            logger.propagate = self._original_propagate[logger_name]
            del self._original_propagate[logger_name]

    def _dispatch_callbacks(self, record: LogRecord) -> None:
        """Dispatch log record to corresponding callbacks."""
        with self._callback_lock:
            # 1. Trigger global callbacks
            for callback in self._global_callbacks:
                self._safe_call(callback, record)

            # 2. Trigger level callbacks
            if record.level in self._level_callbacks:
                for callback in self._level_callbacks[record.level]:
                    self._safe_call(callback, record)

            # 3. Trigger keyword callbacks
            for keyword, callbacks in self._keyword_callbacks.items():
                for callback, case_sensitive in callbacks:
                    message = record.message if case_sensitive else record.message.lower()
                    pattern = keyword if case_sensitive else keyword.lower()
                    if re.search(pattern, message):
                        self._safe_call(callback, record)

    def _safe_call(self, callback: LogCallback, record: LogRecord) -> None:
        """Safely call a callback, catching exceptions to avoid affecting the log system."""
        try:
            callback(record)
        except Exception:
            # Silently handle callback exceptions to avoid affecting normal log flow
            pass


# =============================================================================
# Convenience Functions
# =============================================================================

def get_log_listener() -> LogListener:
    """Get the global LogListener instance."""
    return LogListener()


def create_log_forwarder(target_logger: logging.Logger) -> LogCallback:
    """
    Create a callback that forwards log records to a target logger.

    This is useful when you want to intercept logs from third-party libraries
    and output them through your own logger with custom formatting.

    Args:
        target_logger: The logger to forward logs to.

    Returns:
        A callback function that can be used with on_any(), on_level(), etc.

    Example:
        import logging
        my_logger = logging.getLogger("my_app")
        my_logger.addHandler(logging.StreamHandler())

        listener = get_log_listener()
        listener.watch_all_uvicorn(intercept=True) \
                .on_any(create_log_forwarder(my_logger)) \
                .start()
    """
    def forwarder(record: LogRecord) -> None:
        target_logger.log(record.level, record.message)
    return forwarder


# =============================================================================
# Predefined Empty Callbacks (Placeholders for Future Implementation)
# =============================================================================

def on_uvicorn_reload(record: LogRecord) -> None:
    """Callback placeholder for uvicorn reload events."""
    pass


def on_uvicorn_startup(record: LogRecord) -> None:
    """Callback placeholder for uvicorn startup events."""
    pass


def on_uvicorn_shutdown(record: LogRecord) -> None:
    """Callback placeholder for uvicorn shutdown events."""
    pass


def on_file_change(record: LogRecord) -> None:
    """Callback placeholder for file change events."""
    pass


def on_error_log(record: LogRecord) -> None:
    """Callback placeholder for error logs."""
    pass


def on_warning_log(record: LogRecord) -> None:
    """Callback placeholder for warning logs."""
    pass
