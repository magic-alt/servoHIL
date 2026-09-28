import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_revb_vivado_io_drc import check, expected_io, parse_rtl_ports, parse_xdc


class RevBVivadoIoDrcHarnessTests(unittest.TestCase):
    def test_checked_in_harness_matches_all_64_contract_ports(self):
        report = check(ROOT)
        self.assertEqual(report["status"], "PASS_STATIC_CONTRACT_IO_DRC_NOT_RUN")
        self.assertFalse(report["layout_allowed"])
        self.assertEqual(report["target_part"], "xczu2cg-sfvc784-1-e")
        self.assertEqual(report["top_module"], "servohil_io_drc_top")
        self.assertEqual(report["port_count"], 64)
        self.assertEqual(report["direction_counts"], {"input": 21, "output": 19, "inout": 24})
        self.assertEqual(report["iostandard_counts"], {"LVCMOS18": 32, "LVCMOS33": 32})
        self.assertEqual(report["timing_status"], "BLOCKED_TOP_XDC_CLOCKS_UNBOUND")

    def test_xdc_contains_only_package_pin_and_iostandard(self):
        path = ROOT / "fpga/revb/io_drc/axu2cgb_io_drc.xdc"
        parsed = parse_xdc(path.read_text(encoding="utf-8"))
        self.assertEqual(len(parsed), 64)
        self.assertTrue(all(set(row) == {"PACKAGE_PIN", "IOSTANDARD"} for row in parsed.values()))

    def test_preview_and_harness_xdc_are_semantically_identical(self):
        preview = parse_xdc((ROOT / "hardware/kicad/revB/axu2cgb_expansion/carrier.xdc.preview").read_text())
        harness = parse_xdc((ROOT / "fpga/revb/io_drc/axu2cgb_io_drc.xdc").read_text())
        self.assertEqual(harness, preview)

    def test_rtl_direction_matches_io_contract(self):
        expected = expected_io(ROOT)
        ports = parse_rtl_ports((ROOT / "fpga/revb/io_drc/servohil_io_drc_top.sv").read_text())
        self.assertEqual(set(ports), set(expected))
        for port, row in expected.items():
            self.assertEqual(ports[port], row["direction"])

    def test_timing_commands_are_rejected_from_harness_xdc(self):
        text = "set_property PACKAGE_PIN F7 [get_ports {dac_sclk}]\ncreate_clock -period 10 [get_ports dac_sclk]\n"
        with self.assertRaisesRegex(ValueError, "only PACKAGE_PIN/IOSTANDARD"):
            parse_xdc(text)

    def test_missing_xdc_property_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete XDC properties"):
            parse_xdc("set_property PACKAGE_PIN F7 [get_ports {dac_sclk}]\n")


if __name__ == "__main__":
    unittest.main()
