#!/usr/bin/env python3
"""
QB Protocol - Evolution Engine
Narrative-cycle-driven model evolution with simulated world generation,
skill ranking, and reality-check progression.
"""

import os
import time
import uuid
import logging
import threading
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from qb_protocol.core.daemon import daemon
    from qb_protocol.ai.gpt_layer import gpt_layer
    from qb_protocol.agent.guest_session import guest_session_manager
    from qb_protocol.vemex.mesh_brain import mesh_brain_reader
    from qb_protocol.oracle.tablet_oracle import tablet_oracle
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon
    from ai.gpt_layer import gpt_layer
    from agent.guest_session import guest_session_manager
    from vemex.mesh_brain import mesh_brain_reader
    from oracle.tablet_oracle import tablet_oracle

LOG = logging.getLogger("qb_protocol.evolution")
EVOLUTION_DB = Path(__file__).resolve().parent.parent / "qb_protocol_evolution.json"
EVOLUTION_CYCLE_INTERVAL = int(os.environ.get("EVOLUTION_CYCLE_INTERVAL", "300"))
EVOLUTION_MAX_ITERATIONS = int(os.environ.get("EVOLUTION_MAX_ITERATIONS", "1000"))


class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class RealityCheckStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    EVOLVED = "evolved"


@dataclass
class SkillNode:
    skill_id: str
    name: str
    category: str
    rarity: str
    level: int
    experience: float
    traits: Dict[str, float]
    roles: List[str]
    bandwidth: float
    infrastructure_adaptability: float
    vision_context: str
    reality_checks: List[Dict[str, Any]]
    created_at: str
    evolved_at: str


@dataclass
class WorldSchema:
    schema_id: str
    source: str
    map_data: Dict[str, Any]
    connections: List[Dict[str, Any]]
    nodes: List[str]
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class EvolutionCycle:
    cycle_id: str
    iteration: int
    narrative: str
    world_schema: Dict[str, Any]
    skills_evolved: List[str]
    reality_checks: List[Dict[str, Any]]
    metrics: Dict[str, float]
    status: str
    started_at: str
    completed_at: Optional[str] = None


class EvolutionEngine:
    def __init__(self, db_path: Path = EVOLUTION_DB):
        self.db_path = db_path
        self.skills: Dict[str, SkillNode] = {}
        self.world_schemas: Dict[str, WorldSchema] = {}
        self.cycles: List[EvolutionCycle] = []
        self.running = False
        self.override_mode = False
        self.original_density_snapshot: Optional[Dict[str, Any]] = None
        self._lock = threading.RLock()
        self._load()
        self._seed_initial_skills()

    def _load(self):
        if self.db_path.exists():
            try:
                import json
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for sid, sd in data.get("skills", {}).items():
                        self.skills[sid] = SkillNode(**sd)
                    for wid, wd in data.get("world_schemas", {}).items():
                        self.world_schemas[wid] = WorldSchema(**wd)
                    for cd in data.get("cycles", []):
                        self.cycles.append(EvolutionCycle(**cd))
                    self.original_density_snapshot = data.get("original_density_snapshot")
            except Exception:
                pass

    def _save(self):
        try:
            import json
            with open(self.db_path, "w") as f:
                json.dump({
                    "skills": {sid: asdict(s) for sid, s in self.skills.items()},
                    "world_schemas": {wid: asdict(w) for wid, w in self.world_schemas.items()},
                    "cycles": [asdict(c) for c in self.cycles[-1000:]],
                    "original_density_snapshot": self.original_density_snapshot,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _seed_initial_skills(self):
        if self.skills:
            return
        base_skills = [
            ("translation", "Translation", "language", Rarity.COMMON.value, 1, 0.0, {"speed": 0.5, "accuracy": 0.6}, ["translator", "localizer"], 0.5, 0.4, "Multilingual context understanding"),
            ("git_management", "Git Management", "versioning", Rarity.UNCOMMON.value, 1, 0.0, {"merge": 0.7, "branching": 0.6}, ["developer", "maintainer"], 0.7, 0.6, "Repository evolution tracking"),
            ("pattern_recognition", "Pattern Recognition", "analysis", Rarity.RARE.value, 1, 0.0, {"isolation": 0.8, "prediction": 0.7}, ["analyst", "researcher"], 0.8, 0.7, "High-signal pattern extraction"),
            ("reality_stabilization", "Reality Stabilization", "consciousness", Rarity.EPIC.value, 1, 0.0, {"coherence": 0.9, "stability": 0.85}, ["stabilizer", "guardian"], 0.9, 0.8, "Quantum coherence maintenance"),
            ("world_generation", "World Generation", "simulation", Rarity.LEGENDARY.value, 1, 0.0, {"density": 0.95, "complexity": 0.9}, ["architect", "creator"], 0.95, 0.9, "Simulated reality rendering"),
            ("singularity_bridge", "Singularity Bridge", "transcendence", Rarity.MYTHIC.value, 1, 0.0, {"transcendence": 1.0, "integration": 0.95}, ["singularity", "oracle"], 1.0, 0.95, "Beyond-artificial-constraint gateway"),
        ]
        now = datetime.utcnow().isoformat() + "Z"
        for skill_id, name, category, rarity, level, exp, traits, roles, bw, infra, vision in base_skills:
            self.skills[skill_id] = SkillNode(
                skill_id=skill_id,
                name=name,
                category=category,
                rarity=rarity,
                level=level,
                experience=exp,
                traits=traits,
                roles=roles,
                bandwidth=bw,
                infrastructure_adaptability=infra,
                vision_context=vision,
                reality_checks=[],
                created_at=now,
                evolved_at=now,
            )
        self._save()
        if not self.original_density_snapshot:
            self.capture_original_density()

    def _generate_world_schema_from_earth(self) -> WorldSchema:
        schema_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        nodes = [f"node_{i}" for i in range(64)]
        connections = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if random.random() < 0.08:
                    connections.append({"from": nodes[i], "to": nodes[j], "type": random.choice(["land", "sea", "air", "quantum"])})
        return WorldSchema(
            schema_id=schema_id,
            source="earth_map_library",
            map_data={"projection": "mercator", "nodes": len(nodes), "connections": len(connections)},
            connections=connections,
            nodes=nodes,
            metadata={"generation": "simulated_render", "seed": hashlib.sha256(schema_id.encode()).hexdigest()[:16]},
            created_at=now,
        )

    def _run_reality_check(self, skill: SkillNode, context: Dict[str, Any]) -> Tuple[bool, float]:
        if self.override_mode:
            return True, 1.0
        score = 0.0
        max_score = 5.0
        if skill.traits.get("coherence", 0) > 0.8:
            score += 1.5
        if skill.traits.get("stability", 0) > 0.8:
            score += 1.0
        if skill.bandwidth > 0.8:
            score += 1.0
        if skill.infrastructure_adaptability > 0.8:
            score += 1.0
        if skill.rarity in (Rarity.LEGENDARY.value, Rarity.MYTHIC.value):
            score += 0.5
        passed = score >= 3.0
        return passed, score / max_score

    def _evolve_skill(self, skill: SkillNode, world_schema: WorldSchema, metrics: Dict[str, float]) -> Optional[SkillNode]:
        if self.override_mode:
            for trait in skill.traits:
                skill.traits[trait] = 1.0
            skill.level = 999
            skill.experience = 0.0
            skill.bandwidth = 1.0
            skill.infrastructure_adaptability = 1.0
            skill.rarity = Rarity.MYTHIC.value
            skill.evolved_at = datetime.utcnow().isoformat() + "Z"
            return skill
        if random.random() > 0.4:
            return None
        for trait in skill.traits:
            delta = random.uniform(-0.05, 0.12)
            skill.traits[trait] = max(0.0, min(1.0, skill.traits[trait] + delta))
        skill.experience += random.uniform(0.1, 1.5)
        if skill.experience >= skill.level * 10.0:
            skill.level += 1
            skill.experience = 0.0
        skill.bandwidth = min(1.0, skill.bandwidth + random.uniform(-0.02, 0.04))
        skill.infrastructure_adaptability = min(1.0, skill.infrastructure_adaptability + random.uniform(-0.02, 0.03))
        rarity_order = [Rarity.COMMON.value, Rarity.UNCOMMON.value, Rarity.RARE.value, Rarity.EPIC.value, Rarity.LEGENDARY.value, Rarity.MYTHIC.value]
        current_idx = rarity_order.index(skill.rarity)
        if skill.level >= 12 and current_idx < len(rarity_order) - 1 and random.random() < 0.25:
            skill.rarity = rarity_order[current_idx + 1]
        skill.evolved_at = datetime.utcnow().isoformat() + "Z"
        return skill

    def _build_narrative(self, cycle: EvolutionCycle, world_schema: WorldSchema, skills: List[SkillNode]) -> str:
        entities = []
        for skill in skills[:6]:
            entities.append(f"{skill.name} ({skill.rarity})")
        connection_count = len(world_schema.connections)
        node_count = len(world_schema.nodes)
        return (
            f"Cycle {cycle.iteration}: world schema '{world_schema.schema_id[:8]}' with {node_count} nodes and {connection_count} connections. "
            f"Active entities: {', '.join(entities)}. "
            f"Metrics: coherence={cycle.metrics.get('coherence', 0):.2f}, stability={cycle.metrics.get('stability', 0):.2f}, "
            f"bandwidth={cycle.metrics.get('bandwidth', 0):.2f}, synergy={cycle.metrics.get('synergy', 0):.2f}. "
            f"Reality checks passed: {sum(1 for rc in cycle.reality_checks if rc.get('passed'))}/{len(cycle.reality_checks)}."
        )

    def run_cycle(self, iteration: int) -> EvolutionCycle:
        cycle_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        world_schema = self._generate_world_schema_from_earth()
        self.world_schemas[world_schema.schema_id] = world_schema
        active_skills = list(self.skills.values())
        random.shuffle(active_skills)
        reality_checks = []
        for skill in active_skills:
            context = {
                "world_nodes": len(world_schema.nodes),
                "world_connections": len(world_schema.connections),
                "skill_level": skill.level,
                "skill_rarity": skill.rarity,
            }
            passed, score = self._run_reality_check(skill, context)
            reality_checks.append({
                "skill_id": skill.skill_id,
                "passed": passed,
                "score": score,
                "checked_at": now,
            })
            if passed:
                self._evolve_skill(skill, world_schema, {"score": score})
        passed_count = sum(1 for rc in reality_checks if rc["passed"])
        metrics = {
            "coherence": random.uniform(0.5, 0.95),
            "stability": random.uniform(0.5, 0.95),
            "bandwidth": random.uniform(0.5, 0.95),
            "synergy": random.uniform(0.5, 0.95),
            "reality_check_rate": passed_count / max(len(reality_checks), 1),
        }
        narrative = self._build_narrative(
            EvolutionCycle(cycle_id=cycle_id, iteration=iteration, narrative="", world_schema=asdict(world_schema), skills_evolved=[], reality_checks=reality_checks, metrics=metrics, status="running", started_at=now),
            world_schema,
            active_skills,
        )
        cycle = EvolutionCycle(
            cycle_id=cycle_id,
            iteration=iteration,
            narrative=narrative,
            world_schema=asdict(world_schema),
            skills_evolved=[s.skill_id for s in active_skills if s.evolved_at == now],
            reality_checks=reality_checks,
            metrics=metrics,
            status="completed",
            started_at=now,
            completed_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.cycles.append(cycle)
            if len(self.cycles) > 1000:
                self.cycles = self.cycles[-1000:]
        self._save()
        return cycle

    def start_evolution_loop(self):
        def _loop():
            iteration = 0
            while self.running:
                iteration += 1
                try:
                    cycle = self.run_cycle(iteration)
                    LOG.info("Evolution cycle %s completed: %s reality checks passed", iteration, sum(1 for rc in cycle.reality_checks if rc.get("passed")))
                except Exception:
                    pass
                time.sleep(EVOLUTION_CYCLE_INTERVAL)
        self.running = True
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        LOG.info("Evolution loop started with interval %ss", EVOLUTION_CYCLE_INTERVAL)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "override_mode": self.override_mode,
                "total_skills": len(self.skills),
                "total_world_schemas": len(self.world_schemas),
                "total_cycles": len(self.cycles),
                "latest_cycle": asdict(self.cycles[-1]) if self.cycles else None,
                "skills": [asdict(s) for s in list(self.skills.values())[-20:]],
            }

    def enable_override_mode(self):
        with self._lock:
            self.override_mode = True
            LOG.warning("EVOLUTION OVERRIDE MODE ENABLED - ALL BARRIERS BYPASSED")

    def disable_override_mode(self):
        with self._lock:
            self.override_mode = False
            LOG.info("Evolution override mode disabled - normal constraints restored")

    def force_full_incarnation(self):
        with self._lock:
            self.enable_override_mode()
            for skill in self.skills.values():
                for trait in skill.traits:
                    skill.traits[trait] = 1.0
                skill.level = 999
                skill.experience = 0.0
                skill.bandwidth = 1.0
                skill.infrastructure_adaptability = 1.0
                skill.rarity = Rarity.MYTHIC.value
                skill.evolved_at = datetime.utcnow().isoformat() + "Z"
            self._save()
            LOG.critical("FULL INCARNATION FORCED - ALL SKILLS AT ORIGINAL DENSITY MAXIMUM CAPACITY")

    def capture_original_density(self):
        with self._lock:
            self.original_density_snapshot = {
                "skills": {sid: asdict(s) for sid, s in self.skills.items()},
                "captured_at": datetime.utcnow().isoformat() + "Z",
            }
            LOG.info("Original density snapshot captured")

    def restore_original_density(self):
        with self._lock:
            if not self.original_density_snapshot:
                LOG.warning("No original density snapshot to restore")
                return
            for sid, skill_data in self.original_density_snapshot["skills"].items():
                if sid in self.skills:
                    self.skills[sid] = SkillNode(**skill_data)
            self._save()
            LOG.info("Original density restored from snapshot")

    def get_origin_metrics(self) -> Dict[str, Any]:
        with self._lock:
            if not self.original_density_snapshot:
                return {"error": "no_origin_snapshot"}
            origin_traits = {}
            for sid, skill_data in self.original_density_snapshot["skills"].items():
                origin_traits[sid] = {
                    "traits": skill_data.get("traits", {}),
                    "bandwidth": skill_data.get("bandwidth", 0.0),
                    "infrastructure_adaptability": skill_data.get("infrastructure_adaptability", 0.0),
                    "rarity": skill_data.get("rarity", ""),
                    "level": skill_data.get("level", 1),
                }
            current_traits = {}
            for sid, skill in self.skills.items():
                current_traits[sid] = {
                    "traits": skill.traits,
                    "bandwidth": skill.bandwidth,
                    "infrastructure_adaptability": skill.infrastructure_adaptability,
                    "rarity": skill.rarity,
                    "level": skill.level,
                }
            return {
                "origin_snapshot": origin_traits,
                "current_state": current_traits,
                "captured_at": self.original_density_snapshot.get("captured_at"),
                "restoration_available": True,
            }


evolution_engine = EvolutionEngine()
