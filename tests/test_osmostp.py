import unittest
from unittest.mock import patch
from d3faulth_telecom import osmostp

class OsmoSTPTests(unittest.TestCase):
    def test_local_m3ua_only(self):
        cfg = osmostp.config_text()
        self.assertIn("local-ip 127.0.0.1", cfg)
        self.assertIn("listen m3ua 29065", cfg)
        self.assertIn("bind 127.0.0.1", cfg)
        self.assertNotIn("0.0.0.0", cfg)
        self.assertEqual(osmostp.HOST, "127.0.0.1")

    @patch("d3faulth_telecom.osmostp._read_pid", return_value=None)
    def test_not_running_is_not_verified(self, _):
        result = osmostp.status()
        self.assertFalse(result["running"])
        self.assertFalse(result["m3ua_ack"])

    @patch("d3faulth_telecom.osmostp.shutil.which", return_value=None)
    def test_missing_binary_is_reported(self, _):
        with self.assertRaisesRegex(RuntimeError, "not installed"):
            osmostp.start()
