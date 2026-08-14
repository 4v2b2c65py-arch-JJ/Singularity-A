#!/usr/bin/env python3
"""
QB Protocol - Cross-Platform Package
Automatic deployment and shell support for all environments.
"""

from .detector import PlatformDetector, platform_detector
from .deployer import CrossPlatformDeployer, cross_platform_deployer
from .shell import FreedomShell, freedom_shell
from .metal import MetalManager, metal_manager
from .cloud import CloudConverter, cloud_converter
from .testing import AutoTester, auto_tester
from .api.routes import router as cross_platform_router

__all__ = [
    "PlatformDetector",
    "platform_detector",
    "CrossPlatformDeployer",
    "cross_platform_deployer",
    "FreedomShell",
    "freedom_shell",
    "MetalManager",
    "metal_manager",
    "CloudConverter",
    "cloud_converter",
    "AutoTester",
    "auto_tester",
    "cross_platform_router",
]
