import tempfile
import unittest
from pathlib import Path
from d3faulth_telecom.phase1_candidate import inspect_candidate, write_candidate

class Phase1CandidateTests(unittest.TestCase):
    def test_expected_isolation(self):
        result=inspect_candidate()
        self.assertEqual(result["issues"], [])
        self.assertFalse(result["syntax_verified"])
        self.assertFalse(result["routing_verified"])

    def test_rejects_live_port(self):
        result=inspect_candidate("listen m3ua 29065")
        self.assertTrue(result["issues"])

    def test_write_once_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"candidate.cfg"
            result=write_candidate(path)
            self.assertFalse(result["service_modified"])
            self.assertTrue(path.is_file())
            with self.assertRaises(FileExistsError):
                write_candidate(path)

    def test_ports_and_supported_listener_value(self):
        from d3faulth_telecom.phase1_candidate import CONFIG_TEXT
        self.assertIn("bind 127.0.0.1 4240", CONFIG_TEXT)
        self.assertIn("listen m3ua 29165", CONFIG_TEXT)
        self.assertIn("accept-asp-connections pre-configured", CONFIG_TEXT)
        self.assertNotIn("accept-asp-connections static-only", CONFIG_TEXT)

    def test_rejects_invalid_asp_acceptance(self):
        from d3faulth_telecom.phase1_candidate import CONFIG_TEXT
        changed=CONFIG_TEXT.replace("accept-asp-connections pre-configured", "accept-asp-connections static-only")
        result=inspect_candidate(changed)
        self.assertTrue(any("ASP acceptance" in issue for issue in result["issues"]))

    def test_383_point_codes_from_kali_startup(self):
        from d3faulth_telecom.phase1_candidate import CONFIG_TEXT
        self.assertIn("point-code 0.0.1", CONFIG_TEXT)
        self.assertIn("routing-key 100 0.2.7", CONFIG_TEXT)
        self.assertIn("routing-key 200 0.5.2", CONFIG_TEXT)
        self.assertNotIn("routing-key 100 23", CONFIG_TEXT)
        self.assertNotIn("routing-key 200 42", CONFIG_TEXT)

    def test_rejects_previous_invalid_point_codes(self):
        from d3faulth_telecom.phase1_candidate import CONFIG_TEXT
        old=CONFIG_TEXT.replace("routing-key 100 0.2.7", "routing-key 100 23")
        self.assertTrue(inspect_candidate(old)["issues"])
