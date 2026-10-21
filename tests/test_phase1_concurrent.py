import unittest
from unittest.mock import patch
from d3faulth_telecom import phase1_concurrent

class ConcurrentTests(unittest.TestCase):
    def test_no_candidate_listener_fails_closed(self):
        with patch.object(phase1_concurrent, "_open_asp", side_effect=ConnectionRefusedError("not listening")):
            result=phase1_concurrent.exercise(timeout=0.01)
        self.assertFalse(result["concurrent_active"])
        self.assertFalse(result["receiver_verified"])
        self.assertEqual(result["routing"], "UNVERIFIED")
        self.assertFalse(result["pcap_verified"])

    def test_activation_failure_skips_data(self):
        class FakeSocket:
            closed=False
            def close(self): self.closed=True
        destination=FakeSocket()
        with patch.object(phase1_concurrent, "_open_asp", side_effect=[
            (destination, {"asp_active":"ACK_VERIFIED"}),
            RuntimeError("ASPAC_ACK missing")]), patch.object(phase1_concurrent, "send_m3ua") as send:
            result=phase1_concurrent.exercise(timeout=0.01)
        self.assertFalse(result["concurrent_active"])
        self.assertFalse(result["data_sent"])
        self.assertTrue(destination.closed)
        send.assert_not_called()

    def test_receiver_success_keeps_pcap_unverified(self):
        class FakeSocket:
            def recv(self, amount): return b"synthetic"
            def close(self): pass
        dest, src = FakeSocket(), FakeSocket()
        parsed={"opc":23,"dpc":42,"payload":phase1_concurrent.PAYLOAD}
        with patch.object(phase1_concurrent, "_open_asp", side_effect=[
            (dest, {"asp_active":"ACK_VERIFIED"}), (src, {"asp_active":"ACK_VERIFIED"})]), \
             patch.object(phase1_concurrent,"send_m3ua"), \
             patch.object(phase1_concurrent,"select") as select_module, \
             patch.object(phase1_concurrent,"decode_data",return_value=parsed):
            select_module.select.return_value=([dest],[],[])
            result=phase1_concurrent.exercise(timeout=0.01)
        self.assertTrue(result["concurrent_active"])
        self.assertTrue(result["receiver_verified"])
        self.assertFalse(result["pcap_verified"])
        self.assertEqual(result["routing"],"UNVERIFIED")
