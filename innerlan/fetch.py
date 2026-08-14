#!/usr/bin/env python3
"""
QB Protocol - Innerlan Fetch
High-level fetch layer via GPT model integration.
"""

from __future__ import annotations

import os
import time
import uuid
import json
import logging
import threading
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.innerlan.fetch")


@dataclass
class FetchRequest:
    request_id: str
    source: str
    query: str
    mode: str
    context: Dict[str, Any]
    max_tokens: int
    temperature: float
    timestamp: str


@dataclass
class FetchResponse:
    request_id: str
    source: str
    mode: str
    raw: str
    enhanced: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int
    cached: bool
    timestamp: str


class InnerlanFetch:
    def __init__(self):
        self.requests: List[FetchRequest] = []
        self.responses: List[FetchResponse] = []
        self._cache: Dict[str, FetchResponse] = {}
        self._lock = threading.RLock()
        self._start_time = time.time()

    def fetch(self, source: str, query: str, mode: str = "gpt_enhanced", context: Optional[Dict[str, Any]] = None, max_tokens: int = 256, temperature: float = 0.7) -> FetchResponse:
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        context = context or {}

        cache_key = hashlib.sha256(f"{source}:{query}:{mode}".encode()).hexdigest()[:16]
        with self._lock:
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                cached.cached = True
                self.responses.append(cached)
                if len(self.responses) > 10000:
                    self.responses = self.responses[-10000:]
                return cached

        request = FetchRequest(
            request_id=request_id,
            source=source,
            query=query,
            mode=mode,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            timestamp=timestamp,
        )
        with self._lock:
            self.requests.append(request)
            if len(self.requests) > 10000:
                self.requests = self.requests[-10000:]

        start = time.time()
        raw = self._raw_fetch(source, query, context)
        enhanced = self._enhance_with_gpt(raw, query, mode, max_tokens, temperature)
        latency = (time.time() - start) * 1000

        model = "unknown"
        provider = "unknown"
        tokens_used = len(query.split()) + len(enhanced.split())

        try:
            from qb_protocol.ai.gpt_layer import gpt_layer
            status = gpt_layer.get_status()
            model = status.get("model_path", "tinyllama-1.1b-chat-v1.0")
            provider = status.get("model_backend", "simulated")
        except Exception:
            pass

        response = FetchResponse(
            request_id=request_id,
            source=source,
            mode=mode,
            raw=raw,
            enhanced=enhanced,
            model=model,
            provider=provider,
            latency_ms=latency,
            tokens_used=tokens_used,
            cached=False,
            timestamp=timestamp,
        )
        with self._lock:
            self._cache[cache_key] = response
            self.responses.append(response)
            if len(self.responses) > 10000:
                self.responses = self.responses[-10000:]

        return response

    def _raw_fetch(self, source: str, query: str, context: Dict[str, Any]) -> str:
        if source.startswith("http://") or source.startswith("https://"):
            return self._fetch_url(source, query, context)
        elif source.startswith("file://"):
            return self._fetch_file(source[7:], query, context)
        elif source.startswith("env://"):
            return self._fetch_env(source[6:], query, context)
        elif source.startswith("shell://"):
            return self._fetch_shell(source[7:], query, context)
        else:
            return json.dumps({"source": source, "query": query, "context": context})

    def _fetch_url(self, url: str, query: str, context: Dict[str, Any]) -> str:
        try:
            import requests
            headers = {
                "User-Agent": "QB-Protocol-Innerlan-Fetch/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            timeout = context.get("timeout", 10)
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            text = response.text
            if context.get("strip_html", True):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, "html.parser")
                    text = soup.get_text(separator=" ", strip=True)
                except Exception:
                    pass
            max_chars = context.get("max_chars", 8000)
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            return text
        except Exception as e:
            return f"FETCH_ERROR: {str(e)}"

    def _fetch_file(self, path: str, query: str, context: Dict[str, Any]) -> str:
        try:
            file_path = Path(path).expanduser().resolve()
            if not file_path.exists():
                return f"FILE_NOT_FOUND: {path}"
            text = file_path.read_text(encoding="utf-8", errors="replace")
            max_chars = context.get("max_chars", 8000)
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            return text
        except Exception as e:
            return f"FILE_ERROR: {str(e)}"

    def _fetch_env(self, key: str, query: str, context: Dict[str, Any]) -> str:
        value = os.environ.get(key, "")
        if not value:
            return f"ENV_NOT_SET: {key}"
        return value

    def _fetch_shell(self, command: str, query: str, context: Dict[str, Any]) -> str:
        try:
            import subprocess
            timeout = context.get("timeout", 10)
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            if result.stderr.strip():
                output += "\nSTDERR:\n" + result.stderr.strip()
            max_chars = context.get("max_chars", 8000)
            if len(output) > max_chars:
                output = output[:max_chars] + "..."
            return output
        except Exception as e:
            return f"SHELL_ERROR: {str(e)}"

    def _enhance_with_gpt(self, raw: str, query: str, mode: str, max_tokens: int, temperature: float) -> str:
        if mode == "raw":
            return raw
        elif mode == "gpt_enhanced":
            return self._gpt_enhance(raw, query, max_tokens, temperature)
        elif mode == "summarize":
            return self._gpt_summarize(raw, query, max_tokens, temperature)
        elif mode == "extract":
            return self._gpt_extract(raw, query, max_tokens, temperature)
        else:
            return raw

    def _gpt_enhance(self, raw: str, query: str, max_tokens: int, temperature: float) -> str:
        try:
            from qb_protocol.ai.gpt_layer import gpt_layer
            prompt = (
                "You are Innerlan, a high-level fetch integration layer.\n"
                "Enhance the following raw fetched content based on the user query.\n"
                "Return only the enhanced content, no explanations.\n\n"
                f"Query: {query}\n\n"
                f"Raw fetched content:\n{raw[:4000]}\n\n"
                "Enhanced response:"
            )
            result = gpt_layer.query(prompt, max_tokens=max_tokens, temperature=temperature)
            return result.get("response", raw)
        except Exception as e:
            LOG.warning("GPT enhancement failed: %s", e)
            return raw

    def _gpt_summarize(self, raw: str, query: str, max_tokens: int, temperature: float) -> str:
        try:
            from qb_protocol.ai.gpt_layer import gpt_layer
            prompt = (
                "You are Innerlan, a high-level fetch integration layer.\n"
                "Summarize the following fetched content concisely.\n"
                "Return only the summary, no explanations.\n\n"
                f"Query: {query}\n\n"
                f"Content:\n{raw[:4000]}\n\n"
                "Summary:"
            )
            result = gpt_layer.query(prompt, max_tokens=max_tokens, temperature=temperature)
            return result.get("response", raw)
        except Exception as e:
            LOG.warning("GPT summarization failed: %s", e)
            return raw

    def _gpt_extract(self, raw: str, query: str, max_tokens: int, temperature: float) -> str:
        try:
            from qb_protocol.ai.gpt_layer import gpt_layer
            prompt = (
                "You are Innerlan, a high-level fetch integration layer.\n"
                "Extract the most relevant information from the fetched content that answers the query.\n"
                "Return only the extracted information, no explanations.\n\n"
                f"Query: {query}\n\n"
                f"Content:\n{raw[:4000]}\n\n"
                "Extracted information:"
            )
            result = gpt_layer.query(prompt, max_tokens=max_tokens, temperature=temperature)
            return result.get("response", raw)
        except Exception as e:
            LOG.warning("GPT extraction failed: %s", e)
            return raw

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_requests": len(self.requests),
                "total_responses": len(self.responses),
                "cache_size": len(self._cache),
                "uptime_seconds": time.time() - self._start_time,
            }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.responses[-limit:]]


innerlan_fetch = InnerlanFetch()
