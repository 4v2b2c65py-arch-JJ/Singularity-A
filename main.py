#!/usr/bin/env python3
"""
QB Protocol - Main Entry Point
Starts unified daemon, server, foreground monitor, and registers services.
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qb_protocol.core.daemon import daemon
from qb_protocol.server.platform_server import server
from qb_protocol.stabilizers.reality_stabilizer import reality_stabilizer
from qb_protocol.dream.dream_engine import dream_engine
from qb_protocol.package.node_service_package import node_package, rate_limiter


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
LOG = logging.getLogger("qb_protocol")


def register_default_services():
    node_package.register_service("status", lambda payload: daemon.get_status())
    node_package.register_service("platform", lambda payload: server.get_platform_capabilities())
    node_package.register_service("stabilizer_status", lambda payload: reality_stabilizer.get_status())
    node_package.register_service("dream_status", lambda payload: dream_engine.get_status())


async def main():
    register_default_services()
    await daemon.start()
    start_msg = await server.start()
    LOG.info(start_msg)
    LOG.info("QB Protocol active: daemon=%s, server=%s, stabilizer=%s, dream=%s", daemon.running, server.running, reality_stabilizer.running, dream_engine)
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await daemon.stop()
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
