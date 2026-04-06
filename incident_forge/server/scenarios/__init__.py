# incident_forge/server/scenarios/__init__.py
"""Scenario definitions for IncidentForge."""

from .easy import EASY_SCENARIOS
from .medium import MEDIUM_SCENARIOS
from .hard import HARD_SCENARIOS

ALL_SCENARIOS = EASY_SCENARIOS + MEDIUM_SCENARIOS + HARD_SCENARIOS

__all__ = ["EASY_SCENARIOS", "MEDIUM_SCENARIOS", "HARD_SCENARIOS", "ALL_SCENARIOS"]
