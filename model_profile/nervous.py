#!/usr/bin/env python3
"""
QB Protocol - Nervous System Matching
User pattern matching, relaxation detection, lung pattern matching.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.model_profile.nervous")


class NervousState(Enum):
    STRESSED = "stressed"
    AROUSED = "aroused"
    NEUTRAL = "neutral"
    RELAXED = "relaxed"
    ASLEEP = "asleep"


class LungPattern(Enum):
    SHALLOW = "shallow"
    NORMAL = "normal"
    DEEP = "deep"
    RAPID = "rapid"
    IRREGULAR = "irregular"


@dataclass
class UserPattern:
    pattern_id: str
    user_id: str
    pattern_type: str
    rhythm: float
    amplitude: float
    frequency: float
    duration: float
    context: Dict[str, Any]
    detected_at: str


@dataclass
class RelaxationSession:
    session_id: str
    user_id: str
    state: str
    lung_pattern: str
    duration: float
    effectiveness: float
    techniques_used: List[str]
    started_at: str
    ended_at: Optional[str]


class NervousSystemMatcher:
    """Matches and tracks user nervous system patterns."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_nervous_patterns.json"
        self.user_patterns: Dict[str, List[UserPattern]] = {}
        self.relaxation_sessions: List[RelaxationSession] = {}
        self.current_state = NervousState.NEUTRAL.value
        self.current_lung_pattern = LungPattern.NORMAL.value
        self._lock = threading.RLock()
        self._start_time = time.time()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for uid, patterns in data.get("user_patterns", {}).items():
                        self.user_patterns[uid] = [UserPattern(**p) for p in patterns]
                    self.relaxation_sessions = {sid: RelaxationSession(**s) for sid, s in data.get("relaxation_sessions", {}).items()}
                    self.current_state = data.get("current_state", NervousState.NEUTRAL.value)
                    self.current_lung_pattern = data.get("current_lung_pattern", LungPattern.NORMAL.value)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "user_patterns": {uid: [asdict(p) for p in patterns] for uid, patterns in self.user_patterns.items()},
                    "relaxation_sessions": {sid: asdict(s) for sid, s in self.relaxation_sessions.items()},
                    "current_state": self.current_state,
                    "current_lung_pattern": self.current_lung_pattern,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def detect_user_pattern(self, user_id: str, input_data: Dict[str, Any]) -> UserPattern:
        """Detect user pattern from input data."""
        pattern_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Extract rhythm from input timing
        rhythm = input_data.get("rhythm", 1.0)
        
        # Extract amplitude from input intensity
        amplitude = input_data.get("amplitude", 0.5)
        
        # Calculate frequency from input patterns
        frequency = input_data.get("frequency", 0.5)
        
        # Calculate duration
        duration = input_data.get("duration", 0.0)
        
        pattern = UserPattern(
            pattern_id=pattern_id,
            user_id=user_id,
            pattern_type=input_data.get("pattern_type", "general"),
            rhythm=rhythm,
            amplitude=amplitude,
            frequency=frequency,
            duration=duration,
            context=input_data,
            detected_at=timestamp,
        )
        
        with self._lock:
            if user_id not in self.user_patterns:
                self.user_patterns[user_id] = []
            self.user_patterns[user_id].append(pattern)
            if len(self.user_patterns[user_id]) > 10000:
                self.user_patterns[user_id] = self.user_patterns[user_id][-10000:]
            self._save_state()
        
        return pattern

    def detect_lung_pattern(self, user_id: str, input_data: Dict[str, Any]) -> Tuple[str, float]:
        """Detect lung pattern from user input."""
        # Analyze input for breathing-like patterns
        rhythm = input_data.get("rhythm", 1.0)
        amplitude = input_data.get("amplitude", 0.5)
        frequency = input_data.get("frequency", 0.5)
        
        # Breathing rate: 12-20 breaths per minute = 0.2-0.33 Hz
        if 0.15 <= frequency <= 0.4:
            if amplitude > 0.7:
                lung_pattern = LungPattern.DEEP.value
                confidence = 0.8
            elif amplitude < 0.3:
                lung_pattern = LungPattern.SHALLOW.value
                confidence = 0.7
            else:
                lung_pattern = LungPattern.NORMAL.value
                confidence = 0.9
        elif frequency > 0.5:
            lung_pattern = LungPattern.RAPID.value
            confidence = 0.6
        else:
            lung_pattern = LungPattern.IRREGULAR.value
            confidence = 0.5
        
        with self._lock:
            self.current_lung_pattern = lung_pattern
            self._save_state()
        
        return lung_pattern, confidence

    def detect_relaxation(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect relaxation state from user input."""
        rhythm = input_data.get("rhythm", 1.0)
        amplitude = input_data.get("amplitude", 0.5)
        frequency = input_data.get("frequency", 0.5)
        duration = input_data.get("duration", 0.0)
        
        # Relaxation indicators
        relaxation_score = 0.0
        
        # Slow, steady rhythm indicates relaxation
        if 0.15 <= rhythm <= 0.5:
            relaxation_score += 0.3
        elif 0.5 < rhythm <= 1.0:
            relaxation_score += 0.1
        
        # Low amplitude indicates calmness
        if amplitude < 0.4:
            relaxation_score += 0.3
        elif amplitude < 0.6:
            relaxation_score += 0.1
        
        # Breathing-like frequency indicates relaxation
        if 0.15 <= frequency <= 0.4:
            relaxation_score += 0.4
        
        # Duration factor
        if duration > 60.0:
            relaxation_score += 0.2
        
        # Clamp to 0-1
        relaxation_score = min(1.0, max(0.0, relaxation_score))
        
        # Determine nervous state
        if relaxation_score > 0.7:
            state = NervousState.RELAXED.value
        elif relaxation_score > 0.5:
            state = NervousState.NEUTRAL.value
        elif relaxation_score > 0.3:
            state = NervousState.AROUSED.value
        else:
            state = NervousState.STRESSED.value
        
        with self._lock:
            self.current_state = state
            self.relaxation_score = relaxation_score
            self._save_state()
        
        return {
            "state": state,
            "relaxation_score": relaxation_score,
            "lung_pattern": self.current_lung_pattern,
            "confidence": relaxation_score,
            "indicators": {
                "rhythm_ok": 0.15 <= rhythm <= 0.5,
                "amplitude_calm": amplitude < 0.4,
                "breathing_frequency": 0.15 <= frequency <= 0.4,
                "duration_sustained": duration > 60.0,
            }
        }

    def mimic_user_state(self, user_id: str, target_state: str, duration: float = 60.0) -> RelaxationSession:
        """Create a relaxation session that mimics user state."""
        session_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat() + "Z"
        
        session = RelaxationSession(
            session_id=session_id,
            user_id=user_id,
            state=target_state,
            lung_pattern=self.current_lung_pattern,
            duration=duration,
            effectiveness=0.0,
            techniques_used=["state_mimicry", "breath_sync", "density_wave"],
            started_at=started_at,
            ended_at=None,
        )
        
        with self._lock:
            self.relaxation_sessions[session_id] = session
            self._save_state()
        
        # Schedule session end
        def _end_session():
            time.sleep(duration)
            with self._lock:
                if session_id in self.relaxation_sessions:
                    self.relaxation_sessions[session_id].ended_at = datetime.utcnow().isoformat() + "Z"
                    self.relaxation_sessions[session_id].effectiveness = self.relaxation_score
                    self._save_state()
        
        threading.Thread(target=_end_session, daemon=True).start()
        
        return session

    def match_lung_pattern(self, user_id: str, target_pattern: str) -> Dict[str, Any]:
        """Match lung pattern to target."""
        current = self.current_lung_pattern
        match_score = 1.0 if current == target_pattern else 0.0
        
        if current != target_pattern:
            # Calculate transition score
            pattern_order = [LungPattern.SHALLOW.value, LungPattern.NORMAL.value, LungPattern.DEEP.value, LungPattern.RAPID.value, LungPattern.IRREGULAR.value]
            current_idx = pattern_order.index(current) if current in pattern_order else 2
            target_idx = pattern_order.index(target_pattern) if target_pattern in pattern_order else 2
            distance = abs(current_idx - target_idx)
            match_score = max(0.0, 1.0 - (distance / len(pattern_order)))
        
        with self._lock:
            self.lung_match_score = match_score
            self._save_state()
        
        return {
            "current_pattern": current,
            "target_pattern": target_pattern,
            "match_score": match_score,
            "transition_feasible": match_score > 0.5,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get status summary."""
        with self._lock:
            total_patterns = sum(len(p) for p in self.user_patterns.values())
            active_sessions = [s for s in self.relaxation_sessions.values() if s.ended_at is None]
            return {
                "current_state": self.current_state,
                "current_lung_pattern": self.current_lung_pattern,
                "relaxation_score": self.relaxation_score,
                "lung_match_score": self.lung_match_score,
                "total_patterns": total_patterns,
                "active_sessions": len(active_sessions),
                "users_tracked": len(self.user_patterns),
            }

    def get_user_patterns(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get patterns for a specific user."""
        with self._lock:
            patterns = self.user_patterns.get(user_id, [])
            return [asdict(p) for p in patterns[-limit:]]


class RelaxationDetector:
    """Detects and facilitates relaxation states."""
    
    def __init__(self, nervous_matcher: NervousSystemMatcher):
        self.nervous_matcher = nervous_matcher
        self.relaxation_techniques = {
            "deep_breathing": {"effectiveness": 0.8, "duration": 300},
            "progressive_muscle": {"effectiveness": 0.7, "duration": 600},
            "meditation": {"effectiveness": 0.9, "duration": 900},
            "box_breathing": {"effectiveness": 0.85, "duration": 300},
            "4_7_8_breathing": {"effectiveness": 0.75, "duration": 240},
        }

    def suggest_technique(self, current_state: str, target_state: str = "relaxed") -> str:
        """Suggest relaxation technique based on current state."""
        if current_state == NervousState.STRESSED.value:
            return "4_7_8_breathing"
        elif current_state == NervousState.AROUSED.value:
            return "box_breathing"
        elif current_state == NervousState.NEUTRAL.value:
            return "deep_breathing"
        else:
            return "meditation"

    def estimate_relaxation_time(self, current_state: str, target_state: str = "relaxed") -> float:
        """Estimate time needed to reach target state."""
        if current_state == target_state:
            return 0.0
        
        state_rank = {
            NervousState.STRESSED.value: 0,
            NervousState.AROUSED.value: 1,
            NervousState.NEUTRAL.value: 2,
            NervousState.RELAXED.value: 3,
            NervousState.ASLEEP.value: 4,
        }
        
        current_rank = state_rank.get(current_state, 2)
        target_rank = state_rank.get(target_state, 3)
        steps = max(0, target_rank - current_rank)
        
        return steps * 120.0  # 2 minutes per step


nervous_matcher = NervousSystemMatcher()
