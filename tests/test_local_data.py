import unittest
from unittest.mock import patch
from d3faulth_telecom.m3ua_data import encode_data,decode_data,PC_A,PC_B,PAYLOAD
from d3faulth_telecom.protocol import ProtocolError
from d3faulth_telecom.route_verification import verify_route

class LocalDataTests(unittest.TestCase):
    def test_fixed_synthetic_message_roundtrip(self):
        result=decode_data(encode_data(PC_A,PC_B))
        self.assertEqual(result["payload"],PAYLOAD)
        self.assertEqual((result["opc"],result["dpc"]),(PC_A,PC_B))
    def test_other_point_codes_rejected(self):
        with self.assertRaises(ProtocolError):
            encode_data(300,400)
    def test_custom_payload_rejected(self):
        with self.assertRaises(ProtocolError):
            encode_data(PC_A,PC_B,b"other")
    @patch("d3faulth_telecom.route_verification.time.sleep")
    @patch("d3faulth_telecom.route_verification.exercise",
           return_value={"destination_received":True,"payload_matches":True})
    @patch("d3faulth_telecom.route_verification.run_capture",
           return_value={"data_frames":2})
    def test_route_requires_both_capture_and_receipt(self,*_):
        self.assertTrue(verify_route()["route_healthy"])
    @patch("d3faulth_telecom.route_verification.time.sleep")
    @patch("d3faulth_telecom.route_verification.exercise",
           return_value={"destination_received":True,"payload_matches":True})
    @patch("d3faulth_telecom.route_verification.run_capture",
           return_value={"data_frames":0})
    def test_missing_pcap_fails_closed(self,*_):
        self.assertFalse(verify_route()["route_healthy"])
