#!/usr/bin/env python3
"""
QB Protocol - Live Model Chat
Interactive CLI chat interface for TinyLlama model.
Connects to local API server or direct gpt_layer.
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.environ.get("QB_API_URL", "http://127.0.0.1:17760")
DIRECT_MODE = os.environ.get("CHAT_DIRECT_MODE", "false").lower() == "true"

if not DIRECT_MODE:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from ai.gpt_layer import gpt_layer
    except ImportError:
        DIRECT_MODE = True


def chat_via_api(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{API_URL}/ai/query",
            json={"prompt": prompt, "max_tokens": 256, "temperature": 0.7},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", str(data))
    except Exception as e:
        return f"[API Error] {e}"


def chat_direct(prompt: str) -> str:
    try:
        result = gpt_layer.query(prompt, max_tokens=256, temperature=0.7)
        return result.get("response", str(result))
    except Exception as e:
        return f"[Direct Error] {e}"


def main():
    print("=" * 60)
    print("QB Protocol - TinyLlama Live Chat")
    print(f"Mode: {'DIRECT' if DIRECT_MODE else 'API'}")
    print(f"Endpoint: {API_URL}")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    history = []
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            break

        start = time.time()
        if DIRECT_MODE:
            reply = chat_direct(user_input)
        else:
            reply = chat_via_api(user_input)
        elapsed = time.time() - start

        history.append({"user": user_input, "assistant": reply, "time": elapsed})
        print(f"\nModel ({elapsed:.2f}s): {reply}")

    print("\nGoodbye.")
    if history:
        print(f"Messages exchanged: {len(history)}")


if __name__ == "__main__":
    main()
