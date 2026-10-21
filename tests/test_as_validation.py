import unittest
from d3faulth_telecom.as_validation import EXPECTED, validate_manifest, compare_config, compare_snapshots

class ASValidationTests(unittest.TestCase):
    def test_fixed_lab_manifest_accepted(self):
        self.assertEqual(validate_manifest(EXPECTED), [])

    def test_external_stp_rejected(self):
        manifest = {**EXPECTED, "stp":{"host":"8.8.8.8","port":29065}}
        self.assertIn("INVALID_STP", {x["code"] for x in validate_manifest(manifest)})

    def test_missing_as_detected_without_modification(self):
        result = compare_config(configuration="cs7 instance 0\n listen m3ua 29065\n  local-ip 127.0.0.1\n")
        self.assertTrue(any(x["type"]=="application_server" for x in result["missing_expectations"]))
        self.assertFalse(result["configuration_ready"])
        self.assertEqual(result["mode"], "READ_ONLY")

    def test_snapshot_diff_keeps_routing_unverified(self):
        before = compare_config(configuration="cs7 instance 0\n")
        after = compare_config(configuration="cs7 instance 0\n as test-a m3ua\n routing-context 100\n point-code 23\n")
        report = compare_snapshots(before, after)
        self.assertEqual(report["routing"], "UNVERIFIED")
        self.assertIn("NO_AS", report["resolved_issue_codes"])
