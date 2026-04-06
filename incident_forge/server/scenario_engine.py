# incident_forge/server/scenario_engine.py
"""
Scenario selection and procedural variation engine.

Supports both fixed scenario selection and procedural generation
of scenario variants from templates + randomization.
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional

from .scenarios import ALL_SCENARIOS, EASY_SCENARIOS, MEDIUM_SCENARIOS, HARD_SCENARIOS
from .scenarios.easy import Scenario


SCENARIOS_BY_DIFFICULTY: Dict[str, List[Scenario]] = {
    "easy": EASY_SCENARIOS,
    "medium": MEDIUM_SCENARIOS,
    "hard": HARD_SCENARIOS,
}


class ScenarioEngine:
    """Selects and optionally mutates scenarios for each episode."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._used_ids: List[str] = []

    def select(
        self,
        difficulty: str = "easy",
        scenario_id: Optional[str] = None,
    ) -> Scenario:
        """Select a scenario by difficulty or explicit ID.

        If scenario_id is given, returns that exact scenario.
        Otherwise picks a random scenario at the given difficulty.
        """
        if scenario_id:
            for s in ALL_SCENARIOS:
                if s.id == scenario_id:
                    return copy.deepcopy(s)
            raise ValueError(f"Unknown scenario_id: {scenario_id}")

        pool = SCENARIOS_BY_DIFFICULTY.get(difficulty, EASY_SCENARIOS)
        scenario = self._rng.choice(pool)
        return copy.deepcopy(scenario)

    def generate(self, difficulty: str, seed: int) -> Scenario:
        """Procedurally generate a scenario variation from templates.

        With 5 templates × randomized services × variable noise =
        hundreds of unique scenarios from a small codebase.
        """
        rng = random.Random(seed)
        templates = SCENARIOS_BY_DIFFICULTY.get(difficulty, EASY_SCENARIOS)
        template = rng.choice(templates)
        scenario = copy.deepcopy(template)

        # Assign a unique generated ID
        scenario.id = f"gen_{difficulty}_{seed}"
        scenario.name = f"{scenario.name} (variant #{seed % 1000})"

        # ── Randomize metric values within realistic ranges ──────────
        for svc_name, mods in scenario.service_modifications.items():
            if "error_rate_percent" in mods:
                base = mods["error_rate_percent"]
                mods["error_rate_percent"] = round(
                    base + rng.uniform(-base * 0.2, base * 0.2), 1
                )
            if "latency_p99_ms" in mods:
                base = mods["latency_p99_ms"]
                mods["latency_p99_ms"] = round(
                    base + rng.uniform(-base * 0.15, base * 0.3), 1
                )
            if "memory_percent" in mods:
                base = mods["memory_percent"]
                mods["memory_percent"] = round(
                    min(99.5, base + rng.uniform(-3, 5)), 1
                )

        # ── Randomize red herrings ───────────────────────────────────
        all_services = [
            "api-gateway", "auth-service", "user-service", "order-service",
            "payment-service", "inventory-service", "notification-service",
        ]
        safe_services = [
            s for s in all_services
            if s not in scenario.service_modifications
        ]
        if safe_services and rng.random() < 0.5:
            herring_svc = rng.choice(safe_services)
            scenario.red_herrings.append({
                "service": herring_svc,
                "hint": rng.choice([
                    "Slight latency variance (normal)",
                    "Minor log warning (routine)",
                    "CPU spike (garbage collection)",
                ]),
            })

        # ── Vary optimal step count ──────────────────────────────────
        scenario.optimal_step_count += rng.randint(-1, 2)
        scenario.optimal_step_count = max(3, scenario.optimal_step_count)

        return scenario
