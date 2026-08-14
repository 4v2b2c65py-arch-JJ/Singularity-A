#!/usr/bin/env python3
"""
QB Protocol - Sleep Agent API Routes
Background agent control, silent operation, task scheduling.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.sleep_agent.sleep import sleep_agent
    HAS_SLEEP_AGENT = True
except ImportError:
    try:
        from sleep_agent.sleep import sleep_agent
        HAS_SLEEP_AGENT = True
    except ImportError:
        HAS_SLEEP_AGENT = False

router = APIRouter(prefix="/sleep-agent", tags=["sleep-agent"])


@router.get("/status")
def sleep_status():
    if not HAS_SLEEP_AGENT:
        return {"error": "sleep_agent_unavailable"}
    return sleep_agent.get_status()


@router.post("/start")
def start_sleep_agent():
    if not HAS_SLEEP_AGENT:
        return {"error": "sleep_agent_unavailable"}
    return sleep_agent.start()


@router.post("/stop")
def stop_sleep_agent():
    if not HAS_SLEEP_AGENT:
        return {"error": "sleep_agent_unavailable"}
    return sleep_agent.stop()


@router.post("/tasks")
def add_sleep_task(body: Dict[str, Any] = Body(...)):
    if not HAS_SLEEP_AGENT:
        return {"error": "sleep_agent_unavailable"}
    task_type = body.get("task_type", "")
    payload = body.get("payload", {})
    priority = int(body.get("priority", 5))
    run_in_sleep = body.get("run_in_sleep", True)
    screen_off = body.get("screen_off", True)
    if not task_type:
        return {"error": "task_type_required"}
    task = sleep_agent.add_task(task_type=task_type, payload=payload, priority=priority, run_in_sleep=run_in_sleep, screen_off=screen_off)
    return {"task_id": task.task_id, "status": "queued"}


@router.get("/tasks")
def get_sleep_tasks():
    if not HAS_SLEEP_AGENT:
        return {"error": "sleep_agent_unavailable"}
    with sleep_agent._lock:
        return {"tasks": [asdict(t) for t in sleep_agent.tasks[-100:]]}


@router.get("/")
def sleep_root():
    return RedirectResponse(url="/sleep-agent/status")
