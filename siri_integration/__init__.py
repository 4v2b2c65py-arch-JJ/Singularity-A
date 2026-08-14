#!/usr/bin/env python3
"""
QB Protocol - Siri Integration Package
Voice commands, Shortcuts, session tokens, autonomous actions.
"""

from .siri import SiriIntegration, siri_integration
from .shortcuts import ShortcutManager, shortcut_manager
from .session import SiriSessionManager, siri_session_manager
from .responses import SiriResponseStore, siri_response_store
from .api.routes import router as siri_router

__all__ = [
    "SiriIntegration",
    "siri_integration",
    "ShortcutManager",
    "shortcut_manager",
    "SiriSessionManager",
    "siri_session_manager",
    "SiriResponseStore",
    "siri_response_store",
    "siri_router",
]
