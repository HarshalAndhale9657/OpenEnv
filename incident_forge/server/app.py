# incident_forge/server/app.py
"""
FastAPI application entry point for IncidentForge.

Uses OpenEnv's create_app() to expose reset/step/state endpoints,
with optional web interface via ENABLE_WEB_INTERFACE=true.
"""

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Optional Web Interface / Dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.get("/ui")
async def ui_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "UI dashboard not deployed or built."}

