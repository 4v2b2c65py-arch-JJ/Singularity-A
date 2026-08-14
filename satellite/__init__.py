#!/usr/bin/env python3
"""
QB Protocol - Satellite Package
Real satellite/modem communication with government assurance.
"""

from .core.iridium import IridiumSBD, SatelliteConfig, ExitCode, iridium_manager
from .core.security import SatelliteSecurity, SecurityClearance, satellite_security
from .core.government import GovernmentAssurance, ComplianceLevel, government_assurance
from .core.udp_bridge import UDPBridge, udp_bridge
from .api.routes import router as satellite_router

__all__ = [
    "IridiumSBD",
    "SatelliteConfig",
    "ExitCode",
    "iridium_manager",
    "SatelliteSecurity",
    "SecurityClearance",
    "satellite_security",
    "GovernmentAssurance",
    "ComplianceLevel",
    "government_assurance",
    "UDPBridge",
    "udp_bridge",
    "satellite_router",
]
