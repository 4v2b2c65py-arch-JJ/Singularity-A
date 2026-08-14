#!/usr/bin/env python3
"""
QB Protocol - VR Quest Package
Lightweight Quest 3 VR package with PC companion.
"""

from .core.regions import RegionManager, Region, region_manager
from .core.session import SessionManager, Session, session_manager
from .core.content import ContentManager, ContentManifest, content_manager
from .core.diagnostics import NetworkDiagnostics, DiagnosticResult, network_diagnostics
from .companion.oscquery import OSCQueryBridge, OSCQueryDiscovery, oscquery_bridge
from .companion.slimevr import SlimeVRBridge, SlimeVRTracker, slimevr_bridge
from .companion.tracking import TrackingManager, TrackingProfile, tracking_manager
from .companion.auto_reconnect import AutoReconnect, ReconnectConfig, auto_reconnect
from .companion.service import CompanionService, ServiceState, companion_service
from .quest.config import QuestConfig, PackageBudget, quest_config
from .quest.avatar import AvatarManager, AvatarTier, avatar_manager

__all__ = [
    "RegionManager",
    "Region",
    "region_manager",
    "SessionManager",
    "Session",
    "session_manager",
    "ContentManager",
    "ContentManifest",
    "content_manager",
    "NetworkDiagnostics",
    "DiagnosticResult",
    "network_diagnostics",
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
    "QuestConfig",
    "PackageBudget",
    "quest_config",
    "AvatarManager",
    "AvatarTier",
    "avatar_manager",
]
