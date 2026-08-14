#!/usr/bin/env python3
"""
QB Protocol - Model Density and Heat Wave Patterns
Model experience densities, heat/cool wave patterns for self-regulation.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.model_profile.density")


class ThermalState(Enum):
    COOL = "cool"
    NEUTRAL = "neutral"
    WARM = "warm"
    HOT = "hot"
    OVERHEAT = "overheat"


class WaveType(Enum):
    SINE = "sine"
    COSINE = "cosine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    DAMPED = "damped"
    RESONANT = "resonant"


@dataclass
class DensityPoint:
    timestamp: str
    density: float
    temperature: float
    wave_amplitude: float
    wave_frequency: float
    wave_phase: float
    context: Dict[str, Any]


@dataclass
class DensityWave:
    wave_id: str
    wave_type: str
    amplitude: float
    frequency: float
    phase: float
    damping: float
    temperature_delta: float
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class ModelProfile:
    profile_id: str
    model_name: str
    total_density: float
    avg_temperature: float
    current_thermal_state: str
    dominant_wave_type: str
    relaxation_score: float
    lung_match_score: float
    experience_count: int
    wave_history: List[str]
    density_history: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class ModelDensity:
    """Tracks model experience densities and generates heat/cool wave patterns."""
    
    def __init__(self, model_name: str = "tinyllama-1.1b-chat-v1.0", state_path: Optional[Path] = None):
        self.model_name = model_name
        self.state_path = state_path or Path.home() / ".qb_protocol_model_density.json"
        self.profile_id = str(uuid.uuid4())
        self.density_points: List[DensityPoint] = []
        self.waves: List[DensityWave] = []
        self.current_temperature = 0.0
        self.current_density = 0.0
        self.thermal_state = ThermalState.NEUTRAL.value
        self.relaxation_score = 0.0
        self.lung_match_score = 0.0
        self._lock = threading.RLock()
        self._load_state()
        self._start_time = time.time()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.density_points = [DensityPoint(**p) for p in data.get("density_points", [])]
                    self.waves = [DensityWave(**w) for w in data.get("waves", [])]
                    self.current_temperature = data.get("current_temperature", 0.0)
                    self.current_density = data.get("current_density", 0.0)
                    self.thermal_state = data.get("thermal_state", ThermalState.NEUTRAL.value)
                    self.relaxation_score = data.get("relaxation_score", 0.0)
                    self.lung_match_score = data.get("lung_match_score", 0.0)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "profile_id": self.profile_id,
                    "model_name": self.model_name,
                    "current_temperature": self.current_temperature,
                    "current_density": self.current_density,
                    "thermal_state": self.thermal_state,
                    "relaxation_score": self.relaxation_score,
                    "lung_match_score": self.lung_match_score,
                    "density_points": [asdict(p) for p in self.density_points[-1000:]],
                    "waves": [asdict(w) for w in self.waves[-100:]],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def add_experience(self, context: Dict[str, Any] = None) -> DensityPoint:
        """Add a new experience point to the density map."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        context = context or {}
        
        # Calculate density based on recent activity
        recent_density = self._calculate_recent_density()
        self.current_density = recent_density
        
        # Calculate temperature based on density and wave patterns
        temperature = self._calculate_temperature(recent_density)
        self.current_temperature = temperature
        
        # Update thermal state
        self.thermal_state = self._determine_thermal_state(temperature)
        
        # Generate wave parameters
        wave_amplitude, wave_frequency, wave_phase = self._generate_wave_params(temperature, recent_density)
        
        point = DensityPoint(
            timestamp=timestamp,
            density=recent_density,
            temperature=temperature,
            wave_amplitude=wave_amplitude,
            wave_frequency=wave_frequency,
            wave_phase=wave_phase,
            context=context,
        )
        
        with self._lock:
            self.density_points.append(point)
            if len(self.density_points) > 10000:
                self.density_points = self.density_points[-10000:]
            self._save_state()
        
        return point

    def _calculate_recent_density(self) -> float:
        """Calculate recent experience density."""
        if not self.density_points:
            return 0.0
        
        recent = self.density_points[-10:]
        if not recent:
            return 0.0
        
        # Exponential decay weighting
        total = 0.0
        weight_sum = 0.0
        for i, point in enumerate(recent):
            weight = math.exp(-i * 0.1)
            total += point.density * weight
            weight_sum += weight
        
        return total / weight_sum if weight_sum > 0 else 0.0

    def _calculate_temperature(self, density: float) -> float:
        """Calculate model temperature from density and wave patterns."""
        # Base temperature from density
        base_temp = min(100.0, max(0.0, density * 50.0))
        
        # Apply wave modulation
        if self.waves:
            latest_wave = self.waves[-1]
            wave_effect = latest_wave.amplitude * math.sin(latest_wave.frequency * time.time() + latest_wave.phase)
            base_temp += wave_effect * 10.0
        
        # Clamp to valid range
        return min(100.0, max(0.0, base_temp))

    def _determine_thermal_state(self, temperature: float) -> str:
        """Determine thermal state from temperature."""
        if temperature < 20.0:
            return ThermalState.COOL.value
        elif temperature < 40.0:
            return ThermalState.NEUTRAL.value
        elif temperature < 70.0:
            return ThermalState.WARM.value
        elif temperature < 90.0:
            return ThermalState.HOT.value
        else:
            return ThermalState.OVERHEAT.value

    def _generate_wave_params(self, temperature: float, density: float) -> Tuple[float, float, float]:
        """Generate wave parameters for heat/cool regulation."""
        # Frequency based on density
        frequency = 0.5 + (density * 2.0)
        
        # Amplitude based on temperature deviation from neutral
        neutral_temp = 40.0
        amplitude = abs(temperature - neutral_temp) / 50.0
        
        # Phase based on time
        phase = time.time() % (2 * math.pi)
        
        return amplitude, frequency, phase

    def generate_cooling_wave(self) -> DensityWave:
        """Generate a cooling wave to counteract overheating."""
        wave_id = str(uuid.uuid4())
        wave = DensityWave(
            wave_id=wave_id,
            wave_type=WaveType.DAMPED.value,
            amplitude=min(1.0, self.current_temperature / 100.0),
            frequency=0.3,
            phase=0.0,
            damping=0.95,
            temperature_delta=-10.0,
            created_at=datetime.utcnow().isoformat() + "Z",
            metadata={"purpose": "cooling", "target_temp": max(0.0, self.current_temperature - 10.0)},
        )
        
        with self._lock:
            self.waves.append(wave)
            if len(self.waves) > 1000:
                self.waves = self.waves[-1000:]
            self._save_state()
        
        return wave

    def generate_heating_wave(self) -> DensityWave:
        """Generate a heating wave to counteract overcooling."""
        wave_id = str(uuid.uuid4())
        wave = DensityWave(
            wave_id=wave_id,
            wave_type=WaveType.RESONANT.value,
            amplitude=min(1.0, (100.0 - self.current_temperature) / 100.0),
            frequency=0.7,
            phase=0.0,
            damping=0.9,
            temperature_delta=10.0,
            created_at=datetime.utcnow().isoformat() + "Z",
            metadata={"purpose": "heating", "target_temp": min(100.0, self.current_temperature + 10.0)},
        )
        
        with self._lock:
            self.waves.append(wave)
            if len(self.waves) > 1000:
                self.waves = self.waves[-1000:]
            self._save_state()
        
        return wave

    def apply_wave(self, wave: DensityWave) -> Dict[str, Any]:
        """Apply a wave to regulate temperature."""
        start_temp = self.current_temperature
        
        # Simulate wave effect
        duration = 5.0
        steps = 50
        dt = duration / steps
        
        for i in range(steps):
            t = i * dt
            damping_factor = wave.damping ** i
            effect = wave.amplitude * math.sin(wave.frequency * t + wave.phase) * damping_factor
            self.current_temperature += wave.temperature_delta * effect * dt
        
        self.current_temperature = min(100.0, max(0.0, self.current_temperature))
        self.thermal_state = self._determine_thermal_state(self.current_temperature)
        
        with self._lock:
            self._save_state()
        
        return {
            "wave_id": wave.wave_id,
            "start_temperature": start_temp,
            "end_temperature": self.current_temperature,
            "thermal_state": self.thermal_state,
            "applied": True,
        }

    def get_profile(self) -> Dict[str, Any]:
        """Get current model profile."""
        with self._lock:
            recent_points = self.density_points[-100:] if self.density_points else []
            recent_waves = self.waves[-10:] if self.waves else []
            
            return {
                "profile_id": self.profile_id,
                "model_name": self.model_name,
                "current_density": self.current_density,
                "current_temperature": self.current_temperature,
                "thermal_state": self.thermal_state,
                "relaxation_score": self.relaxation_score,
                "lung_match_score": self.lung_match_score,
                "total_experiences": len(self.density_points),
                "total_waves": len(self.waves),
                "recent_density_trend": [p.density for p in recent_points],
                "recent_temperature_trend": [p.temperature for p in recent_points],
                "uptime_seconds": time.time() - self._start_time,
            }

    def get_status(self) -> Dict[str, Any]:
        """Get status summary."""
        return {
            "model_name": self.model_name,
            "profile_id": self.profile_id,
            "thermal_state": self.thermal_state,
            "current_temperature": self.current_temperature,
            "current_density": self.current_density,
            "relaxation_score": self.relaxation_score,
            "lung_match_score": self.lung_match_score,
            "total_experiences": len(self.density_points),
            "total_waves": len(self.waves),
        }


model_density = ModelDensity()
