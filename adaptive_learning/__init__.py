#!/usr/bin/env python3
"""
QB Protocol - Adaptive Learning Package
Keyboard style learning, emoji generation, password remembering.
"""

from .keyboard import AdaptiveKeyboard, adaptive_keyboard
from .emoji import EmojiGenerator, emoji_generator
from .passwords import PasswordManager, password_manager
from .api.routes import router as adaptive_learning_router

__all__ = [
    "AdaptiveKeyboard",
    "adaptive_keyboard",
    "EmojiGenerator",
    "emoji_generator",
    "PasswordManager",
    "password_manager",
    "adaptive_learning_router",
]
