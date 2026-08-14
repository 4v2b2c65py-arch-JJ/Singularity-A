#!/usr/bin/env python3
"""
QB Protocol - Sleep Agent Package
Background agent that runs silently without screen flash.
"""

from .sleep import SleepAgent, sleep_agent
from .api.routes import router as sleep_agent_router

__all__ = [
    "SleepAgent",
    "sleep_agent",
    "sleep_agent_router",
]
