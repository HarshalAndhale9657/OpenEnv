---
title: OpenEnv Test
emoji: 🔥
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# 🚀 IncidentForge — Production Incident Response RL Environment

This is a sandboxed microservice simulation where an LLM agent receives production alerts and must investigate, diagnose, and remediate incidents.

### 🎮 How to use:
1. **The Server**: Runs on port 8000 (via Docker).
2. **The API**:
   - `POST /reset`: Start a fresh incident.
   - `POST /step`: Perform an action (e.g., `check_logs`, `check_metrics`).
   - `GET /health`: Check status.

### 📁 Structure:
- `incident_forge/`: Core logic and simulator.
- `inference.py`: Python script to run an LLM agent against this space.
- `Dockerfile`: Production deployment configuration.
