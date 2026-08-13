#!/usr/bin/env python3
"""
QB Protocol - AI Mode GPT Layer
TinyLlama-1.1B-Chat via llama-cpp-python with S3 model storage.
Falls back to simulated mode if model unavailable.
"""

import os
import time
import uuid
import logging
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon

LOG = logging.getLogger("qb_protocol.ai")
AI_ENABLED = os.environ.get("AI_MODE_ENABLED", "false").lower() == "true"
AI_MODEL_PROVIDER = os.environ.get("AI_MODEL_PROVIDER", "local")
AI_MODEL_PATH = os.environ.get("AI_MODEL_PATH", "")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "")
HF_NAMESPACE = os.environ.get("HF_NAMESPACE", "lostinArt")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
TINYLLAMA_MODEL = os.environ.get("TINYLLAMA_MODEL", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")


@dataclass
class AIQuery:
    query_id: str
    prompt: str
    response: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int
    timestamp: str


class GPTLayer:
    def __init__(self):
        self.model = None
        self.model_path = None
        self.model_backend = None
        self.queries: List[AIQuery] = []
        self.start_time = time.time()
        self._load_attempted = False
        self._load_lock = threading.Lock()

    def _load_model(self):
        if not AI_ENABLED:
            LOG.info("AI mode disabled")
            return
        try:
            local_path = Path(AI_MODEL_PATH)
            if not local_path.exists():
                if AI_MODEL_PROVIDER == "s3":
                    local_path = self._download_from_s3()
                elif AI_MODEL_PROVIDER == "hf":
                    local_path = self._download_from_hf()
                else:
                    LOG.warning("AI model not found at %s", local_path)
                    return
            if local_path and local_path.exists():
                try:
                    from llama_cpp import Llama
                    self.model = Llama(model_path=str(local_path), n_ctx=2048, n_threads=4)
                    self.model_path = str(local_path)
                    self.model_backend = "llama-cpp"
                    LOG.info("Loaded TinyLlama model via llama-cpp-python from %s", local_path)
                except Exception as e1:
                    LOG.warning("llama-cpp-python load failed: %s", e1)
                    try:
                        from ctransformers import AutoModelForCausalLM
                        self.model = AutoModelForCausalLM.from_pretrained(str(local_path.parent), model_file=local_path.name, model_type="llama")
                        self.model_path = str(local_path)
                        self.model_backend = "ctransformers"
                        LOG.info("Loaded TinyLlama model via ctransformers from %s", local_path)
                    except Exception as e2:
                        LOG.warning("ctransformers load failed: %s", e2)
                        self.model = None
                        self.model_backend = None
        except Exception as e:
            LOG.warning("Model load failed: %s", e)
            self.model = None
            self.model_backend = None

    def _download_from_s3(self) -> Optional[Path]:
        try:
            import boto3
            from botocore.client import Config
            
            s3_key = f"models/{HF_NAMESPACE}/{TINYLLAMA_MODEL}"
            local_path = Path(tempfile.gettempdir()) / TINYLLAMA_MODEL
            
            if local_path.exists():
                return local_path
            
            LOG.info("Downloading model from S3: %s", s3_key)
            s3 = boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                endpoint_url=AWS_ENDPOINT_URL,
                config=Config(signature_version="s3v4"),
            )
            bucket = "lostinArt"
            s3.download_file(bucket, s3_key, str(local_path))
            LOG.info("Downloaded model to %s", local_path)
            return local_path
        except Exception as e:
            LOG.warning("S3 download failed: %s", e)
            return None

    def _download_from_hf(self) -> Optional[Path]:
        try:
            from huggingface_hub import hf_hub_download
            
            repo_id = AI_MODEL_PATH
            filename = TINYLLAMA_MODEL
            local_path = Path(tempfile.gettempdir()) / filename
            
            if local_path.exists():
                return local_path
            
            LOG.info("Downloading model from HF Hub: %s/%s", repo_id, filename)
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                token=HF_TOKEN,
                local_dir=str(local_path.parent),
                local_dir_use_symlinks=False,
            )
            result = Path(downloaded)
            LOG.info("Downloaded model to %s", result)
            return result
        except Exception as e:
            LOG.warning("HF Hub download failed: %s", e)
            return None

    def _ensure_model_loaded(self):
        if self.model is not None or self._load_attempted:
            return
        with self._load_lock:
            if self.model is not None or self._load_attempted:
                return
            self._load_attempted = True
            self._load_model()

    def query(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> Dict[str, Any]:
        self._ensure_model_loaded()
        query_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if not self.model:
            response = self._simulated_response(prompt)
            query = AIQuery(
                query_id=query_id,
                prompt=prompt,
                response=response,
                model="tinyllama-1.1b-chat-simulated",
                provider="simulated",
                latency_ms=0.0,
                tokens_used=len(prompt.split()) + len(response.split()),
                timestamp=timestamp,
            )
            self.queries.append(query)
            if len(self.queries) > 10000:
                self.queries = self.queries[-10000:]
            return {
                "query_id": query_id,
                "prompt": prompt,
                "response": response,
                "model": "tinyllama-1.1b-chat-simulated",
                "provider": "simulated",
                "tokens_used": query.tokens_used,
                "timestamp": timestamp,
            }
        
        try:
            start = time.time()
            formatted_prompt = f"<|system|>\nYou are a helpful assistant.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
            backend = getattr(self, 'model_backend', None)
            if backend == "llama-cpp":
                result = self.model(
                    formatted_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["</s>"],
                )
                latency = (time.time() - start) * 1000
                response_text = result["choices"][0]["text"].strip()
                tokens = result.get("usage", {}).get("total_tokens", len(prompt.split()) + len(response_text.split()))
                provider = "llama-cpp"
            elif backend == "ctransformers":
                response_text = self.model(formatted_prompt, max_new_tokens=max_tokens, temperature=temperature, stop=["</s>"])
                latency = (time.time() - start) * 1000
                tokens = len(prompt.split()) + len(response_text.split())
                provider = "ctransformers"
            else:
                raise RuntimeError("No LLM backend loaded")
            
            query = AIQuery(
                query_id=query_id,
                prompt=prompt,
                response=response_text,
                model="tinyllama-1.1b-chat-v1.0",
                provider=provider,
                latency_ms=latency,
                tokens_used=tokens,
                timestamp=timestamp,
            )
            self.queries.append(query)
            if len(self.queries) > 10000:
                self.queries = self.queries[-10000:]
            
            return {
                "query_id": query_id,
                "prompt": prompt,
                "response": response_text,
                "model": "tinyllama-1.1b-chat-v1.0",
                "provider": provider,
                "latency_ms": latency,
                "tokens_used": tokens,
                "timestamp": timestamp,
            }
        except Exception as e:
            LOG.error("AI query failed: %s", e)
            return {
                "query_id": query_id,
                "prompt": prompt,
                "response": f"Error: {str(e)}",
                "model": "tinyllama-1.1b-chat-v1.0",
                "provider": getattr(self, 'model_backend', 'unknown'),
                "error": str(e),
                "timestamp": timestamp,
            }

    def _simulated_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I am TinyLlama running in simulated mode. How can I help you?"
        elif "quantum" in prompt_lower:
            return "Quantum computing leverages superposition and entanglement to process information in fundamentally new ways."
        elif "consciousness" in prompt_lower:
            return "Consciousness remains one of the hardest problems in science and philosophy."
        elif "agent" in prompt_lower:
            return "Agentic systems can autonomously plan, reason, and execute tasks using tools."
        else:
            return f"Simulated response to: {prompt[:100]}..."

    def get_status(self) -> Dict[str, Any]:
        return {
            "ai_enabled": AI_ENABLED,
            "model_loaded": self.model is not None,
            "model_path": self.model_path,
            "model_backend": getattr(self, 'model_backend', None),
            "provider": AI_MODEL_PROVIDER,
            "query_count": len(self.queries),
            "uptime_seconds": time.time() - self.start_time,
        }

    def get_query_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [asdict(q) for q in self.queries[-limit:]]


gpt_layer = GPTLayer()
