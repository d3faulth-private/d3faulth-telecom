import unittest
from d3faulth_telecom.msisdn_analysis import decode_tbcd, mask_msisdn, inspect_decoded_json

class MsisdnAnalysisTests(unittest.TestCase):
    def test_tbcd_nibble_order_and_filler(self):
        self.assertEqual(decode_tbcd(bytes.fromhex("214365f7")), "1234567")

    def test_reject_invalid_filler(self):
        with self.assertRaises(ValueError):
            decode_tbcd(bytes.fromhex("f1"))

    def test_masking_never_returns_full_number(self):
        self.assertEqual(mask_msisdn("+1 202 555 0123"), "•••••••••23")
        self.assertIsNone(mask_msisdn("not a number"))

    def test_explicit_msisdn_fields_only(self):
        data=[{"_source":{"layers":{"gsm_map":{"gsm_map.msisdn":"+12025550123",
               "gsm_map.imsi":"001010123456789","other":"123456789"}}}}]
        result=inspect_decoded_json(data)
        self.assertEqual(result["msisdn_fields_detected"],1)
        self.assertEqual(result["field_counts"],{"gsm_map.msisdn":1})
        self.assertFalse(result["numbers_exposed"])

    def test_nested_unrelated_not_counted(self):
        self.assertEqual(inspect_decoded_json({"foo":"12025550123"})["msisdn_fields_detected"],0)
