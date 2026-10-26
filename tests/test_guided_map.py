import unittest
from d3faulth_telecom.guided_map import describe, execute, fixtures, run_guided

class GuidedMapTests(unittest.TestCase):
    def test_scenarios_offline_only(self):
        for scenario in ("ati","update-location"):
            result = describe(scenario)
            self.assertFalse(result["network_io"])
            self.assertFalse(result["mutates_real_subscriber"])

    def test_ati_denies_untrusted_requester(self):
        result=execute("ati")
        self.assertEqual(result["unprivileged"]["decision"],"DENY")
        self.assertFalse(result["unprivileged"]["disclosed"])
        self.assertFalse(result["real_map_executed"])

    def test_location_requires_approval(self):
        with self.assertRaises(PermissionError):
            execute("update-location")

    def test_location_restores_state(self):
        original=fixtures()["TEST-SIM-001"].serving_vlr
        result=execute("update-location",approved=True)
        self.assertTrue(result["synthetic_state_changed_during_test"])
        self.assertTrue(result["state_restored"])
        self.assertEqual(fixtures()["TEST-SIM-001"].serving_vlr,original)

    def test_guided_cancel(self):
        result=run_guided(input_fn=lambda prompt:"0",output_fn=lambda text:None)
        self.assertEqual(result["status"],"CANCELLED")

    def test_guided_decline_change(self):
        choices=iter(("2","NO"))
        result=run_guided(input_fn=lambda prompt:next(choices),output_fn=lambda text:None)
        self.assertEqual(result["status"],"CANCELLED")
