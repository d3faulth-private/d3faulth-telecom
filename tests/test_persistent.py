import unittest
from unittest.mock import patch
from d3faulth_telecom import persistent
from d3faulth_telecom.topology import topology_lines, topology_render

class PersistentCoreTests(unittest.TestCase):
    def test_loopback_only(self):
        self.assertEqual(persistent.HOST, "127.0.0.1")

    @patch("d3faulth_telecom.persistent.PIDFILE")
    @patch("d3faulth_telecom.persistent.HEALTHFILE")
    @patch("d3faulth_telecom.persistent._pid_alive", return_value=False)
    def test_stale_state_not_live(self, _alive, health, pid):
        pid.read_text.return_value = "123456"
        health.read_text.return_value = '{"routes": [{"status": "HEALTHY"}]}'
        self.assertFalse(persistent.state()["running"])
        self.assertEqual(persistent.state()["routes"], [])

    def test_all_topology_lines_equal_width(self):
        for width in (64, 80, 120):
            lines = topology_lines(width, "ASP CLIENT", "SCTP RELAY", "DEST RESPONDER",
                                   "HEALTHY", "FAILED")
            self.assertEqual(len({len(line) for line in lines}), 1)
            self.assertEqual(lines[2].count("▶"), 1)
            self.assertIn("╳", lines[2])

    def test_render_reports_live_probe(self):
        path = {"status": "HEALTHY",
                "segments": [{"status": "HEALTHY"}, {"status": "HEALTHY"}]}
        self.assertIn("Two-hop signaling transport: HEALTHY",
                      topology_render(90, "UNTESTED", path).plain)
