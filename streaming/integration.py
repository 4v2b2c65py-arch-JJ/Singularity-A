#!/usr/bin/env python3
"""
QB Protocol - Streaming Integration
Main integration module for the streaming system.
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

LOG = logging.getLogger("qb_protocol.streaming.integration")


class StreamingIntegration:
    def __init__(self, repo_path: Path = Path(".")):
        self.repo_path = Path(repo_path).resolve()
        self._lock = threading.RLock()
        self._catalog = None
        self._menu_fetcher = None
        self._realm_detector = None
        self._layer_detector = None
        self._stream_mapper = None

    def _get_catalog(self):
        if self._catalog is None:
            try:
                from streaming.core.catalog import catalog
                self._catalog = catalog
            except ImportError:
                pass
        return self._catalog

    def _get_menu_fetcher(self):
        if self._menu_fetcher is None:
            try:
                from streaming.core.menu_fetcher import menu_fetcher
                self._menu_fetcher = menu_fetcher
            except ImportError:
                pass
        return self._menu_fetcher

    def _get_realm_detector(self):
        if self._realm_detector is None:
            try:
                from streaming.core.realm import realm_detector
                self._realm_detector = realm_detector
            except ImportError:
                pass
        return self._realm_detector

    def _get_layer_detector(self):
        if self._layer_detector is None:
            try:
                from streaming.core.layer import layer_detector
                self._layer_detector = layer_detector
            except ImportError:
                pass
        return self._layer_detector

    def _get_stream_mapper(self):
        if self._stream_mapper is None:
            try:
                from streaming.core.stream_mapper import stream_mapper
                self._stream_mapper = stream_mapper
            except ImportError:
                pass
        return self._stream_mapper

    def register_realm(self, name: str, realm_type: str = "unknown", description: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        catalog = self._get_catalog()
        if not catalog:
            return {"status": "error", "message": "Catalog module not available"}
        realm = catalog.create_realm(name, realm_type, description, metadata=metadata)
        return {"status": "success", "realm": asdict(realm)}

    def register_stream_source(self, name: str, url: str, realm_id: str, layer_id: str, **kwargs) -> Dict[str, Any]:
        catalog = self._get_catalog()
        if not catalog:
            return {"status": "error", "message": "Catalog module not available"}
        source = catalog.add_stream_source(name, url, realm_id, layer_id, **kwargs)
        return {"status": "success", "source": asdict(source)}

    def fetch_menu_from_source(self, source_id: str) -> Dict[str, Any]:
        menu_fetcher = self._get_menu_fetcher()
        if not menu_fetcher:
            return {"status": "error", "message": "Menu fetcher module not available"}
        items = menu_fetcher.fetch_menu(source_id)
        return {"status": "success", "items": [asdict(i) for i in items], "count": len(items)}

    def detect_realm(self, name: str, url: str, description: str = "") -> Dict[str, Any]:
        detector = self._get_realm_detector()
        if not detector:
            return {"status": "error", "message": "Realm detector module not available"}
        realm = detector.detect_realm(name, url, description)
        return {"status": "success", "realm": asdict(realm)}

    def detect_layer(self, realm_id: str, name: str, url: str, description: str = "") -> Dict[str, Any]:
        detector = self._get_layer_detector()
        if not detector:
            return {"status": "error", "message": "Layer detector module not available"}
        layer = detector.detect_layer(realm_id, name, url, description)
        return {"status": "success", "layer": asdict(layer)}

    def select_stream(self, item_id: str, realm_id: str, layer_id: str, available_sources: List[str], preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        mapper = self._get_stream_mapper()
        if not mapper:
            return {"status": "error", "message": "Stream mapper module not available"}
        mapping = mapper.select_stream(item_id, realm_id, layer_id, available_sources, preferences)
        return {"status": "success", "mapping": asdict(mapping)}

    def get_catalog(self, realm_id: str, layer_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        catalog = self._get_catalog()
        if not catalog:
            return {"status": "error", "message": "Catalog module not available"}
        items = catalog.get_catalog(realm_id, layer_id, limit)
        return {"status": "success", "items": items, "count": len(items)}

    def get_status(self) -> Dict[str, Any]:
        status = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "modules": {},
        }
        catalog = self._get_catalog()
        if catalog:
            status["modules"]["catalog"] = catalog.get_status()
        menu_fetcher = self._get_menu_fetcher()
        if menu_fetcher:
            status["modules"]["menu_fetcher"] = menu_fetcher.get_status()
        realm_detector = self._get_realm_detector()
        if realm_detector:
            status["modules"]["realm_detector"] = realm_detector.get_status()
        layer_detector = self._get_layer_detector()
        if layer_detector:
            status["modules"]["layer_detector"] = layer_detector.get_status()
        stream_mapper = self._get_stream_mapper()
        if stream_mapper:
            status["modules"]["stream_mapper"] = stream_mapper.get_status()
        return status


streaming_integration = StreamingIntegration()
