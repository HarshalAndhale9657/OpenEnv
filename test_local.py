"""
IncidentForge Local Test Script
Runs episodes directly (no HTTP server needed) to verify the environment works.
"""

from incident_forge.server.incident_environment import IncidentEnvironment
from incident_forge.models import IncidentAction, ActionType


def divider(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
        print(f"{'='*60}")


def run_episode(difficulty: str = "easy") -> float:
    """Run a full episode and return the reward."""
    env = IncidentEnvironment()

    divider(f"EPISODE — difficulty={difficulty}")

    # --- Reset ---
    obs = env.reset(difficulty=difficulty)
    print(f"\n[ALERT]    {obs.alert_summary}")
    print(f"[AFFECTED] {obs.affected_services}")
    print(f"[SEVERITY] {obs.severity}")

    primary = obs.affected_services[0] if obs.affected_services else "api-gateway"

    # --- Define a scripted investigation sequence ---
    actions = [
        IncidentAction(action_type=ActionType.CHECK_METRICS, target_service=primary, parameters={}),
        IncidentAction(action_type=ActionType.CHECK_LOGS,    target_service=primary, parameters={}),
        IncidentAction(action_type=ActionType.CHECK_CONFIG,  target_service=primary, parameters={}),
        IncidentAction(action_type=ActionType.RUN_DIAGNOSTIC, target_service=primary, parameters={"command": "health_check"}),
        IncidentAction(action_type=ActionType.RESTART_SERVICE, target_service=primary, parameters={}),
        IncidentAction(
            action_type=ActionType.SUBMIT_DIAGNOSIS,
            target_service="",
            parameters={"diagnosis": f"Investigated {primary}: found anomalous metrics and error logs indicating service failure. Restarted service to remediate."}
        ),
    ]

    # --- Step through actions ---
    for i, action in enumerate(actions, 1):
        result = env.step(action)
        print(f"\n[STEP {i}] {action.action_type.value} → {action.target_service}")
        # Truncate long outputs
        snippet = str(result.result)[:250].replace('\n', ' ')
        print(f"  Result : {snippet}...")
        if result.done:
            print(f"\n{'─'*60}")
            print(f"  ✅ Episode DONE!")
            print(f"  💰 Reward  : {result.reward:.4f}")
            breakdown = env.state.reward_breakdown
            if breakdown:
                for k, v in breakdown.items():
                    print(f"     {k:<30} {v:.4f}")
            print(f"  📋 Steps   : {env.state.step_count}")
            print(f"  🔍 Investigated: {env.state.services_investigated}")
            return result.reward or 0.0

    print("  ⚠️  Episode did not terminate (shouldn't happen with submit_diagnosis)")
    return 0.0


def main():
    print("🔥 IncidentForge — Local Environment Test")
    print("==========================================")

    rewards = []

    # Run one episode per difficulty
    for diff in ["easy", "medium", "hard"]:
        r = run_episode(diff)
        rewards.append(r)

    divider("SUMMARY")
    labels = ["easy", "medium", "hard"]
    for label, r in zip(labels, rewards):
        bar = "█" * int(r * 20)
        print(f"  {label:<8} {r:.4f}  {bar}")
    print(f"\n  Average reward: {sum(rewards)/len(rewards):.4f}")
    print(f"  Min: {min(rewards):.4f}  Max: {max(rewards):.4f}")


if __name__ == "__main__":
    main()
