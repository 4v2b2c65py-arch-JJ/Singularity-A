#!/usr/bin/env python3
"""
QB Protocol - Communication Integration
Main integration module for the communication system.
"""

import os
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.communication.integration")


class CommunicationIntegration:
    def __init__(self, repo_path: Path = Path(".")):
        self.repo_path = Path(repo_path).resolve()
        self._lock = threading.RLock()
        self._timeline = None
        self._message_log = None
        self._coordinates = None
        self._github = None
        self._addons = None
        self._sessions = None
        self._celestial = None

    def _get_timeline(self):
        if self._timeline is None:
            try:
                from communication.timeline import communication_timeline
                self._timeline = communication_timeline
            except ImportError:
                pass
        return self._timeline

    def _get_message_log(self):
        if self._message_log is None:
            try:
                from communication.message_log import message_log
                self._message_log = message_log
            except ImportError:
                pass
        return self._message_log

    def _get_coordinates(self):
        if self._coordinates is None:
            try:
                from communication.coordinate_system import coordinate_system
                self._coordinates = coordinate_system
            except ImportError:
                pass
        return self._coordinates

    def _get_github(self):
        if self._github is None:
            try:
                from communication.github_manager import github_manager
                self._github = github_manager
            except ImportError:
                pass
        return self._github

    def _get_addons(self):
        if self._addons is None:
            try:
                from communication.addon_discovery import addon_discovery
                self._addons = addon_discovery
            except ImportError:
                pass
        return self._addons

    def _get_sessions(self):
        if self._sessions is None:
            try:
                from communication.session_sharing import session_sharing
                self._sessions = session_sharing
            except ImportError:
                pass
        return self._sessions

    def _get_celestial(self):
        if self._celestial is None:
            try:
                from communication.celestial_router import celestial_router
                self._celestial = celestial_router
            except ImportError:
                pass
        return self._celestial

    def record_conversation(self, conversation_id: str, content: Dict[str, Any], user_info: Dict[str, Any], coordinates: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        timeline = self._get_timeline()
        if not timeline:
            return {"status": "error", "message": "Timeline module not available"}
        if not coordinates:
            coordinates = {"dimension": "earth", "universe": "current"}
        entry = timeline.record(
            conversation_id=conversation_id,
            mode="present",
            content=content,
            coordinates=coordinates,
            user_info=user_info,
            metadata=metadata,
        )
        message_log = self._get_message_log()
        if message_log:
            message_log.record(
                conversation_id=conversation_id,
                message_type="conversation",
                sender=user_info.get("username", "unknown"),
                recipient="system",
                content=content,
                coordinates=coordinates,
                metadata=metadata,
            )
        return {"status": "success", "entry": asdict(entry)}

    def get_conversation_history(self, conversation_id: str, mode: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        timeline = self._get_timeline()
        if not timeline:
            return {"status": "error", "message": "Timeline module not available"}
        entries = timeline.get_timeline(conversation_id, limit=limit)
        return {"status": "success", "conversation_id": conversation_id, "entries": entries}

    def set_timeline_mode(self, conversation_id: str, mode: str) -> Dict[str, Any]:
        timeline = self._get_timeline()
        if not timeline:
            return {"status": "error", "message": "Timeline module not available"}
        return timeline.set_active_mode(conversation_id, mode)

    def auto_commit(self, message_template: str = "QB Protocol: auto-sync {timestamp}") -> Dict[str, Any]:
        github = self._get_github()
        if not github:
            return {"status": "error", "message": "GitHub module not available"}
        return github.auto_commit_push(message_template)

    def get_system_status(self) -> Dict[str, Any]:
        status = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "modules": {},
        }
        github = self._get_github()
        if github:
            status["modules"]["github"] = github.get_status()
        timeline = self._get_timeline()
        if timeline:
            status["modules"]["timeline"] = timeline.get_status()
        message_log = self._get_message_log()
        if message_log:
            status["modules"]["messages"] = message_log.get_status()
        coordinates = self._get_coordinates()
        if coordinates:
            status["modules"]["coordinates"] = coordinates.get_status()
        addons = self._get_addons()
        if addons:
            status["modules"]["addons"] = addons.get_status()
        sessions = self._get_sessions()
        if sessions:
            status["modules"]["sessions"] = sessions.get_status()
        celestial = self._get_celestial()
        if celestial:
            status["modules"]["celestial"] = celestial.get_status()
        return status


communication_integration = CommunicationIntegration()
