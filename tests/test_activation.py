import unittest
from unittest.mock import patch
from d3faulth_telecom.protocol import encode_m3ua, decode_m3ua
from d3faulth_telecom.activation import activation_probe

class ActivationTests(unittest.TestCase):
    def test_codec_round_trip(self):
        for pair, label in (((4, 1), "ASPAC"), ((4, 3), "ASPAC_ACK")):
            self.assertEqual(decode_m3ua(encode_m3ua(*pair))["name"], label)

    @patch("d3faulth_telecom.activation.osmostp.status", return_value={"running": False})
    def test_does_not_probe_without_managed_stp(self, _):
        result = activation_probe()
        self.assertEqual(result["asp_active"], "UNVERIFIED")
        self.assertEqual(result["routing"], "UNVERIFIED")

    @patch("d3faulth_telecom.activation.osmostp.status", return_value={"running": False})
    def test_no_routing_claim(self, _):
        self.assertNotEqual(activation_probe()["routing"], "VERIFIED")
