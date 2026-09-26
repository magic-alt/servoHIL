"""Actual Icarus regressions for the AD7606C-16 serial controller."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/revb/ad7606c16_controller.sv'
BENCH=ROOT/'tests/rtl/tb_ad7606c16_controller.sv'


class AdcControllerSourceTests(unittest.TestCase):
    def test_synthesizable_controller_exists(self):
        self.assertTrue(RTL.is_file(),'missing AD7606C-16 initialization/acquisition controller')


@unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),
                     'Icarus unavailable; required in revb-runtime-verification CI')
class AdcControllerRtlTests(unittest.TestCase):
    def run_case(self, **params):
        self.assertTrue(RTL.is_file())
        self.assertTrue(BENCH.is_file())
        with tempfile.TemporaryDirectory() as t:
            image=Path(t)/'adc.vvp'
            args=['iverilog','-g2012','-Wall','-s','tb_ad7606c16_controller']
            args += [f'-Ptb_ad7606c16_controller.{k}={int(v)}' for k,v in params.items()]
            args += ['-o',str(image),str(RTL),str(BENCH)]
            built=subprocess.run(args,capture_output=True,text=True,timeout=15)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            ran=subprocess.run(['vvp',str(image)],capture_output=True,text=True,timeout=15)
            self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr)
            self.assertIn('ADC_CONTROLLER_PASS',ran.stdout)

    def test_config_readback_then_eight_lane_capture(self):
        self.run_case()

    def test_config_mismatch_fails_closed(self):
        self.run_case(BAD_CONFIG=1)

    def test_busy_never_asserts_times_out(self):
        self.run_case(NO_BUSY=1)


if __name__=='__main__':
    unittest.main()
