#!/usr/bin/env python3
"""
QB Protocol - Streaming Catalog
Stremio-like catalog system with realms, layers, and stream sources.
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

LOG = logging.getLogger("qb_protocol.streaming.catalog")


class RealmType(Enum):
    ANIME = "anime"
    MOVIE = "movie"
    SERIES = "series"
    DOCUMENTARY = "documentary"
    LIVE = "live"
    UNKNOWN = "unknown"
    CUSTOM = "custom"


class LayerType(Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CORE = "core"
    UNKNOWN = "unknown"


@dataclass
class Realm:
    realm_id: str
    name: str
    realm_type: str
    description: str
    layers: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class Layer:
    layer_id: str
    realm_id: str
    name: str
    layer_type: str
    depth: int
    streams: List[str]
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class StreamSource:
    source_id: str
    name: str
    url: str
    realm_id: str
    layer_id: str
    stream_type: str
    quality: str
    language: str
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class CatalogItem:
    item_id: str
    title: str
    realm_id: str
    layer_id: str
    stream_sources: List[str]
    poster: str
    backdrop: str
    description: str
    year: int
    rating: float
    genres: List[str]
    metadata: Dict[str, Any]
    created_at: str


class StreamingCatalog:
    def __init__(self, db_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_streaming_catalog.json"):
        self.db_path = db_path
        self.realms: Dict[str, Realm] = {}
        self.layers: Dict[str, Layer] = {}
        self.stream_sources: Dict[str, StreamSource] = {}
        self.catalog_items: Dict[str, CatalogItem] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for rid, r in data.get("realms", {}).items():
                        self.realms[rid] = Realm(**r)
                    for lid, l in data.get("layers", {}).items():
                        self.layers[lid] = Layer(**l)
                    for sid, s in data.get("stream_sources", {}).items():
                        self.stream_sources[sid] = StreamSource(**s)
                    for cid, c in data.get("catalog_items", {}).items():
                        self.catalog_items[cid] = CatalogItem(**c)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "realms": {rid: asdict(r) for rid, r in self.realms.items()},
                    "layers": {lid: asdict(l) for lid, l in self.layers.items()},
                    "stream_sources": {sid: asdict(s) for sid, s in self.stream_sources.items()},
                    "catalog_items": {cid: asdict(c) for cid, c in self.catalog_items.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_realm(self, name: str, realm_type: str = RealmType.UNKNOWN.value, description: str = "", layers: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Realm:
        realm = Realm(
            realm_id=str(uuid.uuid4()),
            name=name,
            realm_type=realm_type,
            description=description,
            layers=layers or [],
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.realms[realm.realm_id] = realm
        self._save()
        return realm

    def create_layer(self, realm_id: str, name: str, layer_type: str = LayerType.SURFACE.value, depth: int = 0, streams: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Layer:
        layer = Layer(
            layer_id=str(uuid.uuid4()),
            realm_id=realm_id,
            name=name,
            layer_type=layer_type,
            depth=depth,
            streams=streams or [],
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.layers[layer.layer_id] = layer
            realm = self.realms.get(realm_id)
            if realm and layer.layer_id not in realm.layers:
                realm.layers.append(layer.layer_id)
                realm.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return layer

    def add_stream_source(self, name: str, url: str, realm_id: str, layer_id: str, stream_type: str = "video", quality: str = "unknown", language: str = "en", metadata: Optional[Dict[str, Any]] = None) -> StreamSource:
        source = StreamSource(
            source_id=str(uuid.uuid4()),
            name=name,
            url=url,
            realm_id=realm_id,
            layer_id=layer_id,
            stream_type=stream_type,
            quality=quality,
            language=language,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.stream_sources[source.source_id] = source
            layer = self.layers.get(layer_id)
            if layer and source.source_id not in layer.streams:
                layer.streams.append(source.source_id)
        self._save()
        return source

    def add_catalog_item(self, title: str, realm_id: str, layer_id: str, stream_sources: Optional[List[str]] = None, poster: str = "", backdrop: str = "", description: str = "", year: int = 0, rating: float = 0.0, genres: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> CatalogItem:
        item = CatalogItem(
            item_id=str(uuid.uuid4()),
            title=title,
            realm_id=realm_id,
            layer_id=layer_id,
            stream_sources=stream_sources or [],
            poster=poster,
            backdrop=backdrop,
            description=description,
            year=year,
            rating=rating,
            genres=genres or [],
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.catalog_items[item.item_id] = item
        self._save()
        return item

    def get_realms(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.realms.values()]

    def get_layers(self, realm_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(l) for l in self.layers.values() if l.realm_id == realm_id]

    def get_stream_sources(self, realm_id: str, layer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            sources = [s for s in self.stream_sources.values() if s.realm_id == realm_id]
            if layer_id:
                sources = [s for s in sources if s.layer_id == layer_id]
            return [asdict(s) for s in sources]

    def get_catalog(self, realm_id: str, layer_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            items = [c for c in self.catalog_items.values() if c.realm_id == realm_id]
            if layer_id:
                items = [c for c in items if c.layer_id == layer_id]
            return [asdict(c) for c in items[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_realms": len(self.realms),
                "total_layers": len(self.layers),
                "total_stream_sources": len(self.stream_sources),
                "total_catalog_items": len(self.catalog_items),
                "realms": list(self.realms.keys()),
            }


catalog = StreamingCatalog()
