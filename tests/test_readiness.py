import unittest
from unittest.mock import patch
from d3faulth_telecom.readiness import verify_lab

class ReadinessTests(unittest.TestCase):
    @patch("d3faulth_telecom.readiness.shutil.which", return_value="/usr/bin/tshark")
    @patch("d3faulth_telecom.readiness.activation_probe", return_value={"asp_active": "ACTIVE"})
    @patch("d3faulth_telecom.readiness.osmostp.status",
           return_value={"running": True, "m3ua_ack": True})
    def test_active_never_means_data_routed(self, *_):
        result = verify_lab()
        self.assertEqual(result["checks"]["m3ua_asp_active"], "PASS")
        self.assertEqual(result["checks"]["ss7_data_routing"], "UNVERIFIED")
        self.assertFalse(result["route_healthy"])

    @patch("d3faulth_telecom.readiness.activation_probe")
    @patch("d3faulth_telecom.readiness.osmostp.status",
           return_value={"running": False, "m3ua_ack": False})
    def test_stopped_stp_skips_activation(self, stp, activation):
        result = verify_lab()
        self.assertEqual(result["checks"]["osmostp_process"], "FAIL")
        self.assertFalse(result["ready_for_capture_review"])
        activation.assert_not_called()
