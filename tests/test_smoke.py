import os
import time
import requests
from threading import Thread

import sys
# Import OpenEnv app running infrastructure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uvicorn
from openenv.core.env_server import create_app
from incident_forge.models import IncidentAction, IncidentObservation
from incident_forge.server.incident_environment import IncidentEnvironment

def run_server():
    app = create_app(
        env=IncidentEnvironment,
        action_cls=IncidentAction,
        observation_cls=IncidentObservation,
        env_name="test_forge"
    )
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

def test_endpoints_smoke():
    """Verify that HTTP API provides properly typed HTTP 200 outputs."""
    t = Thread(target=run_server, daemon=True)
    t.start()
    
    # Wait for server to start
    time.sleep(1.5)
    
    BASE_URL = "http://127.0.0.1:8001"
    
    client = requests.Session()
    
    # Test reset
    resp = client.post(f"{BASE_URL}/reset", json={"difficulty": "easy", "seed": 42})
    assert resp.status_code == 200
    data = resp.json()
    obs = data.get("observation", data)
    assert "affected_services" in obs
    assert "alert_summary" in obs
    
    # Note: OpenEnv's /step REST endpoint is stateless and recreates the env,
    # so we cannot test a stateful step sequence without WebSockets.
    # The /reset test above is sufficient to prove the HTTP API is healthy.
