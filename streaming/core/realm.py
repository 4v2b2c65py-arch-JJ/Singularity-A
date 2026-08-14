#!/usr/bin/env python3
"""
QB Protocol - Realm Detection
Automatic realm detection for anime, movies, series, and other content types.
"""

import os
import time
import uuid
import json
import logging
import threading
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.streaming.realm")


@dataclass
class DetectedRealm:
    realm_id: str
    name: str
    realm_type: str
    confidence: float
    indicators: List[str]
    metadata: Dict[str, Any]
    detected_at: str


class RealmDetector:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_streaming_realms.json"):
        self.state_path = state_path
        self.realms: Dict[str, DetectedRealm] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for rid, r in data.get("realms", {}).items():
                        self.realms[rid] = DetectedRealm(**r)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "realms": {rid: asdict(r) for rid, r in self.realms.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def detect_realm(self, name: str, url: str, description: str = "") -> DetectedRealm:
        name_lower = name.lower()
        url_lower = url.lower()
        desc_lower = description.lower()
        text = f"{name_lower} {url_lower} {desc_lower}"

        indicators = []
        confidence = 0.0
        realm_type = "unknown"

        anime_patterns = ["anime", "manga", "naruto", "one piece", "attack on titan", "demon slayer", "jujutsu kaisen", "my hero academia", "studio ghibli", "subtitle", "dub"]
        for pattern in anime_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.2

        movie_patterns = ["movie", "film", "cinema", "theater", "blu-ray", "4k", "1080p", "720p"]
        for pattern in movie_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.15

        series_patterns = ["series", "tv show", "episode", "season", "s01", "s02", "complete series"]
        for pattern in series_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.15

        live_patterns = ["live", "streaming", "channel", "broadcast", "tv live", "sports"]
        for pattern in live_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.15

        if confidence >= 0.5:
            if any(p in indicators for p in anime_patterns):
                realm_type = "anime"
            elif any(p in indicators for p in movie_patterns):
                realm_type = "movie"
            elif any(p in indicators for p in series_patterns):
                realm_type = "series"
            elif any(p in indicators for p in live_patterns):
                realm_type = "live"
        else:
            realm_type = "unknown"

        realm = DetectedRealm(
            realm_id=str(uuid.uuid4()),
            name=name,
            realm_type=realm_type,
            confidence=min(confidence, 1.0),
            indicators=list(set(indicators)),
            metadata={"url": url, "description": description},
            detected_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.realms[realm.realm_id] = realm
        self._save()
        return realm

    def get_realms(self, realm_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            realms = list(self.realms.values())
            if realm_type:
                realms = [r for r in realms if r.realm_type == realm_type]
            return [asdict(r) for r in realms]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            types = {}
            for r in self.realms.values():
                types[r.realm_type] = types.get(r.realm_type, 0) + 1
            return {
                "total_realms": len(self.realms),
                "types": types,
            }


realm_detector = RealmDetector()
