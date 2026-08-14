#!/usr/bin/env python3
"""
QB Protocol - Model Profile API Routes
Model densities, heat waves, nervous system matching, relaxation.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.model_profile.density import model_density
    from qb_protocol.model_profile.nervous import nervous_matcher, RelaxationDetector
    HAS_MODEL_PROFILE = True
except ImportError:
    try:
        from model_profile.density import model_density
        from model_profile.nervous import nervous_matcher, RelaxationDetector
        HAS_MODEL_PROFILE = True
    except ImportError:
        HAS_MODEL_PROFILE = False

router = APIRouter(prefix="/model-profile", tags=["model-profile"])


@router.get("/status")
def model_profile_status():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    return model_density.get_status()


@router.get("/profile")
def get_model_profile():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    return model_density.get_profile()


@router.post("/experience")
def add_experience(body: Dict[str, Any] = Body(...)):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    context = body.get("context", {})
    point = model_density.add_experience(context=context)
    return asdict(point)


@router.post("/wave/cooling")
def generate_cooling_wave():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    wave = model_density.generate_cooling_wave()
    result = model_density.apply_wave(wave)
    return {"wave": asdict(wave), "result": result}


@router.post("/wave/heating")
def generate_heating_wave():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    wave = model_density.generate_heating_wave()
    result = model_density.apply_wave(wave)
    return {"wave": asdict(wave), "result": result}


@router.get("/waves")
def get_waves(limit: int = 50):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    with model_density._lock:
        waves = model_density.waves[-limit:]
    return {"waves": [asdict(w) for w in waves]}


@router.get("/nervous/status")
def nervous_status():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    return nervous_matcher.get_status()


@router.post("/nervous/detect")
def detect_nervous_pattern(body: Dict[str, Any] = Body(...)):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    user_id = body.get("user_id", "default")
    input_data = body.get("input_data", {})
    pattern = nervous_matcher.detect_user_pattern(user_id, input_data)
    return asdict(pattern)


@router.post("/nervous/relaxation")
def detect_relaxation(body: Dict[str, Any] = Body(...)):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    user_id = body.get("user_id", "default")
    input_data = body.get("input_data", {})
    result = nervous_matcher.detect_relaxation(user_id, input_data)
    return result


@router.post("/nervous/mimic")
def mimic_user_state(body: Dict[str, Any] = Body(...)):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    user_id = body.get("user_id", "default")
    target_state = body.get("target_state", "relaxed")
    duration = float(body.get("duration", 60.0))
    session = nervous_matcher.mimic_user_state(user_id, target_state, duration=duration)
    return asdict(session)


@router.post("/nervous/lung-match")
def match_lung_pattern(body: Dict[str, Any] = Body(...)):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    user_id = body.get("user_id", "default")
    target_pattern = body.get("target_pattern", "normal")
    result = nervous_matcher.match_lung_pattern(user_id, target_pattern)
    return result


@router.get("/nervous/patterns/{user_id}")
def get_user_patterns(user_id: str, limit: int = 100):
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    patterns = nervous_matcher.get_user_patterns(user_id, limit=limit)
    return {"user_id": user_id, "patterns": patterns}


@router.get("/relaxation/techniques")
def get_relaxation_techniques():
    if not HAS_MODEL_PROFILE:
        return {"error": "model_profile_unavailable"}
    detector = RelaxationDetector(nervous_matcher)
    return {"techniques": detector.relaxation_techniques}


@router.get("/")
def model_profile_root():
    return RedirectResponse(url="/model-profile/status")
