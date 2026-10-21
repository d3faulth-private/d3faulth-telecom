import unittest
import time
from d3faulth_telecom.delivery import (
    issue_receipt, verify_delivery, route_health, DeliveryReceipt)
from d3faulth_telecom.delivery_demo import run_delivery_demo
from d3faulth_telecom.signaling_state import State

class DeliveryTests(unittest.TestCase):
    def test_real_local_destination_receives_payload(self):
        result = run_delivery_demo()
        self.assertEqual(result["mode"], "TRANSPORT-DEMO")
        self.assertTrue(result["not_ss7_routing"])
        self.assertEqual(result["delivery"]["status"], "VERIFIED", result)

    def test_missing_receipt_cannot_be_healthy(self):
        proof = verify_delivery(None, "t1", "dest", b"test")
        self.assertEqual(route_health(proof, "ESTABLISHED", "ACTIVE"), "UNVERIFIED")

    def test_wrong_destination_or_payload_fails(self):
        receipt = issue_receipt("t1", "dest", b"correct")
        self.assertEqual(verify_delivery(receipt, "t1", "other", b"correct")["status"], "FAILED")
        self.assertEqual(verify_delivery(receipt, "t1", "dest", b"wrong")["status"], "FAILED")

    def test_stale_receipt_is_not_verified(self):
        receipt = DeliveryReceipt("t1", "dest",
            issue_receipt("t1", "dest", b"data").payload_sha256,
            time.time() - 100, True)
        self.assertEqual(verify_delivery(receipt, "t1", "dest", b"data")["status"], "UNVERIFIED")

    def test_asp_active_only_is_not_healthy(self):
        state = State()
        state.transport(True)
        state.observe(3, 4)
        state.observe(4, 3)
        self.assertEqual(state.asp, "ACTIVE")
        self.assertEqual(state.routing, "UNVERIFIED")
        self.assertEqual(state.verify_route({"status": "UNVERIFIED"}), "UNVERIFIED")
        proof = verify_delivery(issue_receipt("t1", "dest", b"data"), "t1", "dest", b"data")
        self.assertEqual(state.verify_route(proof), "HEALTHY")
        state.transport(False)
        self.assertEqual(state.routing, "UNVERIFIED")
