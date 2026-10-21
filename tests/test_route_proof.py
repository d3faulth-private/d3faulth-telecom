import unittest
from d3faulth_telecom.route_proof import verify_route_evidence

class RouteProofTests(unittest.TestCase):
    def records(self):
        return [dict(transaction_id="lab-x", stage=stage, protocol="M3UA-DATA",
                     payload_sha256="a"*64, timestamp=100.0 + i,
                     capture_file="lab.pcapng", frame_number=i+1,
                     receipt_verified=True)
                for i, stage in enumerate(("source-tx", "stp-rx", "stp-tx", "destination-rx"))]
    def test_no_data_is_unverified(self):
        self.assertEqual(verify_route_evidence([])["status"], "UNVERIFIED")
    def test_missing_stp_egress_is_unverified(self):
        self.assertEqual(verify_route_evidence(self.records()[:2]+self.records()[3:])["status"], "UNVERIFIED")
    def test_changed_payload_fails(self):
        rows = self.records()
        rows[2]["payload_sha256"] = "b"*64
        self.assertEqual(verify_route_evidence(rows)["status"], "FAILED")
    def test_no_destination_receipt(self):
        rows = self.records()
        rows[3]["receipt_verified"] = False
        self.assertEqual(verify_route_evidence(rows)["status"], "UNVERIFIED")
    def test_consistent_metadata_still_not_marked_healthy(self):
        result = verify_route_evidence(self.records())
        self.assertEqual(result["status"], "EVIDENCE_COMPLETE")
        self.assertFalse(result["route_healthy"])
