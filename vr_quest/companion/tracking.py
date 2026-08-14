#!/usr/bin/env python3
"""
QB Protocol - VR Quest Tracking Manager
Full-body tracking profiles and management.
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
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.tracking")


class TrackingProfile(Enum):
    HEADSET_CONTROLLERS = 0
    HIP_FEET = 1
    HIP_FEET_KNEES = 2
    HIP_FEET_KNEES_ELBOWS = 3


@dataclass
class TrackingState:
    profile: str
    trackers: List[str]
    active: bool
    drift: float
    packet_loss: float
    metadata: Dict[str, Any]
    updated_at: str


class TrackingManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_tracking.json"):
        self.state_path = state_path
        self.states: Dict[str, TrackingState] = {}
        self.active_profile: str = TrackingProfile.HIP_FEET.value
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("states", {}).items():
                        self.states[sid] = TrackingState(**s)
                    self.active_profile = data.get("active_profile", TrackingProfile.HIP_FEET.value)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "states": {sid: asdict(s) for sid, s in self.states.items()},
                    "active_profile": self.active_profile,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def set_profile(self, profile: "TrackingProfile | int | str") -> TrackingState:
        if isinstance(profile, int):
            profile = TrackingProfile(profile)
        if isinstance(profile, str):
            profile = TrackingProfile(int(profile))
        profile_value = profile.value

        tracker_map = {
            TrackingProfile.HEADSET_CONTROLLERS.value: ["head", "left_controller", "right_controller"],
            TrackingProfile.HIP_FEET.value: ["head", "left_controller", "right_controller", "hip", "left_foot", "right_foot"],
            TrackingProfile.HIP_FEET_KNEES.value: ["head", "left_controller", "right_controller", "hip", "left_foot", "right_foot", "left_knee", "right_knee"],
            TrackingProfile.HIP_FEET_KNEES_ELBOWS.value: ["head", "left_controller", "right_controller", "hip", "left_foot", "right_foot", "left_knee", "right_knee", "left_elbow", "right_elbow"],
        }

        state = TrackingState(
            profile=TrackingProfile(profile_value).name,
            trackers=tracker_map.get(profile_value, []),
            active=True,
            drift=0.0,
            packet_loss=0.0,
            metadata={"default": True},
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.states[state.profile] = state
            self.active_profile = str(profile_value)
        self._save()
        return state

    def update_tracking_quality(self, drift: float, packet_loss: float) -> Optional[TrackingState]:
        with self._lock:
            state = self.states.get(self.active_profile)
            if not state:
                return None
            state.drift = drift
            state.packet_loss = packet_loss
            state.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return state

    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            state = self.states.get(self.active_profile)
            return asdict(state) if state else None

    def get_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.states.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = self.states.get(self.active_profile)
            return {
                "active_profile": self.active_profile,
                "total_profiles": len(self.states),
                "drift": active.drift if active else 0,
                "packet_loss": active.packet_loss if active else 0,
            }


tracking_manager = TrackingManager()
