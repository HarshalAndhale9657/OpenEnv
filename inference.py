"""
IncidentForge Inference Script
Runs N episodes of the RL loop using an LLM via HF Inference API.
"""
import os
import json
import asyncio
from huggingface_hub import AsyncInferenceClient

from incident_forge import IncidentAction
from incident_forge.client import IncidentForgeEnv

HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL = "Qwen/Qwen2.5-7B-Instruct"
BASE_URL = os.environ.get("ENV_URL", "http://localhost:8000")

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer investigating a production incident.
You must interact with the environment via JSON actions.
The action_type must be one of:
- check_logs: Get recent logs for a target_service
- check_metrics: Get metrics for a target_service
- check_config: Get env/config for a target_service 
- check_dependencies: Check upstream/downstream services for target_service
- run_diagnostic: Run specific diag cmd (e.g., {"command": "health_check"}) in parameters
- restart_service: Restart target_service
- scale_service: Scale up/down by setting {"replicas": N} in parameters
- rollback_deploy: Revert target_service to previous healthy version
- update_config: Adjust config by passing key/value pairs in parameters dict
- submit_diagnosis: Submit your final root cause analysis. Set target_service to "" and pass {"diagnosis": "..."} in parameters. This ends the incident.

You must respond with ONLY valid JSON code representing your next action. Example:
{
  "action_type": "check_logs",
  "target_service": "api-gateway",
  "parameters": {},
  "reasoning": "Starting by checking the gateway logs"
}
"""

def parse_action(content: str) -> IncidentAction:
    content = content.replace("```json", "").replace("```", "").strip()
    data = json.loads(content)
    return IncidentAction(**data)

async def run_episode(client: AsyncInferenceClient, env: IncidentForgeEnv):
    """Run a single episode of incident response."""
    result = await env.reset()
    total_reward = 0
    trajectory = []
    
    # We maintain a transcript of interaction for context
    transcript = f"ALERT RECEIVED: {result.observation.alert_summary}\n"
    
    for step in range(20):
        # Build prompt from environment result and transcript
        obs = result.observation
        transcript += f"\n[Observation Step {step}]\nResult: {obs.result}\nAffected: {obs.affected_services}\n"
        
        try:
            # Query the model
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Current History:\n{transcript}\nWhat is your next JSON action?"}
            ]
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=256
            )
            content = response.choices[0].message.content
            
            # Record it
            transcript += f"\n[Agent Action Step {step}]\n{content}\n"
            
            # Parse action
            action = parse_action(content)
            
            # Step the environment
            result = await env.step(action)
            trajectory.append(action.model_dump())
            
            if result.done:
                total_reward = result.reward
                break
                
        except Exception as e:
            # If the LLM generates bad JSON or crashes, report it
            print(f"Error in episode loop: {e}")
            break
            
    return total_reward, len(trajectory)

async def main():
    if not HF_TOKEN:
         print("Warning: HF_TOKEN not set. Running inference requires a valid Hugging Face token.")
    
    client = AsyncInferenceClient(token=HF_TOKEN)
    env = IncidentForgeEnv(base_url=BASE_URL)
    
    rewards = []
    for i in range(5): # run 5 for demo purposes
        print(f"--- Starting Episode {i+1} ---")
        reward, steps = await run_episode(client, env)
        rew_val = reward if reward is not None else 0
        rewards.append(rew_val)
        print(f"Episode {i+1}: reward={rew_val:.4f}, steps={steps}")
    
    if rewards:
        print(f"\nResults: avg={sum(rewards)/len(rewards):.4f}, "
              f"min={min(rewards):.4f}, max={max(rewards):.4f}")

if __name__ == "__main__":
    asyncio.run(main())
