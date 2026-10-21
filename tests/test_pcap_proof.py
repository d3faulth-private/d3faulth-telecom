import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from d3faulth_telecom.pcap_proof import audit_verified_captures, inspect_capture

class PcapEvidenceTests(unittest.TestCase):
    def rows(self):
        return [dict(transaction_id="lab-a", stage=stage,
                     protocol="M3UA-DATA", payload_sha256="a"*64,
                     timestamp=100+i, capture_file="lab.pcapng",
                     frame_number=i+1, receipt_verified=True)
                for i, stage in enumerate(("source-tx", "stp-rx", "stp-tx", "destination-rx"))]

    def test_missing_capture_does_not_prove_route(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"proof.json"
            path.write_text(json.dumps(self.rows()))
            result = audit_verified_captures(path, directory)
            self.assertFalse(result["route_healthy"])
            self.assertEqual(result["status"], "UNVERIFIED")

    @patch("d3faulth_telecom.pcap_proof.inspect_capture")
    def test_matching_frame_metadata_still_not_route_healthy(self, mock_inspect):
        mock_inspect.side_effect = lambda path, frames: {frames[0]: {"ppid":3, "epoch":101.0}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"proof.json"
            path.write_text(json.dumps(self.rows()))
            result = audit_verified_captures(path, directory)
            self.assertEqual(result["status"], "CAPTURE_CORRELATED")
            self.assertFalse(result["route_healthy"])

    def test_invalid_frame_number(self):
        with self.assertRaises(ValueError):
            inspect_capture("/missing.pcap", [0])
