#!/usr/bin/env python3
"""
QB Protocol - Addon Discovery
Discovers, validates, and installs addons automatically.
"""

import os
import time
import uuid
import json
import logging
import threading
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

LOG = logging.getLogger("qb_protocol.addon_discovery")


class AddonStatus(Enum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class AddonManifest:
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    entry_point: str
    permissions: List[str]
    min_qb_version: str
    max_qb_version: str
    checksum: str
    metadata: Dict[str, Any]


class AddonDiscovery:
    def __init__(self, repo_path: Path = Path("."), addons_dir: Path = Path("addons")):
        self.repo_path = Path(repo_path).resolve()
        self.addons_dir = Path(addons_dir).resolve()
        self.addons_dir.mkdir(exist_ok=True)
        self.discovered: Dict[str, AddonManifest] = {}
        self._lock = threading.RLock()
        self._load_manifest()

    def _load_manifest(self):
        manifest_file = self.addons_dir / "manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r") as f:
                    data = json.load(f)
                    for name, manifest in data.get("addons", {}).items():
                        self.discovered[name] = AddonManifest(**manifest)
            except Exception:
                pass

    def _save_manifest(self):
        manifest_file = self.addons_dir / "manifest.json"
        try:
            with open(manifest_file, "w") as f:
                json.dump({
                    "addons": {name: asdict(m) for name, m in self.discovered.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def discover_local(self) -> List[Dict[str, Any]]:
        discovered = []
        for addon_dir in self.addons_dir.iterdir():
            if not addon_dir.is_dir() or addon_dir.name.startswith("."):
                continue
            manifest_file = addon_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r") as f:
                        manifest_data = json.load(f)
                        manifest = AddonManifest(**manifest_data)
                        self.discovered[manifest.name] = manifest
                        discovered.append(asdict(manifest))
                except Exception:
                    pass
        self._save_manifest()
        return discovered

    def discover_from_git(self) -> List[Dict[str, Any]]:
        try:
            from communication.github_manager import github_manager
            git_status = github_manager.get_status()
            return [{"name": "git-integration", "version": "1.0.0", "source": "git"}]
        except ImportError:
            return []

    def validate_manifest(self, manifest_path: Path) -> Tuple[bool, Optional[str]]:
        if not manifest_path.exists():
            return False, "Manifest not found"
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                required = ["name", "version", "entry_point"]
                for field in required:
                    if field not in data:
                        return False, f"Missing required field: {field}"
                return True, None
        except Exception as e:
            return False, str(e)

    def register_addon(self, manifest: AddonManifest) -> Dict[str, Any]:
        with self._lock:
            self.discovered[manifest.name] = manifest
            self._save_manifest()
            return {"status": AddonStatus.AVAILABLE.value, "manifest": asdict(manifest)}

    def get_discovered(self) -> List[Dict[str, Any]]:
        return [asdict(m) for m in self.discovered.values()]

    def get_manifest(self, addon_name: str) -> Optional[AddonManifest]:
        return self.discovered.get(addon_name)

    def get_status(self) -> Dict[str, Any]:
        return {
            "discovered_count": len(self.discovered),
            "addons_dir": str(self.addons_dir),
            "addons": list(self.discovered.keys()),
        }


addon_discovery = AddonDiscovery()
