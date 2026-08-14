#!/usr/bin/env python3
"""
QB Protocol - VR Quest Configuration
Quest app configuration and package budget management.
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

LOG = logging.getLogger("qb_protocol.vr_quest.config")


@dataclass
class PackageBudget:
    max_installed_mb: int = 4500
    current_installed_mb: int = 0
    cache_max_mb: int = 900
    current_cache_mb: int = 0
    textures_resolution: str = "2048"
    audio_compression: str = "ogg"
    mesh_lod_levels: int = 3


@dataclass
class QuestConfig:
    app_version: str
    client_version: str
    world_version: str
    companion_version: str
    release_channel: str
    budget: Dict[str, Any]
    supported_devices: List[str]
    metadata: Dict[str, Any]
    updated_at: str


class QuestConfigManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_quest_config.json"):
        self.state_path = state_path
        self.config: Optional[QuestConfig] = None
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.config = QuestConfig(**data)
            except Exception:
                pass

    def _save(self):
        if not self.config:
            return
        try:
            with open(self.state_path, "w") as f:
                json.dump(asdict(self.config), f, indent=2, default=str)
        except Exception:
            pass

    def initialize(self, app_version: str = "1.0.0", release_channel: str = "production") -> QuestConfig:
        budget = PackageBudget()
        self.config = QuestConfig(
            app_version=app_version,
            client_version=app_version,
            world_version="1.0.0",
            companion_version="1.0.0",
            release_channel=release_channel,
            budget=asdict(budget),
            supported_devices=["Quest 3", "Quest 3S", "Quest Pro", "Quest 2"],
            metadata={},
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        self._save()
        return self.config

    def update_budget(self, installed_mb: int, cache_mb: int) -> QuestConfig:
        if not self.config:
            self.initialize()
        with self._lock:
            self.config.budget["current_installed_mb"] = installed_mb
            self.config.budget["current_cache_mb"] = cache_mb
            self.config.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return self.config

    def get_config(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return asdict(self.config) if self.config else None

    def get_budget_status(self) -> Dict[str, Any]:
        with self._lock:
            if not self.config:
                return {}
            budget = self.config.budget
            installed_pct = (budget.get("current_installed_mb", 0) / budget.get("max_installed_mb", 4500)) * 100
            cache_pct = (budget.get("current_cache_mb", 0) / budget.get("cache_max_mb", 900)) * 100
            return {
                "installed_mb": budget.get("current_installed_mb", 0),
                "max_installed_mb": budget.get("max_installed_mb", 4500),
                "installed_percent": round(installed_pct, 1),
                "cache_mb": budget.get("current_cache_mb", 0),
                "cache_max_mb": budget.get("cache_max_mb", 900),
                "cache_percent": round(cache_pct, 1),
            }


quest_config = QuestConfigManager()
