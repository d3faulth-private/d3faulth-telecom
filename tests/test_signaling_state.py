import unittest
from d3faulth_telecom.signaling_state import State

class SignalingStateTests(unittest.TestCase):
    def test_aspup_ack_does_not_mean_active(self):
        state = State()
        state.transport(True)
        state.observe(3, 4)
        self.assertEqual(state.asp, "UP")
        self.assertEqual(state.routing, "UNVERIFIED")
    def test_activation_requires_prior_up(self):
        state = State()
        state.transport(True)
        state.observe(4, 3)
        self.assertEqual(state.asp, "DOWN")
        self.assertIn("without prior", state.error)
    def test_active_requires_explicit_ack(self):
        state = State()
        state.transport(True)
        state.observe(3, 4)
        state.observe(4, 3)
        self.assertEqual(state.asp, "ACTIVE")
        self.assertEqual(state.routing, "UNVERIFIED")
    def test_disconnect_clears_verified_state(self):
        state = State()
        state.transport(True)
        state.observe(3, 4)
        state.transport(False)
        self.assertEqual(state.asp, "DOWN")
        self.assertEqual(state.routing, "UNVERIFIED")
