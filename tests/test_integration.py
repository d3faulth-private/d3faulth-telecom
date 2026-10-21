import unittest
from unittest.mock import patch
from d3faulth_telecom.integration import verify_capture_session

class IntegrationTests(unittest.TestCase):
    @patch("d3faulth_telecom.integration.time.sleep")
    @patch("d3faulth_telecom.integration.run_capture",
           return_value={"frames": 4, "aspup_ack_frames": 1, "aspac_ack_frames": 1,
                         "ss7_routing": "UNVERIFIED"})
    @patch("d3faulth_telecom.integration.activation_probe",
           return_value={"asp_active": "ACTIVE"})
    def test_management_verified_without_fake_route(self, activation, capture, sleep):
        result = verify_capture_session()
        self.assertTrue(result["verified_management_exchange"])
        self.assertFalse(result["ss7_data_route_healthy"])
        self.assertEqual(result["ss7_data_routing"], "UNVERIFIED")

    @patch("d3faulth_telecom.integration.time.sleep")
    @patch("d3faulth_telecom.integration.run_capture",
           return_value={"frames": 1, "aspup_ack_frames": 0, "aspac_ack_frames": 0})
    @patch("d3faulth_telecom.integration.activation_probe",
           return_value={"asp_active": "ACTIVE"})
    def test_missing_packet_evidence_not_verified(self, *_):
        self.assertFalse(verify_capture_session()["verified_management_exchange"])

    @patch("d3faulth_telecom.integration.time.sleep")
    @patch("d3faulth_telecom.integration.run_capture", side_effect=RuntimeError("permission denied"))
    @patch("d3faulth_telecom.integration.activation_probe",
           return_value={"asp_active": "ACTIVE"})
    def test_capture_errors_not_reported_healthy(self, *_):
        result = verify_capture_session()
        self.assertFalse(result["verified_management_exchange"])
        self.assertIn("permission denied", result["capture_error"])
