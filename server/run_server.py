#!/usr/bin/env python3
"""
QB Protocol - Server Entry Point
Starts FastAPI server with self-healing, IP geolocation, monitoring, and mirror integration.
"""

import logging
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from qb_protocol.server.api_server import app
from qb_protocol.server.monitor_integration import monitor_integration

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
LOG = logging.getLogger("qb_protocol.server")


def main():
    monitor_integration.start()
    LOG.info("Monitor integration started")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=17760)


if __name__ == "__main__":
    main()
