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
