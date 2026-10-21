import struct
import unittest
from unittest.mock import patch
from d3faulth_telecom import phase1_association as association
from d3faulth_telecom.protocol import encode_m3ua, ASPUP_ACK, ASPAC_ACK

NOTIFY = bytes.fromhex("0100000100000018000d0008000100020006000800000064")
ERROR = struct.pack("!BBBBIHHI", 1, 0, 0, 0, 16, 12, 8, 25)

class FakeSocket:
    def __init__(self, responses):
        self.responses = iter(responses)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def settimeout(self, seconds): pass
    def bind(self, target): self.bound = target
    def connect(self, target): self.connected = target
    def recv(self, size):
        try: return next(self.responses)
        except StopIteration: raise TimeoutError("no more messages")

class AssociationTests(unittest.TestCase):
    def test_only_isolated_scope(self):
        self.assertEqual(association.PORT, 29165)
        with self.assertRaises(ValueError):
            association.probe_peer("other", "127.0.0.4")

    def test_notify_parsed(self):
        detail = association._read(FakeSocket([NOTIFY]))
        self.assertEqual(detail["name"], "NOTIFY")
        self.assertEqual(detail["notify"]["routing_contexts"], [100])
        self.assertEqual(detail["notify"]["statuses"][0]["description"], "AS_INACTIVE")

    def test_error_parsed(self):
        detail = association._read(FakeSocket([ERROR]))
        self.assertEqual(detail["name"], "ERROR")
        self.assertEqual(detail["m3ua_error"]["code"], 25)
        self.assertEqual(detail["raw_hex"], ERROR.hex())

    def test_notify_then_ack(self):
        responses = [encode_m3ua(*ASPUP_ACK), NOTIFY, encode_m3ua(*ASPAC_ACK)]
        sock = FakeSocket(responses)
        with patch.object(association, "send_m3ua"):
            result = association.probe_peer("source-asp", "127.0.0.2",
                                            socket_factory=lambda *args: sock)
        self.assertEqual(result["asp_active"], "ACK_VERIFIED")
        self.assertEqual(result["responses"], ["ASPUP_ACK", "NOTIFY", "ASPAC_ACK"])
        self.assertEqual(result["routing"], "UNVERIFIED")

    def test_error_stops_ack_wait(self):
        sock = FakeSocket([encode_m3ua(*ASPUP_ACK), ERROR])
        with patch.object(association, "send_m3ua"):
            result = association.probe_peer("source-asp", "127.0.0.2",
                                            socket_factory=lambda *args: sock)
        self.assertEqual(result["asp_active"], "UNVERIFIED")
        self.assertEqual(result["unexpected_response"]["m3ua_error"]["code"], 25)
        self.assertEqual(result["routing"], "UNVERIFIED")

    def test_missing_listener(self):
        class BrokenSocket(FakeSocket):
            def connect(self, target): raise ConnectionRefusedError("absent")
        result = association.probe_peer("source-asp", "127.0.0.2",
                                        socket_factory=lambda *args: BrokenSocket([]))
        self.assertEqual(result["sctp"], "UNVERIFIED")
        self.assertIn("error", result)

    def test_summary_never_claims_routing(self):
        with patch.object(association, "probe_peer", return_value={"routing":"UNVERIFIED"}):
            report = association.probe_candidate()
        self.assertEqual(report["routing"], "UNVERIFIED")
        self.assertEqual(len(report["peers"]), 2)
