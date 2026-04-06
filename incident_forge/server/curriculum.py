# incident_forge/server/curriculum.py
"""
Dynamic difficulty curriculum manager.

Tracks agent performance and adjusts difficulty level
to keep the training signal informative.
"""

from __future__ import annotations

from typing import List


class CurriculumManager:
    """Manages difficulty progression based on recent agent performance."""

    LEVELS = ["easy", "medium", "hard"]

    def __init__(self):
        self.current_level: int = 0
        self.history: List[float] = []

    @property
    def difficulty(self) -> str:
        return self.LEVELS[self.current_level]

    def select_difficulty(self) -> str:
        """Return the current difficulty level."""
        return self.difficulty

    def update(self, reward: float) -> None:
        """Record a reward and potentially adjust difficulty.

        Rules:
          - If last 3 avg > 0.7 and not at max → level up
          - If last 3 avg < 0.2 and not at min → level down
          - Otherwise → stay
        """
        self.history.append(reward)

        if len(self.history) >= 3:
            recent_avg = sum(self.history[-3:]) / 3
            if recent_avg > 0.7 and self.current_level < len(self.LEVELS) - 1:
                self.current_level += 1
                self.history.clear()
            elif recent_avg < 0.2 and self.current_level > 0:
                self.current_level -= 1
                self.history.clear()

    def reset(self) -> None:
        """Reset curriculum state."""
        self.current_level = 0
        self.history.clear()
