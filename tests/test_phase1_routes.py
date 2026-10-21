import tempfile
import unittest
from pathlib import Path
from d3faulth_telecom.phase1_routes import analyze, route_command_supported, candidate_with_routes

class RoutePreflightTests(unittest.TestCase):
    def test_routing_keys_do_not_count_as_routes(self):
        config = "as destination-as m3ua\n routing-key 200 0.5.2\n"
        report = analyze(config)
        self.assertEqual(len(report["routes_missing"]), 2)
        self.assertFalse(report["runtime_verified"])

    def test_explicit_route_recognized(self):
        report = analyze("update route 0.5.2 0.0.0 linkset destination-as\n")
        self.assertEqual(len(report["routes_present"]), 1)
        self.assertEqual(report["routes_present"][0]["dpc"], "0.5.2")

    def test_vty_command_in_correct_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml = Path(tmp) / "reference.xml"
            xml.write_text("<vtydoc><node id='config-cs7-rt'><command id='update route POINT_CODE MASK linkset LS_NAME [priority]'/></node></vtydoc>")
            self.assertTrue(route_command_supported(xml))

    def test_rejects_nonisolated_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.cfg"
            path.write_text("listen m3ua 29065\n")
            with self.assertRaises(ValueError):
                candidate_with_routes(path)
