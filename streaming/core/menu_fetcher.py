#!/usr/bin/env python3
"""
QB Protocol - Menu Fetcher
Web scraper for fetching menu listings from streaming sources like origin-ver.
"""

import os
import time
import uuid
import json
import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.streaming.menu_fetcher")

try:
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False
    LOG.warning("requests/beautifulsoup4 not installed. Menu fetching disabled.")


@dataclass
class MenuItem:
    item_id: str
    name: str
    url: str
    source: str
    category: str
    metadata: Dict[str, Any]
    fetched_at: str


@dataclass
class MenuSource:
    source_id: str
    name: str
    base_url: str
    menu_selector: str
    fallback_selector: str
    enabled: bool
    last_fetched: Optional[str]
    metadata: Dict[str, Any]


class MenuFetcher:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_streaming_menu.json"):
        self.state_path = state_path
        self.sources: Dict[str, MenuSource] = {}
        self.items: List[MenuItem] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("sources", {}).items():
                        self.sources[sid] = MenuSource(**s)
                    self.items = [MenuItem(**i) for i in data.get("items", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "sources": {sid: asdict(s) for sid, s in self.sources.items()},
                    "items": [asdict(i) for i in self.items[-5000:]],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_source(self, name: str, base_url: str, menu_selector: str = "nav", fallback_selector: str = "ul.menu", enabled: bool = True, metadata: Optional[Dict[str, Any]] = None) -> MenuSource:
        source = MenuSource(
            source_id=str(uuid.uuid4()),
            name=name,
            base_url=base_url,
            menu_selector=menu_selector,
            fallback_selector=fallback_selector,
            enabled=enabled,
            last_fetched=None,
            metadata=metadata or {},
        )
        with self._lock:
            self.sources[source.source_id] = source
        self._save()
        return source

    def fetch_menu(self, source_id: str) -> List[MenuItem]:
        with self._lock:
            source = self.sources.get(source_id)
            if not source or not source.enabled or not HAS_SCRAPING:
                return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        try:
            response = requests.get(source.base_url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            LOG.warning(f"Failed to fetch {source.base_url}: {e}")
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        menu_items = []

        menu_container = soup.select_one(source.menu_selector) or soup.select_one(source.fallback_selector) or soup.find('nav') or soup.find('ul', class_='menu')

        if menu_container:
            for link in menu_container.find_all('a', href=True):
                name = link.get_text(strip=True)
                href = link.get('href')
                if not name or not href:
                    continue
                full_url = urljoin(source.base_url, href)
                item = MenuItem(
                    item_id=str(uuid.uuid4()),
                    name=name,
                    url=full_url,
                    source=source.name,
                    category=self._detect_category(name, full_url),
                    metadata={"source_id": source_id},
                    fetched_at=datetime.utcnow().isoformat() + "Z",
                )
                menu_items.append(item)
        else:
            LOG.warning(f"Could not find menu container for {source.name}")

        with self._lock:
            source.last_fetched = datetime.utcnow().isoformat() + "Z"
            self.items.extend(menu_items)
            if len(self.items) > 10000:
                self.items = self.items[-10000:]
        self._save()
        return menu_items

    def _detect_category(self, name: str, url: str) -> str:
        name_lower = name.lower()
        url_lower = url.lower()
        if any(x in name_lower or x in url_lower for x in ["anime", "manga", "naruto", "one piece", "attack on titan"]):
            return "anime"
        if any(x in name_lower or x in url_lower for x in ["movie", "film", "cinema"]):
            return "movie"
        if any(x in name_lower or x in url_lower for x in ["series", "tv", "show", "episode"]):
            return "series"
        if any(x in name_lower or x in url_lower for x in ["live", "stream", "channel"]):
            return "live"
        return "general"

    def get_items(self, category: Optional[str] = None, source: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            items = self.items
            if category:
                items = [i for i in items if i.category == category]
            if source:
                items = [i for i in items if i.source == source]
            return [asdict(i) for i in items[-limit:]]

    def get_sources(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.sources.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sources": len(self.sources),
                "enabled_sources": len([s for s in self.sources.values() if s.enabled]),
                "total_items": len(self.items),
                "scraping_available": HAS_SCRAPING,
            }


menu_fetcher = MenuFetcher()
