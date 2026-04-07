import asyncio
import json
from incident_forge.client import IncidentForgeEnv
from incident_forge.models import IncidentAction, ActionType

async def mock_llm_agent(alert_summary, affected_services):
    """
    Simulates an LLM agent that thinks and then picks an action.
    This is just for demonstration without an HF_TOKEN.
    """
    print(f"\n[Mock Agent] Received Alert: {alert_summary}")
    print(f"[Mock Agent] Affected Services: {affected_services}")
    
    # Simple scripted logic for mock
    steps = [
        {"action_type": ActionType.CHECK_METRICS, "target_service": affected_services[0], "reasoning": "Checking metrics of the primary service."},
        {"action_type": ActionType.CHECK_LOGS, "target_service": affected_services[0], "reasoning": "Looking for error patterns in logs."},
        {"action_type": ActionType.SUBMIT_DIAGNOSIS, "target_service": "", "parameters": {"diagnosis": f"Simulated diagnosis for {affected_services[0]} based on metrics and logs."}, "reasoning": "Submitting final diagnosis."}
    ]
    
    for action_data in steps:
        yield IncidentAction(**action_data)

async def run_episode(env_url):
    env = IncidentForgeEnv(base_url=env_url)
    
    # 1. Reset
    result = await env.reset()
    obs = result.observation
    
    print(f"\n{'='*60}")
    print(f"  EPISODE START")
    print(f"{'='*60}")
    
    # 2. Loop with Mock Agent
    async for action in mock_llm_agent(obs.alert_summary, obs.affected_services):
        print(f"\n[Agent Action] {action.reasoning}")
        print(f"  Calling: {action.action_type} on {action.target_service}")
        
        result = await env.step(action)
        obs = result.observation
        
        print(f"  Observation Result Snippet: {obs.result[:100]}...")
        
        if result.done:
            print(f"\n{'─'*60}")
            print(f"  ✅ Episode Finished!")
            print(f"  🏆 Final Reward: {result.reward}")
            break

async def main():
    # Use the Docker container running locally
    URL = "http://localhost:8001"
    print(f"Connecting to environment at {URL}...")
    await run_episode(URL)

if __name__ == "__main__":
    asyncio.run(main())
