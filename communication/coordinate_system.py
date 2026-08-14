#!/usr/bin/env python3
"""
QB Protocol - Coordinate System
Tracks designated locations with coordinates for dimensional routing.
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

LOG = logging.getLogger("qb_protocol.communication.coordinates")


@dataclass
class Coordinate:
    coordinate_id: str
    name: str
    latitude: float
    longitude: float
    altitude: Optional[float]
    dimension: str
    timestamp: str
    metadata: Dict[str, Any]


class CoordinateSystem:
    def __init__(self, db_path: Path = Path(__file__).resolve().parent.parent / "qb_protocol_coordinates.json"):
        self.db_path = db_path
        self.coordinates: Dict[str, Coordinate] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for cid, cd in data.get("coordinates", {}).items():
                        self.coordinates[cid] = Coordinate(**cd)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "coordinates": {cid: asdict(c) for cid, c in self.coordinates.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register(self, name: str, latitude: float, longitude: float, altitude: Optional[float] = None, dimension: str = "earth", metadata: Optional[Dict[str, Any]] = None) -> Coordinate:
        coord = Coordinate(
            coordinate_id=str(uuid.uuid4()),
            name=name,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            dimension=dimension,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {},
        )
        with self._lock:
            self.coordinates[coord.coordinate_id] = coord
        self._save()
        return coord

    def get(self, coordinate_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            coord = self.coordinates.get(coordinate_id)
            return asdict(coord) if coord else None

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(c) for c in self.coordinates.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_coordinates": len(self.coordinates),
                "dimensions": list(set(c.dimension for c in self.coordinates.values())),
            }


coordinate_system = CoordinateSystem()
