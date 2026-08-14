#!/usr/bin/env python3
"""
QB Protocol - Icon Generator
Automatic icon generation for OS artifacts and applications.
"""

from __future__ import annotations

import os
import sys
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.icon_generator")


@dataclass
class IconSpec:
    name: str
    size: int
    platform: str
    background_color: str
    foreground_color: str
    shape: str
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedIcon:
    icon_id: str
    spec: Dict[str, Any]
    path: str
    format: str
    size_bytes: int
    checksum: str
    platform: str
    created_at: str


class IconGenerator:
    """Generates icons automatically for OS artifacts and applications."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path.home() / ".qb_protocol_icons"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.icons: Dict[str, GeneratedIcon] = {}
        self._lock = threading.RLock()
        self._load_icons()

    def _load_icons(self):
        index_path = self.output_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, "r") as f:
                    data = json.load(f)
                    for iid, icon in data.get("icons", {}).items():
                        self.icons[iid] = GeneratedIcon(**icon)
            except Exception:
                pass

    def _save_icons(self):
        try:
            index_path = self.output_dir / "index.json"
            with open(index_path, "w") as f:
                json.dump({
                    "icons": {iid: asdict(icon) for iid, icon in self.icons.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def generate_icon(self, spec: IconSpec) -> GeneratedIcon:
        icon_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGBA", (spec.size, spec.size), spec.background_color)
            draw = ImageDraw.Draw(img)

            if spec.shape == "circle":
                draw.ellipse([0, 0, spec.size - 1, spec.size - 1], fill=spec.background_color, outline=spec.foreground_color, width=max(1, spec.size // 16))
            elif spec.shape == "square":
                draw.rectangle([0, 0, spec.size - 1, spec.size - 1], fill=spec.background_color, outline=spec.foreground_color, width=max(1, spec.size // 16))
            elif spec.shape == "rounded":
                radius = spec.size // 4
                self._draw_rounded_rectangle(draw, [0, 0, spec.size - 1, spec.size - 1], radius, fill=spec.background_color, outline=spec.foreground_color, width=max(1, spec.size // 16))

            if spec.text:
                try:
                    font_size = max(8, spec.size // 3)
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), spec.text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (spec.size - text_width) // 2
                y = (spec.size - text_height) // 2
                draw.text((x, y), spec.text, fill=spec.foreground_color, font=font)

            format_ext = "png" if spec.platform in ("macos", "linux") else "ico"
            output_path = self.output_dir / f"{spec.name}_{spec.size}x{spec.size}.{format_ext}"

            if format_ext == "ico":
                img.save(output_path, format="ICO", sizes=[(spec.size, spec.size)])
            else:
                img.save(output_path, format="PNG")

            size_bytes = output_path.stat().st_size
            checksum = hashlib.sha256(output_path.read_bytes()).hexdigest()[:16]

            icon = GeneratedIcon(
                icon_id=icon_id,
                spec=asdict(spec),
                path=str(output_path),
                format=format_ext,
                size_bytes=size_bytes,
                checksum=checksum,
                platform=spec.platform,
                created_at=timestamp,
            )

            with self._lock:
                self.icons[icon_id] = icon
                self._save_icons()

            return icon

        except Exception as e:
            LOG.error("Icon generation failed: %s", e)
            raise

    def _draw_rounded_rectangle(self, draw, bbox, radius, **kwargs):
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], **kwargs)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], **kwargs)
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], **kwargs)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], **kwargs)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], **kwargs)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], **kwargs)

    def generate_app_icon_set(self, app_name: str, base_color: str = "#007AFF", platform: str = "macos") -> List[GeneratedIcon]:
        sizes = [16, 32, 64, 128, 256, 512] if platform == "macos" else [16, 32, 48, 64, 128, 256]
        icons = []
        for size in sizes:
            spec = IconSpec(
                name=app_name,
                size=size,
                platform=platform,
                background_color=base_color,
                foreground_color="#FFFFFF",
                shape="rounded",
                text=app_name[0].upper() if app_name else "A",
                metadata={"app_name": app_name, "size": size},
            )
            icon = self.generate_icon(spec)
            icons.append(icon)
        return icons

    def get_icon(self, icon_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            icon = self.icons.get(icon_id)
            return asdict(icon) if icon else None

    def get_icons(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(icon) for icon in list(self.icons.values())[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_icons": len(self.icons),
                "output_dir": str(self.output_dir),
            }


icon_generator = IconGenerator()
