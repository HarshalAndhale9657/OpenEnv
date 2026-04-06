# incident_forge/client.py
"""
IncidentForge EnvClient — typed client for connecting to a running server.

Provides typed action/observation handling for the IncidentForge environment.
"""

from typing import Any, Dict

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import IncidentAction, IncidentObservation, IncidentState


class IncidentForgeEnv(EnvClient[IncidentAction, IncidentObservation, IncidentState]):
    """Typed client for interacting with a running IncidentForge server."""

    def _step_payload(self, action: IncidentAction) -> Dict[str, Any]:
        """Serialize action to JSON dict for the server."""
        return action.model_dump()

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[IncidentObservation]:
        """Parse server response into typed StepResult."""
        obs_data = payload.get("observation", {})
        obs = IncidentObservation(**obs_data)
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> IncidentState:
        """Parse state response into typed IncidentState."""
        return IncidentState(**payload)
