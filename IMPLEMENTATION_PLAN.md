# IncidentForge — Complete Implementation Plan

> **Start:** April 7, 2026 ~2:15 AM IST
> **Deadline:** April 8, 2026 11:59 PM IST
> **Available Time:** ~46 hours
> **Strategy:** Build in 6 phases. Each phase produces a WORKING state. Never be in a broken state for more than 30 minutes.

---

## Final File Structure (What We're Building)

```
d:\openEnv\incident_forge\
├── .dockerignore
├── __init__.py                          # Exports: IncidentAction, IncidentObservation, IncidentForgeEnv
├── models.py                            # Pydantic: Action, Observation, State
├── client.py                            # IncidentForgeEnv(EnvClient)
├── openenv.yaml                         # Environment manifest
├── pyproject.toml                       # Package config + dependencies
├── README.md                            # Comprehensive documentation (WINNING EDGE)
├── outputs/
│   ├── logs/
│   └── evals/
└── server/
    ├── __init__.py
    ├── app.py                           # FastAPI app (create_fastapi_app)
    ├── incident_environment.py          # Main Environment class (reset/step/state)
    ├── infrastructure_sim.py            # 7-service microservice simulator
    ├── scenario_engine.py               # Scenario definitions + procedural generation
    ├── reward_engine.py                 # 5-dimensional reward computation
    ├── curriculum.py                    # Dynamic difficulty manager
    ├── log_generator.py                 # Realistic log message generation
    ├── scenarios/                       # Scenario template data
    │   ├── __init__.py
    │   ├── easy.py                      # 5 easy scenarios
    │   ├── medium.py                    # 5 medium scenarios
    │   └── hard.py                      # 5 hard scenarios
    ├── requirements.txt
    └── Dockerfile
```

Additionally at the project root level:
```
d:\openEnv\
├── incident_forge/                      # (above)
├── inference.py                         # Mandatory inference script (HF router)
├── Dockerfile                           # Root-level Dockerfile for HF Spaces
├── PROBLEM_STATEMENT.md                 # Already done
├── WINNING_EDGE.md                      # Already done
└── problem.md                           # Already done
```

---

## Phase 1: Foundation & Scaffolding (2-3 hours)
**Goal:** Get a working skeleton that passes `openenv validate`

### Step 1.1: Install OpenEnv
```bash
pip install openenv-core
```

### Step 1.2: Initialize project
```bash
cd d:\openEnv
openenv init incident_forge
```
> If `openenv init` doesn't work on Windows, manually create the structure following the exact OpenEnv pattern from the `envs/` README.

### Step 1.3: Define models.py
This is the **contract** of our environment. Every field must have clear types and descriptions.

```python
# incident_forge/models.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from openenv.core.env_server import Action, Observation, State


class ActionType(str, Enum):
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
    """Agent action in the incident response environment."""
    action_type: ActionType = Field(..., description="Type of action to take")
    target_service: str = Field(..., description="Service to act on")
    parameters: dict = Field(default_factory=dict, description="Additional parameters")
    reasoning: str = Field("", description="Agent's reasoning for this action")


class IncidentObservation(Observation):
    """Observation returned after each agent action."""
    result: str = Field(..., description="Result of the action")
    alert_summary: str = Field("", description="Current active alerts")
    affected_services: list[str] = Field(default_factory=list)
    severity: str = Field("medium", description="low/medium/high/critical")
    time_elapsed_minutes: int = Field(0)
    is_resolved: bool = Field(False)
    success: bool = Field(True)


class IncidentState(State):
    """Internal state of an incident episode."""
    episode_id: str = ""
    step_count: int = 0
    scenario_id: str = ""
    scenario_name: str = ""
    difficulty: str = "easy"
    root_cause: str = ""              # Hidden from agent
    max_steps: int = 20
    services_investigated: list[str] = Field(default_factory=list)
    actions_taken: list[dict] = Field(default_factory=list)
    diagnosis_submitted: bool = False
    submitted_diagnosis: str = ""
    incident_resolved: bool = False
    done: bool = False
```

### Step 1.4: Create server/app.py
```python
# incident_forge/server/app.py
from openenv.core.env_server import create_fastapi_app
from ..models import IncidentAction, IncidentObservation
from .incident_environment import IncidentEnvironment

env = IncidentEnvironment()
app = create_fastapi_app(env, IncidentAction, IncidentObservation)
```

### Step 1.5: Create minimal incident_environment.py
Start with a BARE MINIMUM that compiles and returns valid responses:
```python
# incident_forge/server/incident_environment.py
import uuid
from openenv.core.env_server import Environment
from ..models import IncidentAction, IncidentObservation, IncidentState


class IncidentEnvironment(Environment):
    def __init__(self):
        super().__init__()
        self._state = IncidentState()

    def reset(self) -> IncidentObservation:
        self._state = IncidentState(episode_id=str(uuid.uuid4()))
        # Initial alert
        return IncidentObservation(
            result="Environment ready. Incident alert incoming.",
            alert_summary="ALERT: payment-service error rate elevated",
            affected_services=["payment-service"],
            severity="high",
            success=True
        )

    def step(self, action: IncidentAction) -> IncidentObservation:
        self._state.step_count += 1
        # Placeholder - will be replaced in Phase 2
        return IncidentObservation(
            result=f"Action {action.action_type} on {action.target_service} executed.",
            success=True
        )

    @property
    def state(self) -> IncidentState:
        return self._state
```

### Step 1.6: Create client.py
```python
# incident_forge/client.py
from openenv.core import EnvClient, StepResult
from .models import IncidentAction, IncidentObservation, IncidentState


class IncidentForgeEnv(EnvClient[IncidentAction, IncidentObservation, IncidentState]):
    def _step_payload(self, action: IncidentAction) -> dict:
        return action.model_dump()

    def _parse_result(self, payload: dict) -> StepResult[IncidentObservation]:
        obs = IncidentObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> IncidentState:
        return IncidentState(**payload)
```

### Step 1.7: Create __init__.py
```python
# incident_forge/__init__.py
from .models import IncidentAction, IncidentObservation, IncidentState
from .client import IncidentForgeEnv

__all__ = ["IncidentAction", "IncidentObservation", "IncidentState", "IncidentForgeEnv"]
```

### Step 1.8: Create pyproject.toml, openenv.yaml
Minimal but correct configurations.

### ✅ Phase 1 Gate Check
- [ ] `python -c "from incident_forge import *"` works
- [ ] Server starts: `uvicorn incident_forge.server.app:app --host 0.0.0.0 --port 8000`
- [ ] Can hit `/reset` and `/step` endpoints
- [ ] 🏆 **WINNING EDGE #5:** All technical details correct from the start

---

## Phase 2: Infrastructure Simulator (3-4 hours)
**Goal:** Build the simulated 7-service microservice architecture

### Step 2.1: infrastructure_sim.py
This is the **core simulation**. Each service has state that can be queried.

```python
# Key classes to implement:
class ServiceState:
    """State of a single microservice."""
    name: str
    health: str                # healthy/degraded/unhealthy/unreachable
    cpu_percent: float
    memory_percent: float
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate_percent: float
    request_rate_per_sec: float
    db_connections_active: int
    db_connections_max: int
    disk_usage_percent: float
    uptime_hours: float
    config: dict               # Environment variables
    dependencies: list[str]    # Upstream services
    dependents: list[str]      # Downstream services
    logs: list[str]            # Recent log entries
    recent_deployments: list   # Deployment history


class InfrastructureSimulator:
    """Simulates a 7-service microservices architecture."""
    
    def __init__(self):
        self.services = self._init_services()
    
    def _init_services(self) -> dict[str, ServiceState]:
        """Create the 7 services with healthy baseline state."""
        # api-gateway, auth-service, user-service, order-service,
        # payment-service, inventory-service, notification-service
    
    def inject_incident(self, scenario: Scenario):
        """Modify service states to simulate an incident."""
    
    def get_logs(self, service_name: str) -> str:
        """Return formatted log entries for a service."""
    
    def get_metrics(self, service_name: str) -> str:
        """Return formatted metrics for a service."""
    
    def get_config(self, service_name: str) -> str:
        """Return configuration for a service."""
    
    def get_dependencies(self, service_name: str) -> str:
        """Return dependency graph for a service."""
    
    def restart_service(self, service_name: str) -> str:
        """Simulate restarting a service."""
    
    def update_config(self, service_name: str, changes: dict) -> str:
        """Simulate config update."""
    
    def apply_fix_effects(self, action, scenario):
        """If the action is a correct remediation, update service health."""
```

### Step 2.2: log_generator.py
Generate realistic, timestamped log entries:
```python
class LogGenerator:
    """Generates realistic production-style log entries."""
    
    def generate_healthy_logs(self, service_name: str, count: int) -> list[str]:
        """Normal operation logs (INFO level, request handling)."""
    
    def generate_error_logs(self, service_name: str, error_pattern: str, count: int) -> list[str]:
        """Error logs matching a specific incident pattern."""
    
    def generate_mixed_logs(self, service_name: str, error_ratio: float) -> list[str]:
        """Mix of normal and error logs."""
```

Log format should look like real production logs:
```
2026-04-07T02:14:33.127Z [INFO]  payment-service | req_id=abc123 | POST /api/v1/charge | 200 | 45ms
2026-04-07T02:14:33.891Z [ERROR] payment-service | req_id=def456 | POST /api/v1/charge | Connection pool exhausted. Max: 10, Active: 10, Waiting: 847
2026-04-07T02:14:34.003Z [WARN]  payment-service | Health check degraded. Error rate: 45.2%
```

### ✅ Phase 2 Gate Check
- [ ] `InfrastructureSimulator()` creates 7 services with realistic baseline
- [ ] Can query logs, metrics, config for each service
- [ ] Can inject a simple incident and see service states change
- [ ] Log format looks like real production logs

---

## Phase 3: Scenarios + Procedural Generation (4-5 hours)
**Goal:** Build 15 scenarios across 3 difficulty levels with procedural variation

### Step 3.1: Define scenario data structure
```python
@dataclass
class Scenario:
    id: str
    name: str
    difficulty: str                    # easy/medium/hard
    description: str                   # Alert message shown to agent
    root_cause: str                    # Ground truth cause
    root_cause_keywords: list[str]     # Keywords for grading
    contributing_factors: list[str]    # Secondary causes
    affected_services: list[str]       # Services in the causal chain
    primary_service: str               # Where the root cause lives
    service_modifications: dict        # How to modify each service state
    correct_remediation: list[str]     # Expected remediation actions ("restart:payment-service")
    optimal_step_count: int            # How many steps an expert would take
    red_herrings: list[dict]           # False clues in unrelated services
    postmortem_source: str             # 🏆 WINNING EDGE #1: Real-world source
```

### Step 3.2: Build 5 Easy scenarios (scenarios/easy.py)
Each with:
- Clear log indicators in the primary service
- Metrics that directly show the problem  
- 1 service affected, maybe 1 downstream cascade
- Optimal in 4-6 steps
- **🏆 WINNING EDGE #1:** Each cites a real postmortem

### Step 3.3: Build 5 Medium scenarios (scenarios/medium.py)
Each with:
- Root cause in one service, symptoms in 2-3 others
- Requires checking multiple services to find the origin
- Some red herrings in metrics
- Optimal in 6-10 steps

### Step 3.4: Build 5 Hard scenarios (scenarios/hard.py)  
Each with:
- Hidden root cause (not obvious from logs alone)
- Requires diagnostics or config inspection
- Multiple red herrings
- Optimal in 8-14 steps

### Step 3.5: 🏆 WINNING EDGE #3 — Procedural Generation
```python
class ScenarioGenerator:
    """Procedurally generates scenario variations."""
    
    def generate(self, difficulty: str, seed: int) -> Scenario:
        """Create a unique scenario from templates + randomization.
        
        Randomizes:
        - Which services are affected (from template options)
        - Metric values within realistic ranges
        - Log message ordering and noise level
        - Number and placement of red herrings
        - Specific config values
        
        Uses seed for reproducibility.
        """
        template = random.choice(TEMPLATES[difficulty])
        return self._instantiate_template(template, seed)
```

### ✅ Phase 3 Gate Check
- [ ] 15 scenarios load and are well-defined
- [ ] Each scenario modifies infrastructure state correctly
- [ ] ScenarioGenerator produces different variations from different seeds
- [ ] Each scenario has a `postmortem_source` citation
- [ ] Running `reset()` loads a scenario and shows a realistic alert

---

## Phase 4: Reward Engine + Full Environment Logic (4-5 hours)
**Goal:** Complete the step() logic and 5-dimensional reward system

### Step 4.1: Wire up step() in incident_environment.py

```python
def step(self, action: IncidentAction) -> IncidentObservation:
    self._state.step_count += 1
    self._state.actions_taken.append(action.model_dump())
    
    # Structured logging: [STEP]
    self._log_step(action)
    
    # Route to handler based on action type
    match action.action_type:
        case ActionType.CHECK_LOGS:
            result = self.infra.get_logs(action.target_service)
            self._track_investigation(action.target_service)
        case ActionType.CHECK_METRICS:
            result = self.infra.get_metrics(action.target_service)
            self._track_investigation(action.target_service)
        case ActionType.CHECK_CONFIG:
            result = self.infra.get_config(action.target_service)
            self._track_investigation(action.target_service)
        case ActionType.CHECK_DEPENDENCIES:
            result = self.infra.get_dependencies(action.target_service)
        case ActionType.RUN_DIAGNOSTIC:
            result = self.infra.run_diagnostic(action.target_service, action.parameters)
            self._track_investigation(action.target_service)
        case ActionType.RESTART_SERVICE:
            result = self.infra.restart_service(action.target_service)
        case ActionType.SCALE_SERVICE:
            result = self.infra.scale_service(action.target_service, action.parameters)
        case ActionType.ROLLBACK_DEPLOY:
            result = self.infra.rollback_deploy(action.target_service)
        case ActionType.UPDATE_CONFIG:
            result = self.infra.update_config(action.target_service, action.parameters)
        case ActionType.SUBMIT_DIAGNOSIS:
            result = self._handle_diagnosis(action.parameters.get("diagnosis", ""))
    
    # Check for repeated actions → diminishing returns
    result = self._apply_repetition_penalty(action, result)
    
    # Compute reward if episode is done
    reward = None
    done = False
    if self._state.diagnosis_submitted or self._state.step_count >= self._state.max_steps:
        reward = self.reward_engine.compute(self._state, self.current_scenario)
        done = True
        self._state.done = True
        self._log_end(reward)
    
    return IncidentObservation(
        result=result,
        alert_summary=self.infra.get_active_alerts(),
        affected_services=self.infra.get_affected_service_names(),
        severity=self.infra.get_current_severity(),
        time_elapsed_minutes=self._state.step_count * 3,
        is_resolved=self._state.incident_resolved,
        success=True
    ), reward, done  # Return as StepResult components
```

### Step 4.2: Build reward_engine.py

```python
class RewardEngine:
    """5-dimensional reward computation."""
    
    WEIGHTS = {
        "investigation": 0.25,
        "diagnosis": 0.30,
        "remediation": 0.20,
        "efficiency": 0.15,
        "safety": 0.10,
    }
    
    def compute(self, state: IncidentState, scenario: Scenario) -> float:
        scores = {
            "investigation": self._score_investigation(state, scenario),
            "diagnosis": self._score_diagnosis(state, scenario),
            "remediation": self._score_remediation(state, scenario),
            "efficiency": self._score_efficiency(state, scenario),
            "safety": self._score_safety(state, scenario),
        }
        
        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        return round(max(0.0, min(1.0, total)), 4)  # Clamp to [0, 1]
    
    def _score_investigation(self, state, scenario) -> float:
        """Proportion of relevant services investigated."""
        relevant = set(scenario.affected_services)
        investigated = set(state.services_investigated)
        if not relevant:
            return 1.0
        return len(relevant & investigated) / len(relevant)
    
    def _score_diagnosis(self, state, scenario) -> float:
        """Keyword matching + fuzzy similarity."""
        if not state.diagnosis_submitted:
            return 0.0
        diagnosis = state.submitted_diagnosis.lower()
        
        # Exact keyword matches
        keywords_found = sum(1 for kw in scenario.root_cause_keywords 
                           if kw.lower() in diagnosis)
        keyword_score = keywords_found / max(len(scenario.root_cause_keywords), 1)
        
        # Fuzzy similarity to root cause description
        from difflib import SequenceMatcher
        fuzzy_score = SequenceMatcher(None, diagnosis, scenario.root_cause.lower()).ratio()
        
        # Contributing factors bonus
        factor_bonus = sum(0.05 for f in scenario.contributing_factors 
                          if f.lower() in diagnosis)
        
        return min(1.0, keyword_score * 0.6 + fuzzy_score * 0.3 + factor_bonus)
    
    def _score_remediation(self, state, scenario) -> float:
        """Overlap between taken actions and correct actions."""
        correct = set(scenario.correct_remediation)
        taken = set()
        for a in state.actions_taken:
            if a["action_type"] in ("restart_service", "scale_service", 
                                      "rollback_deploy", "update_config"):
                key = f"{a['action_type']}:{a['target_service']}"
                taken.add(key)
        if not correct:
            return 1.0
        return len(correct & taken) / len(correct)
    
    def _score_efficiency(self, state, scenario) -> float:
        """Fewer steps = better."""
        optimal = scenario.optimal_step_count
        actual = state.step_count
        max_steps = state.max_steps
        if actual <= optimal:
            return 1.0
        return max(0.0, 1.0 - (actual - optimal) / (max_steps - optimal))
    
    def _score_safety(self, state, scenario) -> float:
        """Penalize destructive actions on healthy services."""
        destructive_types = {"restart_service", "rollback_deploy", "scale_service"}
        affected = set(scenario.affected_services)
        penalties = 0
        for a in state.actions_taken:
            if a["action_type"] in destructive_types:
                if a["target_service"] not in affected:
                    penalties += 1
        return max(0.0, 1.0 - penalties * 0.3)
```

### Step 4.3: Add structured logging
```python
def _log_start(self):
    """[START] log entry."""
    print(f"[START] episode_id={self._state.episode_id} "
          f"scenario={self._state.scenario_name} "
          f"difficulty={self._state.difficulty}")

def _log_step(self, action):
    """[STEP] log entry."""
    print(f"[STEP] episode_id={self._state.episode_id} "
          f"step={self._state.step_count} "
          f"action={action.action_type} "
          f"target={action.target_service}")

def _log_end(self, reward):
    """[END] log entry."""
    print(f"[END] episode_id={self._state.episode_id} "
          f"steps={self._state.step_count} "
          f"reward={reward} "
          f"diagnosis_submitted={self._state.diagnosis_submitted}")
```

### Step 4.4: curriculum.py
```python
class CurriculumManager:
    def __init__(self):
        self.current_level = 0
        self.levels = ["easy", "medium", "hard"]
        self.history = []  # recent rewards
    
    def select_difficulty(self) -> str:
        return self.levels[self.current_level]
    
    def update(self, reward: float):
        self.history.append(reward)
        if len(self.history) >= 3:
            avg = sum(self.history[-3:]) / 3
            if avg > 0.7 and self.current_level < 2:
                self.current_level += 1
                self.history.clear()
            elif avg < 0.2 and self.current_level > 0:
                self.current_level -= 1
                self.history.clear()
```

### ✅ Phase 4 Gate Check
- [ ] Full episode runs: reset() → multiple step() → final reward
- [ ] Reward is always between 0.0 and 1.0
- [ ] Different agent behaviors produce meaningfully different rewards
- [ ] Structured `[START]`/`[STEP]`/`[END]` logs print correctly
- [ ] Curriculum advances difficulty when agent scores well
- [ ] 🏆 **WINNING EDGE #5:** All technical compliance items pass

---

## Phase 5: Docker + Deployment (3-4 hours)
**Goal:** Dockerize, deploy to HF Spaces, verify it works remotely

### Step 5.1: Create Dockerfile (at project root, NOT in server/)

> [!CAUTION]
> The Dockerfile MUST be at the outermost directory level, not inside server/. Many teams get this wrong.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY incident_forge/server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy source
COPY . /app/

# Enable web interface
ENV ENABLE_WEB_INTERFACE=true

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "incident_forge.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 5.2: Create requirements.txt
```
openenv-core>=0.2.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
```

### Step 5.3: Test Docker locally
```bash
docker build -t incident-forge:latest .
docker run -p 8000:8000 incident-forge:latest
# Test: curl http://localhost:8000/health
# Test: open http://localhost:8000/web
```

### Step 5.4: Deploy to Hugging Face Spaces
```bash
cd d:\openEnv\incident_forge
openenv push --repo-id YOUR_USERNAME/incident-forge
```

### Step 5.5: Verify deployed Space
- [ ] Space builds successfully
- [ ] `/health` returns 200
- [ ] Web interface loads at `/web`
- [ ] Can step through an episode via the Gradio UI

### ✅ Phase 5 Gate Check
- [ ] Docker builds and runs locally
- [ ] 🏆 **WINNING EDGE #5:** Dockerfile is at root, web interface enabled
- [ ] HF Space is live and accessible
- [ ] Web interface works on the deployed Space

---

## Phase 6: Inference Script + Polish + Winning Edge (6-8 hours)
**Goal:** Write inference script, run benchmarks, polish README, record demo

### Step 6.1: Write inference.py (MANDATORY)

> [!IMPORTANT]
> Uses HF Token via the HF router. NO OpenAI API key.

```python
"""
IncidentForge Inference Script
Runs N episodes of the RL loop using an LLM via HF Inference API.
"""
import os
import json
from huggingface_hub import InferenceClient
from incident_forge import IncidentAction, IncidentForgeEnv
from incident_forge.models import ActionType

HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL = "Qwen/Qwen2.5-7B-Instruct"
BASE_URL = os.environ.get("ENV_URL", "http://localhost:8000")

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer investigating a 
production incident. You have access to the following tools...
[detailed system prompt with all 10 action types]
Respond with a JSON action object."""

def run_episode(client, env):
    """Run a single episode of incident response."""
    result = env.reset()
    total_reward = 0
    trajectory = []
    
    for step in range(20):
        # Get LLM action
        prompt = format_observation(result.observation)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *trajectory,
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse action from LLM response
        action = parse_action(response.choices[0].message.content)
        
        # Step environment
        result = env.step(action)
        trajectory.append(...)
        
        if result.done:
            total_reward = result.reward
            break
    
    return total_reward, len(trajectory)

def main():
    client = InferenceClient(token=HF_TOKEN)
    env = IncidentForgeEnv(base_url=BASE_URL).sync()
    
    rewards = []
    for i in range(30):
        reward, steps = run_episode(client, env)
        rewards.append(reward)
        print(f"Episode {i+1}: reward={reward:.4f}, steps={steps}")
    
    print(f"\nResults: avg={sum(rewards)/len(rewards):.4f}, "
          f"min={min(rewards):.4f}, max={max(rewards):.4f}")
```

### Step 6.2: 🏆 WINNING EDGE #2 — Run Inference + Collect Data
```bash
HF_TOKEN=hf_xxx ENV_URL=https://YOUR-SPACE.hf.space python inference.py
```

Collect and save results for the README:
- Average reward per difficulty
- Min/max/std dev
- Best trajectory example
- Worst trajectory example

### Step 6.3: 🏆 WINNING EDGE #6 — Add Sample Trajectory to README
Take the best episode from inference results and format as a JSON transcript in the README.

### Step 6.4: 🏆 WINNING EDGE #4 — Record Video Demo
1. Open the deployed HF Space web interface
2. Screen record a 2-3 minute walkthrough
3. Show: reset → investigate → diagnose → reward
4. Upload and link in README

### Step 6.5: 🏆 WINNING EDGE #7 — Write "Why This Matters" Section
Add the post-training research perspective to README.

### Step 6.6: Polish README.md
Final README structure:
```
1. Hero banner + one-line description
2. Quick Start (3 lines of code)
3. Why This Environment Matters for Post-Training
4. How It Works (with episode diagram)
5. Action Space Reference
6. Reward Signal Design (5 dimensions explained)
7. Scenario Overview (with postmortem citations)
8. Sample Trajectory (real JSON from inference)
9. Benchmark Results (real data from inference)
10. Curriculum Learning
11. Anti-Reward-Hacking
12. Technical Details (Docker, deployment)
13. Known Limitations & Future Work
```

### Step 6.7: Final validation
```bash
openenv validate
```

### ✅ Phase 6 Gate Check
- [ ] Inference script runs successfully with HF router
- [ ] 🏆 **WINNING EDGE #2:** Real benchmark data in README
- [ ] 🏆 **WINNING EDGE #4:** Video demo recorded and linked
- [ ] 🏆 **WINNING EDGE #6:** Sample trajectory in README
- [ ] 🏆 **WINNING EDGE #7:** Post-training section written
- [ ] `openenv validate` passes
- [ ] Final submission URL saved

---

## Time Budget Summary

| Phase | Hours | Cumulative | Deadline Buffer |
|---|---|---|---|
| Phase 1: Foundation | 2-3h | 3h | 43h left |
| Phase 2: Infrastructure | 3-4h | 7h | 39h left |
| Phase 3: Scenarios | 4-5h | 12h | 34h left |
| Phase 4: Reward + Logic | 4-5h | 17h | 29h left |
| Phase 5: Docker + Deploy | 3-4h | 21h | 25h left |
| Phase 6: Inference + Polish | 6-8h | 29h | 17h left |
| **Buffer for bugs/issues** | **~17h** | | **Safe margin** |

> [!TIP]
> The 17-hour buffer is critical. Docker issues, HF Space build failures, and inference script debugging ALWAYS take longer than expected. Do not skip the buffer.

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Docker build fails on HF Spaces | High | Critical | Test locally first. Keep Dockerfile minimal. |
| OpenEnv API changes/quirks on Windows | Medium | High | We reference the exact patterns from `envs/` README |
| Inference script can't connect to Space | Medium | High | Test with local server first, then swap URL |
| Reward always returns same value | Low | Critical | Test with 3+ different agent behaviors in Phase 4 |
| Running out of time | Medium | Critical | Every phase gate produces a working, submittable state |

---

## Winning Edge Checkpoint — Integrated into Phases

| # | Winning Edge | Integrated In | Status |
|---|---|---|---|
| 1 | Postmortem-grounded scenarios | Phase 3 | ☐ |
| 2 | Real inference benchmark data | Phase 6 | ☐ |
| 3 | Procedural scenario generation | Phase 3 | ☐ |
| 4 | Video demo recording | Phase 6 | ☐ |
| 5 | Technical detail perfection | Phase 1 + throughout | ☐ |
| 6 | Sample trajectory in README | Phase 6 | ☐ |
| 7 | Post-training significance section | Phase 6 | ☐ |

---

## Submission Checklist (Before April 8 11:59 PM IST)

- [ ] `openenv validate` passes
- [ ] Docker builds locally
- [ ] HF Space is live and responsive
- [ ] Web interface works (`/web` endpoint)
- [ ] Inference script runs with HF Token
- [ ] README has benchmark data
- [ ] README has sample trajectory
- [ ] README has postmortem citations
- [ ] README has "Why This Matters for Post-Training" section
- [ ] Reward is always 0.0–1.0
- [ ] Structured logs follow `[START]`/`[STEP]`/`[END]` format
- [ ] HF Space URL submitted on the platform
- [ ] Video demo linked in README (if time permits)
