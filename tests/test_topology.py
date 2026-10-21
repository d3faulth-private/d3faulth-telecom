import unittest
from d3faulth_telecom.topology import topology_lines, topology_render

class TopologyLayoutTests(unittest.TestCase):
    def test_columns_centered_in_equal_cells(self):
        for width in (58, 78, 96, 120):
            rows = topology_lines(width, "ASP CLIENT", "SCTP RELAY", "DEST RESPONDER")
            cell = max(20, (max(64, width) - 4) // 3)
            for row in rows:
                self.assertEqual(len(row), 3 * cell)
            positions = [rows[0].index(n) for n in ("ASP CLIENT", "SCTP RELAY", "DEST RESPONDER")]
            self.assertLess(positions[0], positions[1])
            self.assertLess(positions[1], positions[2])

    def test_disconnected_hlr_not_reported_healthy(self):
        rendered = topology_render(90, "HEALTHY").plain
        self.assertIn("HLR is not implemented", rendered)

    def test_multihop_health_and_failure(self):
        for status in ("HEALTHY", "FAILED"):
            path = {"status": status, "segments": [{"status": status}, {"status": status}]}
            self.assertIn(status, topology_render(90, "UNTESTED", path).plain)
