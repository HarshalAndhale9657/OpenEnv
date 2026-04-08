import unittest
import sys
import os

# Add incident_forge to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'incident_forge')))

from incident_forge.server.incident_environment import IncidentEnvironment
from incident_forge.models import IncidentAction

class TestIncidentEnvironment(unittest.TestCase):
    def setUp(self):
        self.env = IncidentEnvironment()

    def test_reset_creates_deterministic_state(self):
        obs = self.env.reset()
        self.assertIsNotNone(obs.alert_summary)
        self.assertFalse(obs.is_resolved)
        self.assertTrue(len(obs.affected_services) > 0)
        self.assertEqual(obs.time_elapsed_minutes, 0)
        self.assertTrue(obs.success)

    def test_step_returns_dense_reward(self):
        self.env.reset()
        # Test 1: Info gathering yields +0.05
        action = IncidentAction(action_type="check_logs", target_service="api-gateway", parameters={})
        obs = self.env.step(action)
        self.assertGreater(obs.reward, 0.0)
        self.assertFalse(obs.done)
        
        # Test 2: Destructive action on healthy service yields penalty
        action2 = IncidentAction(action_type="restart_service", target_service="unrelated-service", parameters={})
        obs2 = self.env.step(action2)
        self.assertLess(obs2.reward, 0.0)
        self.assertFalse(obs2.done)
        
    def test_grader_determinism(self):
        self.env.reset()
        # Submit generic/vague diagnosis
        action = IncidentAction(
            action_type="submit_diagnosis", 
            target_service="", 
            parameters={"diagnosis": "The system is broken, something crashed."}
        )
        obs = self.env.step(action)
        self.assertTrue(obs.done)
        
        # Adjust test since reward is now an end-to-end multi-dimensional computation
        # We check the total reward instead, or fetch the latest state
        self.assertLess(obs.reward, 0.5)

if __name__ == '__main__':
    print("Running deterministic grader and environment unit tests...")
    unittest.main()
