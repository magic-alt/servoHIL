"""Runtime completion integration must feed health from completed work only."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
WRAP=ROOT/'rtl/revb/runtime_health_integration.sv'
HEALTH=ROOT/'rtl/revb/health_heartbeat.sv'
BENCH=ROOT/'tests/rtl/tb_runtime_health_integration.sv'


class RuntimeIntegrationSourceTests(unittest.TestCase):
    def test_completion_wrapper_exists_and_has_no_command_request_input(self):
        self.assertTrue(WRAP.is_file(),'missing runtime completion integration')
        text=WRAP.read_text()
        for required in ('plant_done_valid','adc_sample_valid','lease_renew_valid'):
            self.assertIn(required,text)
        self.assertNotIn('command_valid',text)
        self.assertNotIn('sample_request',text)


@unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),
                     'Icarus unavailable; required in revb-runtime-verification CI')
class RuntimeIntegrationRtlTests(unittest.TestCase):
    def test_completion_only_and_replay_timeout(self):
        with tempfile.TemporaryDirectory() as t:
            image=Path(t)/'runtime.vvp'
            args=['iverilog','-g2012','-Wall','-s','tb_runtime_health_integration',
                  '-o',str(image),str(HEALTH),str(WRAP),str(BENCH)]
            built=subprocess.run(args,capture_output=True,text=True,timeout=15)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            ran=subprocess.run(['vvp',str(image)],capture_output=True,text=True,timeout=15)
            self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr)
            self.assertIn('RUNTIME_INTEGRATION_PASS',ran.stdout)


if __name__=='__main__':
    unittest.main()
