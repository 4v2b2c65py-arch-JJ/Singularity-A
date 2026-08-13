#!/usr/bin/env python3
"""
QB Protocol - Cross-Platform Server Powered Library
Native bindings and server for Android, iPhone, macOS, Windows, Linux.
"""

import asyncio
import json
import time
import uuid
import platform
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon


@dataclass
class PlatformCapabilities:
    os: str
    arch: str
    python_version: str
    has_gpu: bool
    has_neural_engine: bool
    has_webview: bool
    has_swift: bool
    has_rust: bool
    node_version: Optional[str]
    lua_version: Optional[str]


class CrossPlatformServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 17760):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.base_events.Server] = None
        self.running = False

    def get_platform_capabilities(self) -> PlatformCapabilities:
        node_version = None
        lua_version = None
        try:
            import subprocess
            node = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=2)
            if node.returncode == 0:
                node_version = node.stdout.strip()
        except Exception:
            pass
        try:
            import subprocess
            lua = subprocess.run(["lua", "-v"], capture_output=True, text=True, timeout=2)
            if lua.returncode == 0:
                lua_version = lua.stdout.strip()
        except Exception:
            pass
        return PlatformCapabilities(
            os=platform.system(),
            arch=platform.machine(),
            python_version=platform.python_version(),
            has_gpu=False,
            has_neural_engine=platform.system() == "Darwin",
            has_webview=platform.system() == "Darwin",
            has_swift=False,
            has_rust=False,
            node_version=node_version,
            lua_version=lua_version,
        )

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await reader.read(65536)
            if not data:
                return
            try:
                request = json.loads(data.decode())
            except json.JSONDecodeError:
                writer.close()
                return
            response = await self.route_request(request)
            writer.write(json.dumps(response).encode())
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")
        payload = request.get("payload", {})
        if action == "status":
            return {"status": "ok", "data": daemon.get_status()}
        if action == "platform":
            caps = self.get_platform_capabilities()
            return {"status": "ok", "data": asdict(caps)}
        if action == "register_instance":
            name = payload.get("name", "unnamed")
            platform_name = payload.get("platform")
            metadata = payload.get("metadata", {})
            inst = daemon.register_instance(name=name, platform=platform_name, metadata=metadata)
            return {"status": "ok", "data": asdict(inst)}
        if action == "start_instance":
            instance_id = payload.get("instance_id")
            return {"status": "ok", "started": daemon.start_instance(instance_id)}
        if action == "stop_instance":
            instance_id = payload.get("instance_id")
            return {"status": "ok", "stopped": daemon.stop_instance(instance_id)}
        if action == "register_core":
            instance_id = payload.get("instance_id")
            core_type = payload.get("core_type", "cpu")
            thread_id = payload.get("thread_id")
            core = daemon.register_core(instance_id, core_type, thread_id)
            return {"status": "ok", "data": asdict(core)}
        if action == "update_core":
            core_id = payload.get("core_id")
            load = payload.get("load", 0.0)
            temperature = payload.get("temperature", 0.0)
            daemon.update_core_heartbeat(core_id, load, temperature)
            return {"status": "ok"}
        if action == "dream_layer":
            depth = payload.get("depth", 0.0)
            projection = payload.get("projection", {})
            convergence = payload.get("convergence", 0.0)
            brain_emission = payload.get("brain_state_emission", 0.0)
            singularity = payload.get("singularity_threshold", 0.0)
            layer = daemon.add_dream_layer(depth, projection, convergence, brain_emission, singularity)
            return {"status": "ok", "data": asdict(layer)}
        return {"status": "error", "error": f"Unknown action: {action}"}

    async def start(self):
        self.running = True
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = self.server.sockets[0].getsockname() if self.server.sockets else (self.host, self.port)
        return f"QB Protocol server listening on {addr[0]}:{addr[1]}"

    async def stop(self):
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    def run_sync(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            start_msg = loop.run_until_complete(self.start())
            LOG.info(start_msg)
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self.stop())
            loop.close()


server = CrossPlatformServer()
