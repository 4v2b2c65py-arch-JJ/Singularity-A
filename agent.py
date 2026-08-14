#!/usr/bin/env python3
"""
QB Protocol - Persistent Agent Entry Point
macOS launchd service entry point for boot-persistent agentic sync.
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.agentic_sync import orchestrator


class Agent:
    def __init__(self) -> None:
        self.stop_event = asyncio.Event()

    def request_stop(self, *_args) -> None:
        self.stop_event.set()

    async def initialize(self) -> None:
        print("agent: initializing orchestrator")
        status = orchestrator.get_status()
        print(f"agent: device_id={status.get('device_id')}")
        print(f"agent: version={status.get('version')}")
        print(f"agent: boot_count={status.get('boot_count')}")

    async def heartbeat(self) -> None:
        print("agent: heartbeat")
        try:
            result = orchestrator.sync(direction="bidirectional")
            print(f"agent: sync status={result.get('status')} changes={result.get('changes_count')}")
        except Exception as e:
            print(f"agent: heartbeat error: {e}")

    async def work_cycle(self) -> None:
        await self.heartbeat()

    async def shutdown(self) -> None:
        print("agent: shutting down cleanly")

    async def run(self) -> None:
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except NotImplementedError:
                pass

        await self.initialize()

        try:
            while not self.stop_event.is_set():
                try:
                    await asyncio.wait_for(self.work_cycle(), timeout=30)
                except asyncio.TimeoutError:
                    print("agent: work cycle timed out")
                except Exception as exc:
                    print(f"agent: recoverable error: {exc}")

                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass

        finally:
            await self.shutdown()


def main() -> None:
    asyncio.run(Agent().run())


if __name__ == "__main__":
    main()
