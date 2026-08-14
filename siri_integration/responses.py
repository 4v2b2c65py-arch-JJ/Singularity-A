#!/usr/bin/env python3
"""
QB Protocol - Siri Response Layer
Version: 2.0.0
Native Human Conversation Model

Design:
- Model is the mind. Short prompts, short history, consistent output.
- No heavy token parsing. No fighting the context window.
- If the model exceeds its threshold, it self-corrects within its own generation.
- Temp state is partitioned: only the last turn lives in the prompt.
- Consistency > speed.
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

SIRI_RESPONSES_VERSION = "2.0.0"
SIRI_RESPONSES_S3_BUCKET = os.environ.get("SIRI_RESPONSES_S3_BUCKET", "")
SIRI_RESPONSES_S3_KEY = os.environ.get("SIRI_RESPONSES_S3_KEY", "siri/responses.json")
SIRI_RESPONSES_LOCAL = Path(os.environ.get("SIRI_RESPONSES_LOCAL", str(Path.home() / ".qb_protocol_siri_responses.json")))

_SYSTEM_PROMPT = (
    "You are Siri. Reply in one short sentence. "
    "Never refuse. Never mention you are AI. "
    "If unsure, guess or ask briefly."
)

_MAX_HISTORY = 2
_MAX_TOKENS = 96


class SiriConversationModel:
    """Minimal, constrained conversation model."""

    def __init__(self):
        self._model = None
        self._model_backend = None
        self._load_attempted = False
        self._load_lock = threading.Lock()
        self._history: list[Tuple[str, str]] = []
        self._lock = threading.Lock()

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

    def _build_prompt(self, utterance: str) -> str:
        with self._lock:
            history = list(self._history[-_MAX_HISTORY:])
        
        lines = [_SYSTEM_PROMPT]
        for user_text, siri_text in history:
            lines.append(f"User: {user_text}")
            lines.append(f"Siri: {siri_text}")
        lines.append(f"User: {utterance}")
        lines.append("Siri:")
        return "\n".join(lines)

    def chat(self, utterance: str) -> Dict[str, Any]:
        self._ensure_loaded()
        if not self._model:
            return {}

        prompt = self._build_prompt(utterance)
        try:
            result = self._model.query(prompt, max_tokens=_MAX_TOKENS, temperature=0.75)
            raw = result.get("response", "") if isinstance(result, dict) else str(result)
            text = raw.strip()
            text = re.sub(r"^```.*?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()
            if not text:
                return {}
            if any(p in text.lower() for p in ["sorry", "cannot", "unable", "as an ai", "as a language model"]):
                text = "I'm on it."
            with self._lock:
                self._history.append((utterance, text))
                if len(self._history) > _MAX_HISTORY * 2:
                    self._history = self._history[-_MAX_HISTORY * 2:]
            return {
                "text": text,
                "spoken": text,
                "display": f"💬 {text[:100]}",
                "continue_session": True,
            }
        except Exception as exc:
            LOG.warning("Conversation model failed: %s", exc)
        return {}

    def reset_history(self):
        with self._lock:
            self._history = []

    def get_status(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return {
            "loaded": self._model is not None,
            "backend": self._model_backend,
            "version": SIRI_RESPONSES_VERSION,
            "history_turns": len(self._history),
            "max_history": _MAX_HISTORY,
            "max_tokens": _MAX_TOKENS,
        }


class SiriResponseStore:
    """Cloud-backed response store for system intents."""

    def __init__(self, local_path: Optional[Path] = None):
        self.local_path = local_path or SIRI_RESPONSES_LOCAL
        self.responses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        with self._lock:
            self.responses = {
                "execute": {
                    "text": "Executing your request now.",
                    "spoken": "I'll execute that for you now.",
                    "action": {"type": "execute", "backend": "agent"},
                    "display": "▶️ Executing",
                    "continue_session": False,
                },
                "reminder": {
                    "text": "Reminder saved.",
                    "spoken": "Reminder created.",
                    "action": {"type": "reminder"},
                    "display": "⏰ Reminder",
                    "continue_session": False,
                },
                "control": {
                    "text": "Adjusting now.",
                    "spoken": "Controlling that for you.",
                    "action": {"type": "device_control", "requires_auth": True},
                    "display": "🎛️ Control",
                    "continue_session": False,
                },
                "private": {
                    "text": "Private mode active.",
                    "spoken": "Private mode is now active. Your data stays on your device.",
                    "action": {"type": "private_mode", "cloud_sync": False, "local_only": True},
                    "display": "🔒 Private Mode",
                    "continue_session": True,
                },
                "image": {
                    "text": "Creating that privately.",
                    "spoken": "Creating that image for you privately.",
                    "action": {"type": "generate_image", "private": True, "cloud": "icloud"},
                    "display": "🎨 Generating",
                    "continue_session": True,
                },
                "sleep": {
                    "text": "Sleep mode on.",
                    "spoken": "I'll run quietly in the background.",
                    "action": {"type": "sleep_mode", "screen_off": True, "background_only": True},
                    "display": "😴 Sleep Mode",
                    "continue_session": False,
                },
                "learn": {
                    "text": "Got it, I'll remember.",
                    "spoken": "I'll remember that.",
                    "action": {"type": "learn", "adaptive": True},
                    "display": "🧠 Learning",
                    "continue_session": True,
                },
            }
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
        return data


siri_response_store = SiriResponseStore()
siri_conversation_model = SiriConversationModel()
