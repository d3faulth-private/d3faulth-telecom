import unittest
from d3faulth_telecom.protocol import encode_m3ua, decode_m3ua, ProtocolError
from d3faulth_telecom.lab import run_exchange

class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(decode_m3ua(encode_m3ua(3, 1))["name"], "ASPUP")
        self.assertEqual(decode_m3ua(encode_m3ua(3, 4))["name"], "ASPUP_ACK")
    def test_reject_truncation(self):
        with self.assertRaises(ProtocolError): decode_m3ua(b"\x01\x00")
    def test_reject_unsupported(self):
        with self.assertRaises(ProtocolError): encode_m3ua(1, 1)
    def test_reject_invalid_length(self):
        with self.assertRaises(ProtocolError): decode_m3ua(b"\x01\x00\x03\x01\x00\x00\x00\x0c")
    def test_lab_connection(self):
        try: result = run_exchange(port=29455)
        except RuntimeError as exc:
            if "SCTP" in str(exc) or "Protocol not supported" in str(exc): self.skipTest(str(exc))
            raise
        self.assertEqual(result["status"], "HEALTHY")
    def test_fault(self):
        try: result = run_exchange(port=29456, fail=True)
        except RuntimeError as exc:
            if "SCTP" in str(exc) or "Protocol not supported" in str(exc): self.skipTest(str(exc))
            raise
        self.assertEqual(result["status"], "FAILED")
