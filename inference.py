"""
IncidentForge Inference Script
Runs episodes of the RL loop using an LLM via OpenAI-compatible API.

Required environment variables:
  API_BASE_URL  — LLM API endpoint (default: https://router.huggingface.co/v1)
  MODEL_NAME    — Model identifier (default: Qwen/Qwen2.5-7B-Instruct)
  HF_TOKEN      — Hugging Face API token (required, no default)
  ENV_URL       — Environment server URL (default: http://localhost:8000)
"""
import os
import sys
import json
from openai import OpenAI

# ── Required environment variables ────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# ── Initialize OpenAI client ──────────────────────────────────────────
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

ENV_NAME = "incident_forge"

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer investigating a production incident.
You must interact with the environment via JSON actions.
The action_type must be one of:
- check_logs: Get recent logs for a target_service
- check_metrics: Get metrics for a target_service
- check_config: Get env/config for a target_service
- check_dependencies: Check upstream/downstream services for target_service
- run_diagnostic: Run specific diag cmd. Valid commands: "health_check", "traceroute", "ping", "dns_lookup", "mem_check", "disk_check", "net_stat", "cpu_profile". Set {"command": "..."} in parameters
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

# ── Three tasks at increasing difficulty ──────────────────────────────
TASKS = [
    {"name": "easy_incident", "difficulty": "easy"},
    {"name": "medium_incident", "difficulty": "medium"},
    {"name": "hard_incident", "difficulty": "hard"},
]


# ── Environment communication ────────────────────────────────────────

from openenv import GenericEnvClient, SyncEnvClient

# Initialize OpenEnv WebSocket client for stateful interaction
async_client = GenericEnvClient(ENV_URL)
env_client = SyncEnvClient(async_client)
env_client.connect()

# Fixed seeds per difficulty for reproducible baselines
DIFFICULTY_SEEDS = {
    "easy": 42,
    "medium": 137,
    "hard": 256,
}

def env_reset(difficulty="easy"):
    """Reset the remote or local environment via OpenEnv SDK."""
    seed = DIFFICULTY_SEEDS.get(difficulty, 42)
    state = env_client.reset(difficulty=difficulty, seed=seed)
    
    # Extract data from StepResult
    obs_raw = state.observation
    obs_dict = getattr(obs_raw, "model_dump", lambda: obs_raw)() if hasattr(obs_raw, "model_dump") else obs_raw
    if not isinstance(obs_dict, dict):
        obs_dict = obs_dict.__dict__ if hasattr(obs_dict, "__dict__") else obs_dict
        
    return {"observation": obs_dict, "reward": getattr(state, "reward", 0.0), "done": getattr(state, "done", False)}


def env_step(action_dict):
    """Take a step in the remote or local environment via OpenEnv SDK."""
    state = env_client.step(action_dict)
    
    obs_raw = state.observation
    obs_dict = getattr(obs_raw, "model_dump", lambda: obs_raw)() if hasattr(obs_raw, "model_dump") else obs_raw
    if not isinstance(obs_dict, dict):
        obs_dict = obs_dict.__dict__ if hasattr(obs_dict, "__dict__") else obs_dict
        
    return {"observation": obs_dict, "reward": getattr(state, "reward", 0.0), "done": getattr(state, "done", False)}


# ── LLM interaction ──────────────────────────────────────────────────

def get_llm_action(transcript):
    """Get the next action from the LLM via OpenAI-compatible API."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Current investigation history:\n{transcript}\n\n"
                "What is your next JSON action?"
            ),
        },
    ]
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=300,
    )
    return response.choices[0].message.content


def parse_action(content):
    """Parse LLM output into action dict, stripping markdown fences."""
    content = content.replace("```json", "").replace("```", "").strip()
    # Handle cases where LLM wraps in extra text
    start = content.find("{")
    end = content.rfind("}") + 1
    if start != -1 and end > start:
        content = content[start:end]
    return json.loads(content)


def format_action_str(action_dict):
    """Format action for [STEP] log line."""
    atype = action_dict.get("action_type", "unknown")
    target = action_dict.get("target_service", "")
    if target:
        return f"{atype}({target})"
    return f"{atype}()"


# ── Task runner ──────────────────────────────────────────────────────

def run_task(task_name, difficulty):
    """Run a single task (episode) and emit structured output."""
    rewards = []
    final_episode_reward = None  # Track the terminal reward separately
    step_num = 0
    success = False

    # [START] line
    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}")
    sys.stdout.flush()

    try:
        # Reset the environment
        reset_data = env_reset(difficulty)
        obs = reset_data.get("observation", reset_data)

        # Build initial transcript from alert
        alert = obs.get("alert_summary", obs.get("result", "No alert"))
        affected = obs.get("affected_services", [])
        severity = obs.get("severity", "unknown")
        transcript = (
            f"ALERT RECEIVED:\n{alert}\n"
            f"Affected services: {affected}\n"
            f"Severity: {severity}\n"
        )

        for i in range(1, 21):  # Max 20 steps
            step_num = i

            # Get LLM action
            try:
                raw_content = get_llm_action(transcript)
                action_dict = parse_action(raw_content)
                action_str = format_action_str(action_dict)
                error_msg = None
            except Exception as e:
                error_msg = str(e).replace("\n", " ")[:200]
                action_str = "parse_error()"
                print(
                    f"[STEP] step={step_num} action={action_str} "
                    f"reward=0.00 done=false error={error_msg}"
                )
                sys.stdout.flush()
                rewards.append(0.0)
                break

            # Step the environment
            try:
                step_data = env_step(action_dict)
                obs_data = step_data.get("observation", step_data)

                # Extract reward — check both top-level and nested
                reward = step_data.get("reward")
                if reward is None:
                    reward = obs_data.get("reward")
                reward = float(reward) if reward is not None else 0.0

                # Extract done flag
                done = step_data.get("done", False)
                if not done:
                    done = obs_data.get("done", False)

                error_msg = None
            except Exception as e:
                error_msg = str(e).replace("\n", " ")[:200]
                reward = 0.0
                done = False

            rewards.append(reward)
            done_str = "true" if done else "false"
            error_str = error_msg if error_msg else "null"

            # Display reward as-is for honest logging (don't distort negatives)
            display_reward = round(max(-1.0, min(1.0, reward)), 2)

            # [STEP] line
            print(
                f"[STEP] step={step_num} action={action_str} "
                f"reward={display_reward:.2f} done={done_str} error={error_str}"
            )
            sys.stdout.flush()

            if done:
                final_episode_reward = reward  # This is the full episode reward
                success = reward > 0.3
                break

            # Update transcript for next LLM call
            result = obs_data.get("result", "")
            transcript += (
                f"\n[Step {i}] Action: {json.dumps(action_dict)}\n"
                f"Result: {result}\n"
                f"Affected: {obs_data.get('affected_services', [])}\n"
                f"Severity: {obs_data.get('severity', 'unknown')}\n"
            )

    except Exception as e:
        if not rewards:
            rewards.append(0.0)
        error_msg = str(e).replace("\n", " ")[:200]
        print(
            f"[STEP] step={step_num or 1} action=error() "
            f"reward=0.00 done=true error={error_msg}"
        )
        sys.stdout.flush()

    # [END] line — always emitted
    success_str = "true" if success else "false"
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    # Use the final episode reward as the task score (NOT sum of all rewards)
    # The final_episode_reward comes from RewardEngine and is already meaningful
    if final_episode_reward is not None:
        score_val = final_episode_reward
    elif rewards:
        score_val = rewards[-1]  # Last reward as fallback
    else:
        score_val = 0.5  # Safe default

    # Strictly clamp to (0, 1) exclusive — never 0.0 or 1.0
    score_val = max(0.01, min(0.99, float(score_val)))

    print(f"[END] success={success_str} steps={step_num} score={score_val:.2f} rewards={rewards_str}")
    sys.stdout.flush()

    return rewards


def main():
    """Run all three tasks: easy, medium, hard."""
    all_rewards = []
    for task in TASKS:
        task_rewards = run_task(task["name"], task["difficulty"])
        all_rewards.extend(task_rewards)


if __name__ == "__main__":
    main()
