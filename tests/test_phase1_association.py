import unittest
from unittest.mock import patch
from d3faulth_telecom import phase1_association as association

class AssociationTests(unittest.TestCase):
    def test_scoped_endpoint_and_peers(self):
        self.assertEqual(association.HOST, "127.0.0.1")
        self.assertEqual(association.PORT, 29165)
        self.assertEqual(dict(association.PEERS)["destination-asp"], "127.0.0.3")

    def test_reject_other_peers(self):
        with self.assertRaises(ValueError):
            association.probe_peer("other", "127.0.0.4")

    def test_reports_failure_without_route_success(self):
        class BrokenSocket:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def settimeout(self, value): pass
            def bind(self, target): pass
            def connect(self, target): raise ConnectionRefusedError("test listener absent")
        result=association.probe_peer(
            "source-asp", "127.0.0.2", socket_factory=lambda *args: BrokenSocket())
        self.assertEqual(result["sctp"], "UNVERIFIED")
        self.assertEqual(result["routing"], "UNVERIFIED")
        self.assertIn("error", result)

    def test_candidate_never_claims_routing(self):
        with patch.object(association, "probe_peer", return_value={"routing":"UNVERIFIED"}):
            result=association.probe_candidate()
        self.assertEqual(result["routing"], "UNVERIFIED")
        self.assertEqual(len(result["peers"]), 2)
