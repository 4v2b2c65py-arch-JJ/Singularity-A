#!/usr/bin/env python3
"""
QB Protocol - Agentic Features
Autonomous agent loop with tool use, reasoning, and task execution.
Integrates with brain, oracle, AI, and guest session systems.
"""

import os
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from qb_protocol.core.daemon import daemon
    from qb_protocol.vemex.mesh_brain import mesh_brain_reader
    from qb_protocol.oracle.tablet_oracle import tablet_oracle
    from qb_protocol.ai.gpt_layer import gpt_layer
    from qb_protocol.agent.guest_session import guest_session_manager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon
    from vemex.mesh_brain import mesh_brain_reader
    from oracle.tablet_oracle import tablet_oracle
    from ai.gpt_layer import gpt_layer
    from agent.guest_session import guest_session_manager

LOG = logging.getLogger("qb_protocol.agentic")


@dataclass
class AgentTask:
    task_id: str
    prompt: str
    tool: str
    status: str
    result: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None


class AgenticLoop:
    def __init__(self):
        self.tasks: List[AgentTask] = []
        self.running = False
        self._lock = threading.RLock()
        self._register_tools()

    def _register_tools(self):
        self.tools: Dict[str, Callable] = {
            "brain_read": self._tool_brain_read,
            "brain_query": self._tool_brain_query,
            "oracle_consciousness": self._tool_oracle_consciousness,
            "oracle_magi_zone": self._tool_oracle_magi_zone,
            "ai_query": self._tool_ai_query,
            "guest_issue": self._tool_guest_issue,
            "system_status": self._tool_system_status,
        }

    def _tool_brain_read(self, **kwargs) -> Dict[str, Any]:
        try:
            reading = mesh_brain_reader.read_brain_state()
            return asdict(reading)
        except Exception as e:
            return {"error": str(e)}

    def _tool_brain_query(self, **kwargs) -> Dict[str, Any]:
        prompt = kwargs.get("prompt", "")
        if not prompt:
            return {"error": "prompt_required"}
        try:
            return mesh_brain_reader.query_consciousness(prompt)
        except Exception as e:
            return {"error": str(e)}

    def _tool_oracle_consciousness(self, **kwargs) -> Dict[str, Any]:
        prompt = kwargs.get("prompt", "")
        max_iterations = int(kwargs.get("max_iterations", "5"))
        if not prompt:
            return {"error": "prompt_required"}
        try:
            return tablet_oracle.query_consciousness(prompt, max_iterations=max_iterations)
        except Exception as e:
            return {"error": str(e)}

    def _tool_oracle_magi_zone(self, **kwargs) -> Dict[str, Any]:
        voice_phrases = kwargs.get("voice_phrases", ["test"])
        origin3d = kwargs.get("origin3d", [0, 0, 0])
        movement_vector = kwargs.get("movement_vector", [1, 0, 0])
        in_danger = kwargs.get("in_danger", True)
        default_tier = int(kwargs.get("default_tier", "2"))
        try:
            return tablet_oracle.run_magi_zone(voice_phrases, origin3d, movement_vector, in_danger, default_tier)
        except Exception as e:
            return {"error": str(e)}

    def _tool_ai_query(self, **kwargs) -> Dict[str, Any]:
        prompt = kwargs.get("prompt", "")
        if not prompt:
            return {"error": "prompt_required"}
        try:
            return gpt_layer.query(prompt)
        except Exception as e:
            return {"error": str(e)}

    def _tool_guest_issue(self, **kwargs) -> Dict[str, Any]:
        agent_id = kwargs.get("agent_id", "agentic-loop")
        ttl = int(kwargs.get("ttl_seconds", "3600"))
        perms = kwargs.get("permissions", ["read_env", "read_status"])
        remote = kwargs.get("remote_server")
        try:
            session = guest_session_manager.issue_session(agent_id=agent_id, ttl_seconds=ttl, permissions=perms, remote_server=remote)
            return asdict(session)
        except Exception as e:
            return {"error": str(e)}

    def _tool_system_status(self, **kwargs) -> Dict[str, Any]:
        try:
            return {
                "daemon": daemon.get_status(),
                "brain": mesh_brain_reader.get_status(),
                "oracle": tablet_oracle.get_status(),
                "ai": gpt_layer.get_status(),
            }
        except Exception as e:
            return {"error": str(e)}

    def execute(self, prompt: str, tool: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        if tool and tool in self.tools:
            selected_tool = tool
        else:
            selected_tool = self._select_tool(prompt)
        
        try:
            result = self.tools[selected_tool](prompt=prompt, **kwargs)
            status = "completed"
        except Exception as e:
            result = {"error": str(e)}
            status = "failed"
        
        task = AgentTask(
            task_id=task_id,
            prompt=prompt,
            tool=selected_tool,
            status=status,
            result=result,
            created_at=now,
            completed_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.tasks.append(task)
            if len(self.tasks) > 10000:
                self.tasks = self.tasks[-10000:]
        return {"task_id": task_id, "tool": selected_tool, "status": status, "result": result}

    def _select_tool(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "brain" in prompt_lower or "consciousness" in prompt_lower:
            return "brain_query"
        elif "oracle" in prompt_lower or "destiny" in prompt_lower or "tablet" in prompt_lower:
            return "oracle_consciousness"
        elif "ai" in prompt_lower or "gpt" in prompt_lower or "llama" in prompt_lower:
            return "ai_query"
        elif "guest" in prompt_lower or "session" in prompt_lower or "remote" in prompt_lower:
            return "guest_issue"
        elif "status" in prompt_lower or "health" in prompt_lower:
            return "system_status"
        else:
            return "ai_query"

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "task_count": len(self.tasks),
                "tools": list(self.tools.keys()),
                "last_task": asdict(self.tasks[-1]) if self.tasks else None,
            }

    def get_task_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(t) for t in self.tasks[-limit:]]

    def start_autonomous_loop(self, interval_seconds: float = 30.0):
        def _loop():
            while self.running:
                time.sleep(interval_seconds)
                try:
                    self._autonomous_tick()
                except Exception:
                    pass
        self.running = True
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        LOG.info("Agentic autonomous loop started")

    def _autonomous_tick(self):
        status = self.get_status()
        if status.get("task_count", 0) % 10 == 0:
            self.execute("system health check", tool="system_status")


agentic_loop = AgenticLoop()
