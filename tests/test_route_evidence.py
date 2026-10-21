import json
import tempfile
import unittest
from pathlib import Path
from d3faulth_telecom.route_evidence import audit_file, correlate

class RouteEvidenceTests(unittest.TestCase):
    def test_matching_checkpoints_do_not_assert_stp_routing(self):
        events = [
            {"transaction_id": "test-01", "node": "lab-source", "direction": "sent",
             "payload_sha256": "a"*64, "timestamp": 10.0},
            {"transaction_id": "test-01", "node": "lab-destination", "direction": "received",
             "payload_sha256": "a"*64, "timestamp": 10.2}]
        out = correlate(events)
        self.assertEqual(out["transactions"][0]["status"], "CORRELATED")
        self.assertEqual(out["osmostp_routing"], "UNVERIFIED")

    def test_missing_destination_is_unverified(self):
        result = correlate([{"transaction_id": "x", "node": "lab-source",
                             "direction": "sent", "payload_sha256": "f"*64,
                             "timestamp": 1}])
        self.assertEqual(result["transactions"][0]["status"], "UNVERIFIED")

    def test_duplicate_or_wrong_digest_cannot_correlate(self):
        src = {"transaction_id": "x", "node": "lab-source",
               "direction": "sent", "payload_sha256": "a"*64, "timestamp": 1}
        dst = {"transaction_id": "x", "node": "lab-destination",
               "direction": "received", "payload_sha256": "b"*64, "timestamp": 2}
        self.assertEqual(correlate([src, dst])["transactions"][0]["status"], "UNVERIFIED")
        dst["payload_sha256"] = "a"*64
        self.assertEqual(correlate([src, dst, dict(dst)])["transactions"][0]["status"], "UNVERIFIED")

    def test_jsonl_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"evidence.jsonl"
            path.write_text(json.dumps({"transaction_id": "x", "node": "lab-source",
                "direction": "sent", "payload_sha256": "a"*64, "timestamp": 1})+"\n")
            self.assertEqual(audit_file(path)["osmostp_routing"], "UNVERIFIED")
