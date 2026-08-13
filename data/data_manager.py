#!/usr/bin/env python3
"""
QB Protocol - Data Management
Backup, migration, retention, and integrity for persisted state files.
"""

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

QB_DATA_DIR = Path(__file__).resolve().parent.parent / "qb_data"
QB_DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = QB_DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DataManifest:
    manifest_id: str
    source_path: str
    backup_path: str
    size_bytes: int
    sha256: str
    created_at: str
    retention_days: int
    metadata: Dict[str, Any]


class DataManager:
    def __init__(self, backup_dir: Path = BACKUP_DIR):
        self.backup_dir = backup_dir
        self.manifests: Dict[str, DataManifest] = {}
        self._load_manifests()

    def _load_manifests(self):
        manifest_file = self.backup_dir / "manifests.json"
        if manifest_file.exists():
            with open(manifest_file, "r") as f:
                data = json.load(f)
                for mid, md in data.get("manifests", {}).items():
                    self.manifests[mid] = DataManifest(**md)

    def _save_manifests(self):
        manifest_file = self.backup_dir / "manifests.json"
        with open(manifest_file, "w") as f:
            json.dump({"manifests": {mid: asdict(m) for mid, m in self.manifests.items()}}, f, indent=2)

    def backup_file(self, source: Path, retention_days: int = 7, metadata: Optional[Dict[str, Any]] = None) -> Optional[DataManifest]:
        if not source.exists():
            return None
        manifest_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        backup_name = f"{source.stem}_{int(time.time())}{source.suffix}"
        backup_path = self.backup_dir / backup_name
        try:
            shutil.copy2(source, backup_path)
            sha256 = hashlib.sha256(backup_path.read_bytes()).hexdigest()[:32]
            manifest = DataManifest(
                manifest_id=manifest_id,
                source_path=str(source),
                backup_path=str(backup_path),
                size_bytes=backup_path.stat().st_size,
                sha256=sha256,
                created_at=now,
                retention_days=retention_days,
                metadata=metadata or {},
            )
            self.manifests[manifest_id] = manifest
            self._save_manifests()
            return manifest
        except Exception:
            return None

    def enforce_retention(self):
        cutoff = time.time() - (7 * 24 * 60 * 60)
        expired = []
        for mid, manifest in list(self.manifests.items()):
            try:
                created = datetime.fromisoformat(manifest.created_at.replace("Z", "+00:00")).timestamp()
                if created < cutoff:
                    path = Path(manifest.backup_path)
                    if path.exists():
                        path.unlink()
                    expired.append(mid)
            except Exception:
                pass
        for mid in expired:
            del self.manifests[mid]
        if expired:
            self._save_manifests()
        return {"expired": len(expired)}

    def get_backup_status(self) -> Dict[str, Any]:
        total_size = sum(m.size_bytes for m in self.manifests.values())
        return {
            "backup_count": len(self.manifests),
            "total_backup_size_bytes": total_size,
            "backup_dir": str(self.backup_dir),
        }


data_manager = DataManager()
