#!/usr/bin/env python3
"""
QB Protocol - VR Quest Companion Package
"""

from .oscquery import OSCQueryBridge, OSCQueryDiscovery, oscquery_bridge
from .slimevr import SlimeVRBridge, SlimeVRTracker, slimevr_bridge
from .tracking import TrackingManager, TrackingProfile, tracking_manager
from .auto_reconnect import AutoReconnect, ReconnectConfig, auto_reconnect
from .service import CompanionService, ServiceState, companion_service

__all__ = [
    "OSCQueryBridge",
    "OSCQueryDiscovery",
    "oscquery_bridge",
    "SlimeVRBridge",
    "SlimeVRTracker",
    "slimevr_bridge",
    "TrackingManager",
    "TrackingProfile",
    "tracking_manager",
    "AutoReconnect",
    "ReconnectConfig",
    "auto_reconnect",
    "CompanionService",
    "ServiceState",
    "companion_service",
]
