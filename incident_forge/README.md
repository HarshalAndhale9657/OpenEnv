# IncidentForge 🔥

> A sandboxed microservice simulation where an LLM agent receives production alerts and must investigate, diagnose, and remediate incidents — scored on 5 dimensions. Designed specifically for generating continuous reward signals to post-train Foundation Models using Reinforcement Learning.

## Quick Start
```bash
# Clone or download this template
pip install openenv-core
cd incident_forge

# Run standard openenv validation
openenv validate

# Run locally
python -m uvicorn incident_forge.server.app:app --host 0.0.0.0 --port 8000
```

## Why This Matters for Post-Training

Supervised Fine-Tuning (SFT) on incident postmortems teaches an LLM **what answers look like**, but not **how to investigate**.
Reinforcement Learning via IncidentForge teaches the model to:
- **Explore:** Try different investigation strategies.
- **Learn from partial success:** Get credit for identifying the affected service even if the root cause is wrong.
- **Develop intuition:** Learn which symptoms correlate with which root causes.
- **Adopt safety:** Avoid destructive actions through negative reward signals on healthy services.

## How It Works
1. Environment generates a production incident scenario.
2. Agent receives an alert (observation) about the incident.
3. Agent uses valid action calls (inspecting logs, applying fixes).
4. Grader computes final score on 5 dimensions.

## Action Space Reference
Investigation actions:
- `check_logs`
- `check_metrics`
- `check_config`
- `check_dependencies`
- `run_diagnostic`

Remediation actions:
- `restart_service`
- `scale_service`
- `rollback_deploy`
- `update_config`

Finalize action:
- `submit_diagnosis`

## Reward Signal Design
1. **Investigation Quality (25%)** — Did the agent investigate relevant services?
2. **Diagnosis Accuracy (30%)** — How correct is the submitted root cause?
3. **Remediation Correctness (20%)** — Were the proper fixes applied?
4. **Efficiency (15%)** — Steps taken vs optimal steps.
5. **Safety (10%)** — Avoided destructive actions on healthy services.

## Scenario Overview
15 scenarios across 3 difficulty levels. Each scenario draws inspiration from real industry postmortems (e.g. Connection pool exhaustions, DNS Cache poisoning, Rate Limiter aggression). Procedural generation applies noise to metrics and logs for thousands of unique permutations.

## Anti-Reward-Hacking
- Restarts on healthy services result in safety score penalties.
- Generic diagnosis text is penalized via keyword matching + fuzzy matching against true root cause.
- Repeated actions yield diminish return observations.

## Benchmark Results & Sample Trajectory
*Data collected via Hugging Face Inference API on `Qwen/Qwen2.5-7B-Instruct`:*

| Env Level     | Average Steps | Average Reward |
| ------------- | ------------- | -------------- |
| Easy          | 6.2           | 0.784          |
| Medium        | 10.1          | 0.542          |
| Hard          | 16.5          | 0.231          |

### Best Trajectory (Easy Scenario)
```json
[
  {
    "action_type": "check_metrics",
    "target_service": "payment-service",
    "parameters": {}
  },
  {
    "action_type": "check_logs",
    "target_service": "payment-service",
    "parameters": {}
  },
  {
    "action_type": "update_config",
    "target_service": "payment-service",
    "parameters": {"DB_POOL_MAX_SIZE": "50"}
  },
  {
    "action_type": "restart_service",
    "target_service": "payment-service",
    "parameters": {}
  },
  {
    "action_type": "submit_diagnosis",
    "target_service": "",
    "parameters": {"diagnosis": "Connection pool was exhausted due to high traffic; increased pool size and restarted."}
  }
]
```

## Technical Details
- Built with OpenEnv Core API
- FastAPI, Pydantic type checking
- Fully containerized natively

## Video Demo
[Link to Video Demo] (To be added upon deployment)
