# incident_forge/server/app.py
"""
FastAPI application entry point for IncidentForge.

Uses OpenEnv's create_app() to expose reset/step/state endpoints,
with optional web interface via ENABLE_WEB_INTERFACE=true.
"""

from openenv.core.env_server import create_app

from ..models import IncidentAction, IncidentObservation
from .incident_environment import IncidentEnvironment

# create_app expects a FACTORY (callable), not an instance.
# It will call IncidentEnvironment() to create new instances per session.
app = create_app(
    env=IncidentEnvironment,
    action_cls=IncidentAction,
    observation_cls=IncidentObservation,
    env_name="IncidentForge",
)
