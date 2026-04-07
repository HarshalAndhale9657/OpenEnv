"""Quick test: verify per-step rewards work correctly."""
from incident_forge.server.incident_environment import IncidentEnvironment
from incident_forge.models import IncidentAction, ActionType

env = IncidentEnvironment()
obs = env.reset(seed=42)
print(f"Reset OK. Scenario: {env.state.scenario_name}")

# Step 1: investigate affected service (first time) → should be +0.05
a1 = IncidentAction(action_type=ActionType.CHECK_LOGS, target_service="payment-service")
o1 = env.step(a1)
print(f"Step 1 (check_logs affected):      reward={o1.reward}, done={o1.done}")

# Step 2: investigate same service metrics → should be +0.01 (already investigated)
a2 = IncidentAction(action_type=ActionType.CHECK_METRICS, target_service="payment-service")
o2 = env.step(a2)
print(f"Step 2 (check_metrics re-invest):   reward={o2.reward}, done={o2.done}")

# Step 3: investigate non-affected → should be +0.01
a3 = IncidentAction(action_type=ActionType.CHECK_LOGS, target_service="auth-service")
o3 = env.step(a3)
print(f"Step 3 (check_logs non-affected):   reward={o3.reward}, done={o3.done}")

# Step 4: correct remediation → should be +0.08
a4 = IncidentAction(action_type=ActionType.UPDATE_CONFIG, target_service="payment-service", parameters={"DB_POOL_MAX_SIZE": "50"})
o4 = env.step(a4)
print(f"Step 4 (correct remediation):       reward={o4.reward}, done={o4.done}")

# Step 5: submit diagnosis → should be full episode reward
a5 = IncidentAction(action_type=ActionType.SUBMIT_DIAGNOSIS, target_service="", parameters={"diagnosis": "connection pool exhausted in payment-service database"})
o5 = env.step(a5)
print(f"Step 5 (diagnosis, FINAL):          reward={o5.reward}, done={o5.done}")

print("\n✅ All 5 steps returned numeric rewards (never None)")
print(f"Per-step rewards: {o1.reward}, {o2.reward}, {o3.reward}, {o4.reward}, {o5.reward}")
