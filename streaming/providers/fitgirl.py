#!/usr/bin/env python3
"""
QB Protocol - FitGirl Repacks Scraper
Scrapes game releases from fitgirl-repacks.site
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

LOG = logging.getLogger("qb_protocol.streaming.fitgirl")

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False
    LOG.warning("requests/beautifulsoup4 not installed. FitGirl scraping disabled.")


@dataclass
class FitGirlGame:
    game_id: str
    title: str
    url: str
    repack_size: str
    original_size: str
    release_date: str
    tags: List[str]
    download_links: List[str]
    metadata: Dict[str, Any]
    fetched_at: str


class FitGirlScraper:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_fitgirl.json"):
        self.state_path = state_path
        self.base_url = "https://fitgirl-repacks.site"
        self.games: Dict[str, FitGirlGame] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for gid, g in data.get("games", {}).items():
                        self.games[gid] = FitGirlGame(**g)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "games": {gid: asdict(g) for gid, g in self.games.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        if not HAS_SCRAPING:
            return None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except Exception as e:
            LOG.warning(f"Failed to fetch {url}: {e}")
            return None

    def scrape_page(self, page: int = 1) -> List[FitGirlGame]:
        url = f"{self.base_url}/page/{page}/"
        soup = self._get_soup(url)
        if not soup:
            return []

        games = []
        articles = soup.find_all('article', class_='post')
        if not articles:
            articles = soup.find_all('article')

        for article in articles:
            title_elem = article.find('h1', class_='entry-title') or article.find('h2', class_='entry-title')
            if not title_elem:
                continue
            a = title_elem.find('a', href=True)
            if not a or not a.get('href'):
                continue
            game_url = a['href']
            game = self._scrape_game_page(game_url)
            if game:
                games.append(game)

        return games

    def _scrape_game_page(self, url: str) -> Optional[FitGirlGame]:
        soup = self._get_soup(url)
        if not soup:
            return None

        title = ""
        title_elem = soup.find('h1', class_=re.compile('entry-title|post-title'))
        if title_elem:
            title = title_elem.get_text(strip=True)

        repack_size = ""
        original_size = ""
        size_text = soup.get_text()
        size_match = re.search(r'Repack Size\s*[:]\s*([^\n]+)', size_text, re.IGNORECASE)
        if size_match:
            repack_size = size_match.group(1).strip()
        orig_match = re.search(r'Original Size\s*[:]\s*([^\n]+)', size_text, re.IGNORECASE)
        if orig_match:
            original_size = orig_match.group(1).strip()

        release_date = ""
        date_match = re.search(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', size_text)
        if date_match:
            release_date = date_match.group(1)

        tags = []
        tag_elems = soup.find_all('a', rel='tag')
        for tag in tag_elems:
            tag_text = tag.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)

        download_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(ext in href.lower() for ext in ['.torrent', 'magnet', 'download', 'upload', '1fichier', 'rapidgator', 'zippyshare', 'nitroflare', 'turbobit']):
                download_links.append(href)

        game_id = str(uuid.uuid4())
        game = FitGirlGame(
            game_id=game_id,
            title=title,
            url=url,
            repack_size=repack_size,
            original_size=original_size,
            release_date=release_date,
            tags=tags,
            download_links=list(set(download_links)),
            metadata={"source": "fitgirl-repacks.site"},
            fetched_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.games[game_id] = game
        self._save()
        return game

    def get_latest(self, limit: int = 20) -> List[Dict[str, Any]]:
        games = []
        for page in range(1, 4):
            scraped = self.scrape_page(page)
            games.extend(scraped)
            if len(games) >= limit:
                break
            time.sleep(1)
        with self._lock:
            return [asdict(g) for g in list(self.games.values())[-limit:]]

    def get_games(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(g) for g in list(self.games.values())[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_games": len(self.games),
                "scraping_available": HAS_SCRAPING,
                "base_url": self.base_url,
            }


fitgirl_scraper = FitGirlScraper()
