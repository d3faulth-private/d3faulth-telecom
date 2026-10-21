import unittest
from unittest.mock import patch
from d3faulth_telecom import network

class NetworkTests(unittest.TestCase):
    def test_bindings_are_loopback(self):
        self.assertEqual(network.HOST, "127.0.0.1")
        self.assertNotEqual(network.RELAY_PORT, network.DEST_PORT)
    def test_multi_node_exchange(self):
        try:
            result = network.run_path()
        except RuntimeError as exc:
            if "SCTP" in str(exc): self.skipTest(str(exc))
            raise
        if "SCTP" in result.get("error", "") or "Protocol not supported" in result.get("error", ""):
            self.skipTest(result.get("error"))
        self.assertEqual(result["status"], "HEALTHY", result)
        self.assertEqual(len(result["segments"]), 2)
    def test_ack_failure(self):
        result = network.run_path(fail=True)
        if "SCTP" in result.get("error", "") or "Protocol not supported" in result.get("error", ""):
            self.skipTest(result["error"])
        self.assertEqual(result["status"], "FAILED")
