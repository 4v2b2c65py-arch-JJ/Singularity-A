#!/usr/bin/env python3
"""
QB Protocol - Icon Generator Package
Automatic icon generation for OS artifacts and applications.
"""

from .generator import IconGenerator, icon_generator
from .api.routes import router as icon_generator_router

__all__ = [
    "IconGenerator",
    "icon_generator",
    "icon_generator_router",
]
