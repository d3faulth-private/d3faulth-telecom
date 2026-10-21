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

    def test_unexpected_error_details_preserved(self):
        import struct
        from d3faulth_telecom.protocol import encode_m3ua
        from unittest.mock import patch
        raw = struct.pack("!BBBBIHHI", 1, 0, 0, 0, 16, 12, 8, 25)
        class FakeSocket:
            def recv(self, size): return raw
        with patch.object(association, "send_m3ua"):
            ok, result = association._exchange(FakeSocket(), (4,1), (4,3))
        self.assertFalse(ok)
        self.assertEqual(result["class"], 0)
        self.assertEqual(result["type"], 0)
        self.assertEqual(result["raw_hex"], raw.hex())
        self.assertEqual(result["m3ua_error"]["code"], 25)

    def test_failed_activation_record_has_unexpected_response(self):
        from unittest.mock import patch
        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def settimeout(self, value): pass
            def bind(self, target): pass
            def connect(self, target): pass
        replies = iter(((True, {"name":"ASPUP_ACK","class":3,"type":4,"length":8,"raw_hex":"00"}),
                        (False, {"name":"OTHER","class":0,"type":0,"length":16,"raw_hex":"01",
                                 "m3ua_error":{"code":25,"description":"Invalid Routing Context"}})))
        with patch.object(association, "_exchange", side_effect=lambda *args: next(replies)):
            result = association.probe_peer(
                "source-asp", "127.0.0.2", socket_factory=lambda *args: FakeSocket())
        self.assertEqual(result["asp_up"], "ACK_VERIFIED")
        self.assertEqual(result["asp_active"], "UNVERIFIED")
        self.assertEqual(result["unexpected_response"]["m3ua_error"]["code"], 25)
        self.assertEqual(result["routing"], "UNVERIFIED")
