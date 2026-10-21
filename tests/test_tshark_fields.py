import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from d3faulth_telecom.stp_capture import inspect

class TSharkFieldCompatibilityTests(unittest.TestCase):
    @patch("d3faulth_telecom.stp_capture.subprocess.run")
    @patch("d3faulth_telecom.stp_capture.STATE")
    def test_capture_uses_supported_sctp_ppid_field(self, state, run):
        with tempfile.TemporaryDirectory() as tmp:
            state.__truediv__.return_value = Path(tmp) / "osmostp-captures"
            folder = Path(tmp) / "osmostp-captures"
            folder.mkdir()
            pcap = folder / "sample.pcapng"
            pcap.write_bytes(b"test")
            run.return_value.returncode = 0
            run.return_value.stdout = "1,3,4,3\n2,4,3,3\n"
            result = inspect(pcap)
            argv = run.call_args.args[0]
            self.assertIn("sctp.data_payload_proto_id", argv)
            self.assertNotIn("sctp.ppid", argv)
            self.assertEqual(result["aspup_ack_frames"], 1)
            self.assertEqual(result["aspac_ack_frames"], 1)
