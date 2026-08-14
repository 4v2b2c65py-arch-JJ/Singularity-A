#!/usr/bin/env python3
"""
QB Protocol - Innerlan API Routes
High-level fetch via GPT model integration.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.innerlan.fetch import innerlan_fetch
    HAS_INNERLAN = True
except ImportError:
    try:
        from innerlan.fetch import innerlan_fetch
        HAS_INNERLAN = True
    except ImportError:
        HAS_INNERLAN = False

router = APIRouter(prefix="/innerlan", tags=["innerlan"])


@router.get("/status")
def innerlan_status():
    if not HAS_INNERLAN:
        return {"error": "innerlan_unavailable"}
    return innerlan_fetch.get_status()


@router.post("/fetch")
def innerlan_fetch_endpoint(body: Dict[str, Any] = Body(...)):
    if not HAS_INNERLAN:
        return {"error": "innerlan_unavailable"}
    source = body.get("source", "")
    query = body.get("query", "")
    mode = body.get("mode", "gpt_enhanced")
    context = body.get("context", {})
    max_tokens = body.get("max_tokens", 256)
    temperature = body.get("temperature", 0.7)
    if not source or not query:
        return {"error": "source_and_query_required"}
    response = innerlan_fetch.fetch(
        source=source,
        query=query,
        mode=mode,
        context=context,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response


@router.get("/history")
def innerlan_history(limit: int = 100):
    if not HAS_INNERLAN:
        return {"error": "innerlan_unavailable"}
    return {"history": innerlan_fetch.get_history(limit=limit)}


@router.post("/enhance")
def innerlan_enhance(body: Dict[str, Any] = Body(...)):
    if not HAS_INNERLAN:
        return {"error": "innerlan_unavailable"}
    text = body.get("text", "")
    query = body.get("query", "")
    mode = body.get("mode", "gpt_enhanced")
    max_tokens = body.get("max_tokens", 256)
    temperature = body.get("temperature", 0.7)
    if not text or not query:
        return {"error": "text_and_query_required"}
    response = innerlan_fetch.fetch(
        source="raw_text",
        query=query,
        mode=mode,
        context={"raw_text": text},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return {"enhanced": response.enhanced, "raw": response.raw, "mode": mode}
