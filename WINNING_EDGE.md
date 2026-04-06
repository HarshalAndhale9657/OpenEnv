# 🏆 Winning Edge — Differentiators Checklist

> These are the 7 things we MUST do while building that 95% of teams won't.
> Check off each item as we implement it.

---

## 1. [x] Postmortem-Grounded Scenarios
**Impact: 🔥🔥🔥 | Effort: Low**

Base scenarios on REAL published incident postmortems. Cite the actual URL.

Example sources to use:
- Cloudflare outage reports: https://blog.cloudflare.com/tag/post-mortem/
- GitLab incidents: https://about.gitlab.com/handbook/engineering/infrastructure/incident-review/
- AWS post-event summaries
- Google Cloud incident reports
- PagerDuty public postmortems

For each scenario in our environment, add a comment like:
```python
# Inspired by: Cloudflare outage Sept 2023 — BGP route leak
# Source: https://blog.cloudflare.com/...
```

In the README, add a table:
```
| Scenario | Based On | Source |
|---|---|---|
| Connection Pool Exhaustion | GitLab DB saturation 2022 | [link] |
| Cascading Timeout | Cloudflare API gateway 2023 | [link] |
```

**Why this wins:** Judges see this and think "this person understands real incidents, not just theory."

---

## 2. ☐ Run Inference + Show Real Reward Data
**Impact: 🔥🔥🔥 | Effort: Medium**

After building, actually run 30-50 episodes with a model via HF router and collect:
- Average reward per difficulty level
- Reward distribution histogram (even text-based is fine)
- Example of highest-reward trajectory
- Example of lowest-reward trajectory

Add to README:
```
## Benchmark Results

We ran 50 episodes using Qwen-2.5-7B-Instruct via HF Inference API.

| Difficulty | Episodes | Avg Reward | Min | Max | Std Dev |
|---|---|---|---|---|---|
| Easy | 20 | 0.62 | 0.15 | 0.91 | 0.22 |
| Medium | 20 | 0.31 | 0.04 | 0.68 | 0.18 |
| Hard | 10 | 0.08 | 0.00 | 0.23 | 0.09 |

Key findings:
- Reward signal has meaningful variance ✅
- Difficulty levels produce distinct reward distributions ✅
- Model learns investigation patterns on easy scenarios but struggles with hidden root causes ✅
```

**Why this wins:** 99% of teams won't have real data. This proves the environment works.

---

## 3. [x] Procedural Scenario Generation
**Impact: 🔥🔥🔥 | Effort: Medium**

Don't just hardcode 15 scenarios. Build a generator that creates variations:
- Randomize which services are affected
- Randomize metric values within realistic ranges
- Randomize log message ordering and noise
- Add configurable red herrings (false clues in healthy services)
- Use a seed for reproducibility

```python
def generate_scenario(difficulty: str, seed: int) -> Scenario:
    """Procedurally generate an incident scenario.
    
    With 5 root cause templates × 7 services × variable noise = 
    hundreds of unique scenarios from a small codebase.
    """
```

In the README, mention:
> "IncidentForge can generate unlimited unique scenarios from parameterized templates,
> making it suitable for large-scale RL training runs — not just 15 fixed test cases."

**Why this wins:** Judges from Meta/HF know that real training needs millions of episodes. Hardcoded scenarios don't scale.

---

## 4. ☐ Record a Video Demo
**Impact: 🔥🔥 | Effort: Low**

After deploying to HF Spaces, record a 2-3 minute screen recording:

1. Open the Gradio web interface
2. Click Reset — show the alert appearing
3. Step through 4-5 investigation actions
4. Show the reward breakdown
5. Reset with a different difficulty — show a harder scenario

Save as `demo.mp4` and embed in README:
```markdown
## Demo
[Watch the 2-minute walkthrough](link-to-video)
```

**Why this wins:** Judges reviewing 100+ submissions will spend 2 min on yours. Video > reading code.

---

## 5. ☐ Nail Every Technical Detail
**Impact: 🔥🔥 | Effort: Low**

These are FREE points that many teams will lose:

- [ ] Dockerfile is in the **project root** (NOT inside server/)
- [ ] `ENABLE_WEB_INTERFACE=true` is set
- [ ] Reward is **always** between 0.0 and 1.0 (clamped)
- [ ] Structured logs follow EXACT `[START]`/`[STEP]`/`[END]` format
- [ ] Inference script uses **HF Token** (not OpenAI key)
- [ ] `openenv validate` passes with zero errors
- [ ] All Pydantic models have proper type hints and descriptions
- [ ] `pyproject.toml` has correct dependencies
- [ ] README.md is comprehensive but scannable

---

## 6. ☐ Sample Trajectory in README
**Impact: 🔥🔥 | Effort: Low**

Add a full JSON transcript of one episode to the README:

```json
{
  "episode_id": "ep_001",
  "difficulty": "easy",
  "scenario": "connection_pool_exhaustion",
  "steps": [
    {
      "step": 1,
      "action": {"action_type": "check_logs", "target_service": "payment-service"},
      "observation": {"result": "[ERROR] Connection pool exhausted..."},
      "reward": null
    },
    ...
  ],
  "final_reward": 0.92,
  "reward_breakdown": {
    "investigation": 0.95,
    "diagnosis": 0.98,
    "remediation": 1.0,
    "efficiency": 0.75,
    "safety": 1.0
  }
}
```

**Why this wins:** Lets judges understand your environment in 30 seconds without reading code.

---

## 7. ☐ "Why This Matters for Post-Training" Section
**Impact: 🔥🔥 | Effort: Low**

Add this to README — speaks directly to evaluators:

> "Current post-training pipelines at frontier labs use hundreds of thousands of 
> environments, but they're heavily skewed toward math, coding, and instruction-following. 
> IncidentForge adds a completely new capability axis — operational reasoning under 
> uncertainty — that cannot be learned from static datasets.
> 
> The multi-dimensional reward signal enables process supervision (rewarding investigation 
> quality, not just final answers), which aligns with recent research on outcome vs. 
> process reward models (Lightman et al., 2023).
> 
> Key properties that make IncidentForge valuable for post-training:
> - Partial observability forces active information gathering (not pattern matching)
> - Multiple valid solution paths prevent reward hacking through memorization
> - Safety constraints teach the model risk-aware decision making
> - Curriculum learning ensures continuous training signal at all model capability levels"

---

## Priority Order (What to do when)

| When | What | Status |
|---|---|---|
| During core build | #5 Technical details | ☐ |
| During scenario creation | #1 Postmortem grounding | [x] |
| During scenario creation | #3 Procedural generation | [x] |
| After environment works | #6 Sample trajectory | ☐ |
| After deployment | #2 Run inference + data | ☐ |
| After deployment | #4 Record video | ☐ |
| Final polish | #7 Post-training section | ☐ |

---

*Reference this file at every major milestone to make sure we're not just building — we're building to WIN.*
