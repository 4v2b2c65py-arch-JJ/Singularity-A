#!/usr/bin/env python3
"""
QB Protocol - Siri Integration Package
Version: 1.0.0
Voice commands, Shortcuts, session tokens, autonomous actions.
"""

from .siri import SiriIntegration, siri_integration
from .shortcuts import ShortcutManager, shortcut_manager
from .session import SiriSessionManager, siri_session_manager
from .responses import SiriResponseStore, SiriConversationModel, siri_response_store, siri_conversation_model
from .api.routes import router as siri_router

__version__ = "1.0.0"
__all__ = [
    "SiriIntegration",
    "siri_integration",
    "ShortcutManager",
    "shortcut_manager",
    "SiriSessionManager",
    "siri_session_manager",
    "SiriResponseStore",
    "SiriConversationModel",
    "siri_response_store",
    "siri_conversation_model",
    "siri_router",
]
