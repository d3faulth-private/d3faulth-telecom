import unittest
from unittest.mock import patch
from d3faulth_telecom import capture

class CaptureTests(unittest.TestCase):
    @patch("d3faulth_telecom.capture.shutil.which", return_value=None)
    def test_requires_tshark(self, _):
        with self.assertRaisesRegex(RuntimeError, "tshark"):
            capture.start()

    @patch("d3faulth_telecom.capture.shutil.which", return_value=None)
    def test_requires_wireshark(self, _):
        with self.assertRaisesRegex(RuntimeError, "Wireshark"):
            capture.open_wireshark()

    def test_idle_status(self):
        self.assertFalse(capture.status()["active"])
