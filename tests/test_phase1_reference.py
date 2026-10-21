import tempfile
import unittest
from pathlib import Path
from d3faulth_telecom.phase1_reference import check_reference

class Phase1ReferenceTests(unittest.TestCase):
    def test_missing_commands_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ref.xml"
            path.write_text("<vtydoc><node id='config-cs7-as'><command id='asp NAME'/></node></vtydoc>")
            result=check_reference(path)
            self.assertFalse(result["reference_compatible"])
            self.assertFalse(result["config_parse_verified"])
            self.assertFalse(result["routing_verified"])

    def test_invalid_xml_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ref.xml"
            path.write_text("<not-closed")
            with self.assertRaises(Exception):
                check_reference(path)

    def test_namespaced_xml_commands(self):
        from d3faulth_telecom.phase1_reference import REQUIRED
        from xml.sax.saxutils import escape
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vty.xml"
            groups = []
            for node, commands in REQUIRED.items():
                actual_node = "config-cs7-instance" if node == "config-cs7" else node
                elements = "".join('<command id="' + escape(cmd, {'"':'&quot;'}) + '"/>' for cmd in commands)
                groups.append('<node id="' + actual_node + '">' + elements + '</node>')
            path.write_text('<vtydoc xmlns="urn:osmocom:vty">' + "".join(groups) + '</vtydoc>')
            result = check_reference(path)
            self.assertTrue(result["reference_compatible"])
            self.assertEqual(len(result["matched"]), 9)
            self.assertEqual(result["missing"], [])
            self.assertFalse(result["routing_verified"])
