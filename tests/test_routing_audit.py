import unittest
from d3faulth_telecom.routing_audit import audit_text

class RoutingAuditTests(unittest.TestCase):
    def test_detects_missing_application_server(self):
        cfg = "cs7 instance 0\n listen m3ua 29065\n  local-ip 127.0.0.1\n"
        result = audit_text(cfg, "unable to uniquely identify the AS for this message")
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("NO_AS", codes)
        self.assertIn("AS_AMBIGUOUS", codes)
        self.assertEqual(result["routing"], "UNVERIFIED")
        self.assertFalse(result["service_modified"])

    def test_recognizes_explicit_definitions(self):
        cfg = "cs7 instance 0\n as test-as m3ua\n asp test-asp 127.0.0.1 29065 m3ua\n routing-context 10\n point-code 23\n"
        result = audit_text(cfg)
        self.assertEqual(result["application_servers"], ["test-as"])
        self.assertEqual(result["routing_contexts"], ["10"])
        self.assertEqual(result["point_codes"], ["23"])
        self.assertEqual(result["routing"], "UNVERIFIED")
