#!/usr/bin/env python3
"""
QB Protocol - CLI Chat
Direct interactive chat with TinyLlama model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ai.gpt_layer import gpt_layer


def main():
    print("=" * 60)
    print("QB Protocol - TinyLlama CLI Chat")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            break

        result = gpt_layer.query(user_input, max_tokens=256, temperature=0.7)
        response = result.get("response", str(result))
        print(f"\nModel ({result.get('latency_ms', 0):.2f}s): {response}")

    print("\nGoodbye.")


if __name__ == "__main__":
    main()
