#!/usr/bin/env python3
"""
QB Protocol - Natural Systems Package
Research catalog: plants, fungi, chemicals, publications, products.
"""

from .catalog import NaturalCatalog, natural_catalog
from .api.routes import router as natural_systems_router

__all__ = [
    "NaturalCatalog",
    "natural_catalog",
    "natural_systems_router",
]
