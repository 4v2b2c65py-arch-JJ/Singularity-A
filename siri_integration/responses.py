#!/usr/bin/env python3
"""
QB Protocol - Siri Response Layer
Version: 1.0.0
Release: Production Build - Conversation Model + Cloud Store + Offline Fallback

This is the shipped response stack:
- Tier 1: Cloud-backed response store for system intents (execute, control, reminder, image, sleep, learn, private)
- Tier 2: Local conversation model for chat intent and unknown utterances
- Tier 3: Hardcoded safety fallbacks that never fail

The model is the primary conversational path. The store prevents model drift on system actions.
Offline mode works because store + fallbacks are local-only.
"""

import os
import re
import json
import time
import tempfile
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

LOG = logging.getLogger("qb_protocol.siri_integration.responses")

SIRI_RESPONSES_VERSION = "1.0.0"
SIRI_RESPONSES_S3_BUCKET = os.environ.get("SIRI_RESPONSES_S3_BUCKET", "")
SIRI_RESPONSES_S3_KEY = os.environ.get("SIRI_RESPONSES_S3_KEY", "siri/responses.json")
SIRI_RESPONSES_LOCAL = Path(os.environ.get("SIRI_RESPONSES_LOCAL", str(Path.home() / ".qb_protocol_siri_responses.json")))

DEFAULT_RESPONSES: Dict[str, Dict[str, Any]] = {
    "execute": {
        "text": "Executing your request now.",
        "spoken": "I'll execute that for you now.",
        "action": {
            "type": "execute",
            "backend": "agent",
        },
        "display": "▶️ Executing",
        "continue_session": False,
    },
    "chat": {
        "text": "I'm on it.",
        "spoken": "Let me handle that.",
        "action": {
            "type": "chat",
            "backend": "agent",
        },
        "display": "💬 Responding",
        "continue_session": True,
    },
    "reminder": {
        "text": "Reminder saved.",
        "spoken": "Reminder created.",
        "action": {
            "type": "reminder",
        },
        "display": "⏰ Reminder",
        "continue_session": False,
    },
    "control": {
        "text": "Adjusting now.",
        "spoken": "Controlling that for you.",
        "action": {
            "type": "device_control",
            "requires_auth": True,
        },
        "display": "🎛️ Control",
        "continue_session": False,
    },
    "private": {
        "text": "Private mode active.",
        "spoken": "Private mode is now active. Your data stays on your device.",
        "action": {
            "type": "private_mode",
            "cloud_sync": False,
            "local_only": True,
        },
        "display": "🔒 Private Mode",
        "continue_session": True,
    },
    "image": {
        "text": "Creating that privately.",
        "spoken": "Creating that image for you privately.",
        "action": {
            "type": "generate_image",
            "private": True,
            "cloud": "icloud",
        },
        "display": "🎨 Generating",
        "continue_session": True,
    },
    "sleep": {
        "text": "Sleep mode on.",
        "spoken": "I'll run quietly in the background.",
        "action": {
            "type": "sleep_mode",
            "screen_off": True,
            "background_only": True,
        },
        "display": "😴 Sleep Mode",
        "continue_session": False,
    },
    "learn": {
        "text": "Got it, I'll remember.",
        "spoken": "I'll remember that.",
        "action": {
            "type": "learn",
            "adaptive": True,
        },
        "display": "🧠 Learning",
        "continue_session": True,
    },
    "fallback": {
        "text": "Processing your request.",
        "spoken": "Processing.",
        "action": None,
        "display": "⚙️ Processing",
        "continue_session": False,
    },
}


def _normalize(value: Any, default: str = "") -> str:
    if isinstance(value, dict):
        return _normalize(value.get("text", value.get("content", list(value.values())[0] if value else default)), default)
    if isinstance(value, list):
        return _normalize(value[0], default) if value else default
    return str(value) if value is not None else default


def _validate_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return DEFAULT_RESPONSES["fallback"]
    text = _normalize(data.get("text"), "")
    spoken = _normalize(data.get("spoken"), "")
    action = data.get("action") if isinstance(data.get("action"), dict) else None
    display = _normalize(data.get("display"), "")
    continue_session = bool(data.get("continue_session", False))
    if not text and not spoken:
        text = "Processing your request."
        spoken = "Processing."
    return {
        "text": text[:500],
        "spoken": spoken[:500],
        "action": action,
        "display": display[:120] if display else "⚙️ Processing",
        "continue_session": continue_session,
    }


class SiriResponseStore:
    """Cloud-backed response store with local cache for system intents."""

    def __init__(self, local_path: Optional[Path] = None):
        self.local_path = local_path or SIRI_RESPONSES_LOCAL
        self.responses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        with self._lock:
            self.responses = dict(DEFAULT_RESPONSES)
            if self.local_path.exists():
                try:
                    with open(self.local_path, "r") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self.responses.update(data)
                    LOG.info("Loaded Siri responses from %s", self.local_path)
                except Exception as exc:
                    LOG.warning("Failed to load Siri responses: %s", exc)

    def _download_from_s3(self) -> Optional[Path]:
        if not SIRI_RESPONSES_S3_BUCKET:
            return None
        try:
            import boto3
            from botocore.client import Config

            target = Path(tempfile.gettempdir()) / "qb_siri_responses.json"
            LOG.info("Downloading Siri responses from S3: %s/%s", SIRI_RESPONSES_S3_BUCKET, SIRI_RESPONSES_S3_KEY)
            s3 = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
                endpoint_url=os.environ.get("AWS_ENDPOINT_URL", ""),
                config=Config(signature_version="s3v4"),
            )
            s3.download_file(SIRI_RESPONSES_S3_BUCKET, SIRI_RESPONSES_S3_KEY, str(target))
            LOG.info("Downloaded Siri responses to %s", target)
            return target
        except Exception as exc:
            LOG.warning("S3 download failed: %s", exc)
            return None

    def sync_from_cloud(self) -> bool:
        downloaded = self._download_from_s3()
        if downloaded and downloaded.exists():
            try:
                with open(downloaded, "r") as f:
                    data = json.load(f)
                with self._lock:
                    if isinstance(data, dict):
                        self.responses.update(data)
                        with open(self.local_path, "w") as f:
                            json.dump(self.responses, f, indent=2)
                LOG.info("Synced Siri responses from cloud")
                return True
            except Exception as exc:
                LOG.warning("Cloud sync failed: %s", exc)
        return False

    def get_response(self, intent: str, utterance: str = "") -> Optional[Dict[str, Any]]:
        key = intent if intent in self.responses else None
        if not key:
            return None
        data = dict(self.responses[key])
        if intent == "execute" and utterance:
            data.setdefault("action", {}).setdefault("command", utterance)
            data.setdefault("text", f"Executing: {utterance}")
            data.setdefault("spoken", "I'll execute that for you now.")
            data.setdefault("display", f"▶️ Executing: {utterance[:50]}")
        elif intent == "chat" and utterance:
            data.setdefault("action", {}).setdefault("prompt", utterance)
            data.setdefault("text", f"AI Response: {utterance}")
            data.setdefault("spoken", "Let me think about that.")
            data.setdefault("display", f"💬 {utterance[:50]}")
        elif intent == "reminder" and utterance:
            data.setdefault("action", {}).setdefault("text", utterance)
            data.setdefault("text", f"Reminder set: {utterance}")
            data.setdefault("spoken", "Reminder created.")
            data.setdefault("display", f"⏰ {utterance[:50]}")
        elif intent == "control" and utterance:
            data.setdefault("action", {}).setdefault("command", utterance)
            data.setdefault("text", f"Device control: {utterance}")
            data.setdefault("spoken", "Controlling device.")
            data.setdefault("display", f"🎛️ {utterance[:50]}")
        elif intent == "image" and utterance:
            data.setdefault("action", {}).setdefault("prompt", utterance)
            data.setdefault("text", f"Generating image: {utterance}")
            data.setdefault("spoken", "Creating that image for you privately.")
            data.setdefault("display", f"🎨 Generating: {utterance[:50]}")
        elif intent == "learn" and utterance:
            data.setdefault("action", {}).setdefault("data", utterance)
            data.setdefault("text", f"Learning: {utterance}")
            data.setdefault("spoken", "I'll remember that.")
            data.setdefault("display", f"🧠 Learning: {utterance[:50]}")
        return _validate_response(data)


class SiriConversationModel:
    """Local conversation model for chat and unknown intents."""

    def __init__(self):
        self._model = None
        self._model_backend = None
        self._load_attempted = False
        self._load_lock = threading.Lock()

    def _ensure_loaded(self):
        if self._model is not None or self._load_attempted:
            return
        with self._load_lock:
            if self._model is not None or self._load_attempted:
                return
            self._load_attempted = True
            try:
                try:
                    from qb_protocol.ai.gpt_layer import gpt_layer
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
                    from ai.gpt_layer import gpt_layer
                self._model = gpt_layer
                self._model_backend = getattr(gpt_layer, "model_backend", None)
                LOG.info("Conversation model loaded: %s", self._model_backend)
            except Exception as exc:
                LOG.warning("Conversation model load failed: %s", exc)

    def chat(self, utterance: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate conversational response for chat intent."""
        self._ensure_loaded()
        if not self._model:
            return {}

        context = context or {}
        context_json = json.dumps(context)[:200]
        prompt = (
            "You are Siri for QB Protocol. "
            "Reply conversationally in one short sentence. "
            f"User: \"{utterance}\". Context: {context_json}. "
            "Do not use JSON. Do not use markdown. Just plain text."
        )

        try:
            result = self._model.query(prompt, max_tokens=64, temperature=0.75)
            raw = result.get("response", "") if isinstance(result, dict) else str(result)
            text = raw.strip()
            text = re.sub(r"^```.*?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()
            if not text:
                return {}
            return _validate_response({
                "text": text,
                "spoken": text,
                "display": f"💬 {text[:100]}",
                "continue_session": True,
            })
        except Exception as exc:
            LOG.warning("Conversation model chat failed: %s", exc)
        return {}

    def get_status(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return {
            "loaded": self._model is not None,
            "backend": self._model_backend,
            "version": SIRI_RESPONSES_VERSION,
        }


siri_response_store = SiriResponseStore()
siri_conversation_model = SiriConversationModel()
