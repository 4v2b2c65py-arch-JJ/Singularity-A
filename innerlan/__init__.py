#!/usr/bin/env python3
"""
QB Protocol - Innerlan Fetch Package
High-level fetch layer via GPT model integration.
"""

from .fetch import InnerlanFetch, innerlan_fetch
from .api.routes import router as innerlan_router

__all__ = [
    "InnerlanFetch",
    "innerlan_fetch",
    "innerlan_router",
]
