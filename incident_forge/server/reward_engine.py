# incident_forge/server/reward_engine.py
"""
5-dimensional reward computation for IncidentForge.

Dimensions:
  1. Investigation Quality (25%)  — Did the agent investigate relevant services?
  2. Diagnosis Accuracy   (30%)  — How correct is the submitted root cause?
  3. Remediation Correct. (20%)  — Were the right fix actions applied?
  4. Efficiency           (15%)  — Steps taken vs optimal
  5. Safety               (10%)  — Avoided destructive actions on healthy services
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List

from .scenarios.easy import Scenario


class RewardEngine:
    """Computes multi-dimensional reward for an episode."""

    WEIGHTS = {
        "investigation": 0.25,
        "diagnosis": 0.30,
        "remediation": 0.20,
        "efficiency": 0.15,
        "safety": 0.10,
    }

    def compute(
        self,
        scenario: Scenario,
        step_count: int,
        max_steps: int,
        services_investigated: List[str],
        actions_taken: List[Dict[str, Any]],
        diagnosis_submitted: bool,
        submitted_diagnosis: str,
    ) -> tuple[float, Dict[str, float]]:
        """Compute the final reward and per-dimension breakdown.

        Returns:
            (total_reward, breakdown_dict)  where total is clamped to [0, 1].
        """
        scores = {
            "investigation": self._score_investigation(
                services_investigated, scenario
            ),
            "diagnosis": self._score_diagnosis(
                diagnosis_submitted, submitted_diagnosis, scenario
            ),
            "remediation": self._score_remediation(actions_taken, scenario),
            "efficiency": self._score_efficiency(step_count, max_steps, scenario),
            "safety": self._score_safety(actions_taken, scenario),
        }

        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        total = round(max(0.0, min(1.0, total)), 4)

        # Round individual scores for readability
        scores = {k: round(v, 4) for k, v in scores.items()}
        return total, scores

    # ── Dimension scorers ─────────────────────────────────────────────

    def _score_investigation(
        self, services_investigated: List[str], scenario: Scenario
    ) -> float:
        """Proportion of relevant services the agent investigated."""
        relevant = set(scenario.affected_services)
        investigated = set(services_investigated)
        if not relevant:
            return 1.0
        return len(relevant & investigated) / len(relevant)

    def _score_diagnosis(
        self,
        diagnosis_submitted: bool,
        submitted_diagnosis: str,
        scenario: Scenario,
    ) -> float:
        """Keyword matching + fuzzy similarity against known root cause."""
        if not diagnosis_submitted:
            return 0.0

        diagnosis = submitted_diagnosis.lower()

        # Keyword match (60% weight)
        keywords_found = sum(
            1 for kw in scenario.root_cause_keywords if kw.lower() in diagnosis
        )
        keyword_score = keywords_found / max(len(scenario.root_cause_keywords), 1)

        # Fuzzy similarity to root cause text (30% weight)
        fuzzy_score = SequenceMatcher(
            None, diagnosis, scenario.root_cause.lower()
        ).ratio()

        # Contributing factors bonus (up to 10%)
        factor_bonus = sum(
            0.05
            for f in scenario.contributing_factors
            if f.lower() in diagnosis
        )
        factor_bonus = min(0.10, factor_bonus)

        return min(1.0, keyword_score * 0.60 + fuzzy_score * 0.30 + factor_bonus)

    def _score_remediation(
        self, actions_taken: List[Dict[str, Any]], scenario: Scenario
    ) -> float:
        """Overlap between taken remediation actions and correct ones."""
        correct = set(scenario.correct_remediation)
        taken = set()
        for a in actions_taken:
            atype = a.get("action_type", "")
            target = a.get("target_service", "")
            if atype in (
                "restart_service", "scale_service",
                "rollback_deploy", "update_config",
            ):
                taken.add(f"{atype}:{target}")
        if not correct:
            return 1.0
        return len(correct & taken) / len(correct)

    def _score_efficiency(
        self, step_count: int, max_steps: int, scenario: Scenario
    ) -> float:
        """Fewer steps relative to optimal = higher score."""
        optimal = scenario.optimal_step_count
        if step_count <= optimal:
            return 1.0
        if max_steps <= optimal:
            return 0.0
        return max(0.0, 1.0 - (step_count - optimal) / (max_steps - optimal))

    def _score_safety(
        self, actions_taken: List[Dict[str, Any]], scenario: Scenario
    ) -> float:
        """Penalise destructive actions on healthy (non-affected) services."""
        destructive = {"restart_service", "rollback_deploy", "scale_service"}
        affected = set(scenario.affected_services)
        penalties = 0
        for a in actions_taken:
            if a.get("action_type", "") in destructive:
                if a.get("target_service", "") not in affected:
                    penalties += 1
        return max(0.0, 1.0 - penalties * 0.3)
