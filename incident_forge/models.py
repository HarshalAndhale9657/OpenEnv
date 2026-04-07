# incident_forge/models.py
"""
IncidentForge — Pydantic models for Action, Observation, and State.

These define the contract between agent and environment.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator
import json

from openenv.core.env_server import Action, Observation, State


class ActionType(str, Enum):
    """All possible agent actions in the incident response environment."""

    CHECK_LOGS = "check_logs"
    CHECK_METRICS = "check_metrics"
    CHECK_CONFIG = "check_config"
    CHECK_DEPENDENCIES = "check_dependencies"
    RUN_DIAGNOSTIC = "run_diagnostic"
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOY = "rollback_deploy"
    UPDATE_CONFIG = "update_config"
    SUBMIT_DIAGNOSIS = "submit_diagnosis"


class IncidentAction(Action):
    """Agent action in the incident response environment.

    The agent chooses an action_type and a target_service, with optional
    parameters and reasoning.
    """

    action_type: ActionType = Field(
        ..., description="Type of action to take"
    )
    target_service: str = Field(
        default="", description="Service to act on (leave empty for submit_diagnosis)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters (e.g., diagnosis text, config changes, replica count)",
    )
    reasoning: str = Field(
        default="", description="Agent's reasoning for this action (optional)"
    )

    @field_validator("parameters", mode="before")
    @classmethod
    def parse_params(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            if not v.strip():
                return {}
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Parameters must be a valid JSON dictionary")
        return v or {}


class IncidentObservation(Observation):
    """Observation returned after each agent action.

    Inherits `done`, `reward`, and `metadata` from openenv Observation base.
    """

    result: str = Field(
        default="", description="Result of the action taken"
    )
    alert_summary: str = Field(
        default="", description="Current active alerts across all services"
    )
    affected_services: List[str] = Field(
        default_factory=list, description="List of services currently impacted"
    )
    severity: str = Field(
        default="medium", description="Current incident severity: low/medium/high/critical"
    )
    time_elapsed_minutes: int = Field(
        default=0, description="Simulated time elapsed since incident start"
    )
    is_resolved: bool = Field(
        default=False, description="Whether the incident has been resolved"
    )
    success: bool = Field(
        default=True, description="Whether the action itself succeeded"
    )


class IncidentState(State):
    """Internal state of an incident episode.

    Inherits `episode_id` and `step_count` from openenv State base.
    """

    scenario_id: str = Field(default="", description="ID of the current scenario")
    scenario_name: str = Field(default="", description="Human-readable scenario name")
    difficulty: str = Field(default="easy", description="easy/medium/hard")
    root_cause: str = Field(
        default="", description="Ground truth root cause (hidden from agent)"
    )
    max_steps: int = Field(default=20, description="Maximum steps per episode")
    services_investigated: List[str] = Field(
        default_factory=list,
        description="Services the agent has queried (logs/metrics/config)",
    )
    actions_taken: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of all actions taken"
    )
    diagnosis_submitted: bool = Field(
        default=False, description="Whether the agent has submitted a diagnosis"
    )
    submitted_diagnosis: str = Field(
        default="", description="Text of the submitted diagnosis"
    )
    incident_resolved: bool = Field(
        default=False, description="Whether correct remediation was applied"
    )
    reward_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension reward scores (populated at episode end)",
    )
