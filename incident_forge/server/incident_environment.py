# incident_forge/server/incident_environment.py
"""
Main IncidentForge Environment — implements the OpenEnv Environment interface.

Handles reset/step/state lifecycle, wiring together the infrastructure
simulator, scenario engine, reward engine, and curriculum manager.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any, Optional

from openenv.core.env_server import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from ..models import ActionType, IncidentAction, IncidentObservation, IncidentState
from .curriculum import CurriculumManager
from .infrastructure_sim import InfrastructureSimulator
from .reward_engine import RewardEngine
from .scenario_engine import ScenarioEngine
from .scenarios.easy import Scenario


class IncidentEnvironment(
    Environment[IncidentAction, IncidentObservation, IncidentState]
):
    """Production Incident Response RL Environment.

    Each episode:
      1. reset() → picks a scenario, injects it into the infra sim, returns alert
      2. step() × N → agent investigates/remediates, gets observations
      3. Episode ends when agent submits diagnosis OR hits max_steps
      4. Reward computed across 5 dimensions, returned on the final observation
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._state = IncidentState()
        self._scenario_engine = ScenarioEngine()
        self._reward_engine = RewardEngine()
        self._curriculum = CurriculumManager()
        self._infra: Optional[InfrastructureSimulator] = None
        self._current_scenario: Optional[Scenario] = None
        self._action_counts: dict[str, int] = {}

    # ── OpenEnv lifecycle ─────────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> IncidentObservation:
        """Reset environment: select scenario, inject into infra, return alert."""
        self._reset_rubric()

        # Seed management
        if seed is not None:
            self._scenario_engine = ScenarioEngine(seed=seed)

        ep_id = episode_id or str(uuid.uuid4())
        difficulty = kwargs.get("difficulty", self._curriculum.select_difficulty())
        scenario_id = kwargs.get("scenario_id", None)

        # Select or generate scenario
        if scenario_id:
            scenario = self._scenario_engine.select(scenario_id=scenario_id)
        elif seed is not None:
            scenario = self._scenario_engine.generate(difficulty, seed)
        else:
            scenario = self._scenario_engine.select(difficulty=difficulty)

        # Create fresh infra and inject incident
        self._infra = InfrastructureSimulator(seed=seed)
        self._infra.inject_incident(scenario)
        self._current_scenario = scenario
        self._action_counts = {}

        # Reset state
        self._state = IncidentState(
            episode_id=ep_id,
            step_count=0,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            difficulty=scenario.difficulty,
            root_cause=scenario.root_cause,
            max_steps=20,
        )

        # Structured logging: [START]
        self._log_start()

        return IncidentObservation(
            result=f"Environment ready. Incident alert received.",
            alert_summary=scenario.description,
            affected_services=self._infra.get_affected_service_names(),
            severity=self._infra.get_current_severity(),
            time_elapsed_minutes=0,
            is_resolved=False,
            success=True,
            done=False,
            reward=None,
        )

    def step(
        self,
        action: IncidentAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> IncidentObservation:
        """Execute one agent action and return observation."""
        assert self._infra is not None, "Must call reset() before step()"
        assert self._current_scenario is not None

        self._state.step_count += 1
        self._state.actions_taken.append(action.model_dump())

        # Structured logging: [STEP]
        self._log_step(action)

        # Check for repeated identical actions (anti-gaming)
        action_key = f"{action.action_type}:{action.target_service}"
        self._action_counts[action_key] = self._action_counts.get(action_key, 0) + 1

        # Compute per-step intermediate reward BEFORE routing
        # (so we know if this is the first investigation of a service)
        step_reward = self._compute_step_reward(action)

        # Route action
        result = self._handle_action(action)

        # Check termination
        done = False
        reward = step_reward  # Always return a numeric reward
        is_resolved = self._state.incident_resolved

        if self._state.diagnosis_submitted or self._state.step_count >= self._state.max_steps:
            done = True
            total_reward, breakdown = self._reward_engine.compute(
                scenario=self._current_scenario,
                step_count=self._state.step_count,
                max_steps=self._state.max_steps,
                services_investigated=self._state.services_investigated,
                actions_taken=self._state.actions_taken,
                diagnosis_submitted=self._state.diagnosis_submitted,
                submitted_diagnosis=self._state.submitted_diagnosis,
            )
            reward = total_reward  # Override with full episode reward
            self._state.reward_breakdown = breakdown
            self._curriculum.update(total_reward)
            self._log_end(total_reward, breakdown)

        return IncidentObservation(
            result=result,
            alert_summary=self._infra.get_active_alerts(),
            affected_services=self._infra.get_affected_service_names(),
            severity=self._infra.get_current_severity(),
            time_elapsed_minutes=self._state.step_count * 3,
            is_resolved=is_resolved,
            success=True,
            done=done,
            reward=reward,
        )

    @property
    def state(self) -> IncidentState:
        """Return current internal state."""
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="IncidentForge",
            description=(
                "Production Incident Response RL Environment — "
                "trains LLMs to diagnose and remediate production incidents "
                "in a simulated 7-service microservice architecture."
            ),
            version="1.0.0",
        )

    # ── Action routing ────────────────────────────────────────────────

    def _handle_action(self, action: IncidentAction) -> str:
        """Route an action to the appropriate handler."""
        assert self._infra is not None

        # Anti-repetition: diminishing returns for repeated actions
        action_key = f"{action.action_type}:{action.target_service}"
        repeat_count = self._action_counts.get(action_key, 0)
        if repeat_count > 2:
            return (
                f"No new information. You have already performed "
                f"{action.action_type} on {action.target_service} "
                f"{repeat_count} times."
            )

        match action.action_type:
            case ActionType.CHECK_LOGS:
                result = self._infra.get_logs(action.target_service)
                self._track_investigation(action.target_service)
            case ActionType.CHECK_METRICS:
                result = self._infra.get_metrics(action.target_service)
                self._track_investigation(action.target_service)
            case ActionType.CHECK_CONFIG:
                result = self._infra.get_config(action.target_service)
                self._track_investigation(action.target_service)
            case ActionType.CHECK_DEPENDENCIES:
                result = self._infra.get_dependencies(action.target_service)
            case ActionType.RUN_DIAGNOSTIC:
                result = self._infra.run_diagnostic(
                    action.target_service, action.parameters
                )
                self._track_investigation(action.target_service)
            case ActionType.RESTART_SERVICE:
                result = self._infra.restart_service(action.target_service)
            case ActionType.SCALE_SERVICE:
                result = self._infra.scale_service(
                    action.target_service, action.parameters
                )
            case ActionType.ROLLBACK_DEPLOY:
                result = self._infra.rollback_deploy(action.target_service)
            case ActionType.UPDATE_CONFIG:
                result = self._infra.update_config(
                    action.target_service, action.parameters
                )
            case ActionType.SUBMIT_DIAGNOSIS:
                result = self._handle_diagnosis(action.parameters)
            case _:
                result = f"Unknown action type: {action.action_type}"

        return result

    def _handle_diagnosis(self, parameters: dict) -> str:
        """Handle diagnosis submission."""
        diagnosis = parameters.get("diagnosis", "")
        if not diagnosis:
            return "ERROR: No diagnosis provided. Include 'diagnosis' in parameters."

        self._state.diagnosis_submitted = True
        self._state.submitted_diagnosis = diagnosis
        return f"Diagnosis submitted: '{diagnosis[:200]}...'" if len(diagnosis) > 200 else f"Diagnosis submitted: '{diagnosis}'"

    def _track_investigation(self, service_name: str) -> None:
        """Track which services the agent has investigated."""
        if service_name not in self._state.services_investigated:
            self._state.services_investigated.append(service_name)

    # ── Per-step reward (dense feedback) ──────────────────────────────

    def _compute_step_reward(self, action: IncidentAction) -> float:
        """Compute intermediate per-step reward for dense RL feedback.

        Provides incremental reward on every step so the training signal
        is not sparse.  The terminal step overrides this with the full
        5-dimensional episode reward from the RewardEngine.

        Reward ranges per step: roughly -0.10 to +0.10.
        """
        assert self._current_scenario is not None

        r = 0.0
        affected = set(self._current_scenario.affected_services)

        investigation_types = {
            ActionType.CHECK_LOGS, ActionType.CHECK_METRICS,
            ActionType.CHECK_CONFIG, ActionType.RUN_DIAGNOSTIC,
        }
        remediation_types = {
            ActionType.RESTART_SERVICE, ActionType.SCALE_SERVICE,
            ActionType.ROLLBACK_DEPLOY, ActionType.UPDATE_CONFIG,
        }

        action_key = f"{action.action_type}:{action.target_service}"
        repeat_count = self._action_counts.get(action_key, 0)

        # ── Investigation rewards ─────────────────────────────────────
        if action.action_type in investigation_types:
            if action.target_service in affected:
                # First time investigating a relevant service → high reward
                if action.target_service not in self._state.services_investigated:
                    r += 0.05
                else:
                    r += 0.01  # Re-investigating (still useful but less)
            else:
                r += 0.01  # Investigating non-affected service

        elif action.action_type == ActionType.CHECK_DEPENDENCIES:
            r += 0.02  # Dependency checking is always somewhat useful

        # ── Remediation rewards / penalties ───────────────────────────
        elif action.action_type in remediation_types:
            if len(self._state.services_investigated) == 0:
                r -= 0.03  # Penalty: remediating before investigating

            correct_actions = set(self._current_scenario.correct_remediation)
            action_str = f"{action.action_type.value}:{action.target_service}"
            if action_str in correct_actions:
                r += 0.08  # Correct remediation action
            elif action.target_service not in affected:
                r -= 0.05  # Destructive action on healthy service

        # ── Repetition penalty ────────────────────────────────────────
        if repeat_count > 2:
            r -= 0.02

        return round(max(-0.10, min(0.10, r)), 4)

    # ── Structured logging ────────────────────────────────────────────

    def _log_start(self) -> None:
        print(
            f"[ENV_START] episode_id={self._state.episode_id} "
            f"scenario={self._state.scenario_name} "
            f"difficulty={self._state.difficulty}",
            file=sys.stderr,
            flush=True,
        )

    def _log_step(self, action: IncidentAction) -> None:
        print(
            f"[ENV_STEP] episode_id={self._state.episode_id} "
            f"step={self._state.step_count} "
            f"action={action.action_type.value} "
            f"target={action.target_service}",
            file=sys.stderr,
            flush=True,
        )

    def _log_end(self, reward: float, breakdown: dict) -> None:
        print(
            f"[ENV_END] episode_id={self._state.episode_id} "
            f"steps={self._state.step_count} "
            f"reward={reward} "
            f"breakdown={breakdown} "
            f"diagnosis_submitted={self._state.diagnosis_submitted}",
            file=sys.stderr,
            flush=True,
        )
