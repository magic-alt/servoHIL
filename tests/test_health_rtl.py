"""Run actual synthesizable health RTL, not a Python replacement of its logic."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT/'rtl/revb/health_heartbeat.sv'
BENCH = ROOT/'tests/rtl/tb_health_heartbeat.sv'


class Vectors:
    def __init__(self, initial=0):
        self.seq = dict.fromkeys(('plant', 'io', 'lease'), initial)
        self.rows = []

    def tick(self, *, start=0, arm=0, fault=0, plant='advance', io='advance', lease='advance'):
        row = [start, arm, fault]
        for name, mode in (('plant', plant), ('io', io), ('lease', lease)):
            if mode not in ('advance', 'duplicate', 'missing', 'jump'):
                raise ValueError(mode)
            if mode in ('advance', 'jump'):
                self.seq[name] = (self.seq[name] + (2 if mode == 'jump' else 1)) & 0xffffffff
            row.extend([int(mode != 'missing'), self.seq[name]])
        self.rows.append(row)
        return len(self.rows)-1

    def run(self, count, **kw):
        for _ in range(count):
            self.tick(**kw)
        return len(self.rows)-1

    def start(self):
        self.tick(start=1)
        self.run(3)
        return self


class HealthRtlSourceTests(unittest.TestCase):
    def test_real_health_core_is_present(self):
        self.assertTrue(RTL.is_file(), 'deadline-qualified hardware heartbeat RTL is missing')


@unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),
                     'Icarus unavailable; required in revb-runtime-verification CI')
class HealthRtlTests(unittest.TestCase):
    def simulate(self, vectors, **parameters):
        self.assertTrue(RTL.is_file(), 'missing health RTL')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, output, image = tmp/'input.txt', tmp/'output.txt', tmp/'run.vvp'
            source.write_text('\n'.join(
                f'{s} {a} {f} {p} {ps:x} {i} {isq:x} {l} {ls:x}'
                for s, a, f, p, ps, i, isq, l, ls in vectors.rows)+'\n')
            args = ['iverilog', '-g2012', '-Wall', '-s', 'tb_health_heartbeat']
            args += [f'-Ptb_health_heartbeat.{k}={v}' for k,v in parameters.items()]
            args += ['-o', str(image), str(RTL), str(BENCH)]
            built = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            ran = subprocess.run(['vvp', str(image), f'+input={source}', f'+output={output}'],
                                 capture_output=True, text=True, timeout=15)
            self.assertEqual(ran.returncode, 0, ran.stdout+ran.stderr)
            self.assertIn(f'HEALTH_VECTORS_PASS count={len(vectors.rows)}', ran.stdout)
            result = [tuple(map(int,line.split()))[1:] for line in output.read_text().splitlines()]
            self.assertEqual(len(result), len(vectors.rows))
            return result  # WDI, ARM, healthy, reason

    def test_default_parameters_emit_real_five_ms_period_at_100mhz(self):
        self.assertTrue(RTL.is_file(), 'missing health RTL')
        with tempfile.TemporaryDirectory() as tmp:
            image=Path(tmp)/'cadence.vvp'
            subprocess.run(['iverilog','-g2012','-Wall','-s','tb_health_cadence',
                            '-o',str(image),str(RTL),str(BENCH.with_name('tb_health_cadence.sv'))],
                           check=True, capture_output=True, text=True, timeout=15)
            result=subprocess.run(['vvp',str(image)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('CADENCE_PASS edges=2 interval_ns=5000000',result.stdout)

    def test_no_session_never_feeds_or_arms(self):
        v=Vectors();v.run(100,arm=1)
        self.assertTrue(all(x[:3]==(0,0,0) for x in self.simulate(v)))

    def test_healthy_disarmed_session_feeds_at_exact_window_cadence(self):
        v=Vectors().start();v.run(250)
        r=self.simulate(v)
        falls=[i for i in range(1,len(r)) if r[i-1][0] and not r[i][0]]
        self.assertGreaterEqual(len(falls),4)
        self.assertTrue(all(b-a==50 for a,b in zip(falls,falls[1:])))
        self.assertTrue(all(x[1]==0 and x[3]==0 for x in r))
        self.assertTrue(r[-1][2])

    def test_arm_must_be_low_while_healthy_before_rising(self):
        v=Vectors();v.tick(start=1);v.run(40,arm=1)
        before=len(v.rows)-1;v.run(2,arm=0);after=v.tick(arm=1)
        r=self.simulate(v)
        self.assertTrue(all(x[1]==0 for x in r[:before+1]))
        self.assertEqual(r[after][1],1)

    def test_duplicate_or_absent_progress_expires_at_exact_boundary(self):
        for stream,limit,code in [('plant',11,2),('io',13,4),('lease',31,8)]:
            for mode in ('duplicate','missing'):
                with self.subTest(stream=stream,mode=mode):
                    v=Vectors().start();last=v.run(limit-1,**{stream:mode})
                    expired=v.tick(**{stream:mode});v.run(40)
                    r=self.simulate(v)
                    self.assertEqual(r[last][3],0)
                    self.assertEqual(r[expired][3],code)
                    self.assertTrue(all(x[1:3]==(0,0) and x[3]==code for x in r[expired:]))

    def test_progress_on_last_allowed_edge_prevents_timeout(self):
        for stream,limit in [('plant',11),('io',13),('lease',31)]:
            v=Vectors().start();v.run(limit-1,**{stream:'missing'});v.tick();v.run(40)
            self.assertTrue(all(x[3]==0 for x in self.simulate(v)),stream)

    def test_gapped_sequences_latch_fault(self):
        for stream,code in [('plant',16),('io',32),('lease',64)]:
            v=Vectors().start();bad=v.tick(**{stream:'jump'});v.run(50)
            r=self.simulate(v)
            self.assertEqual(r[bad][3],code,stream)
            self.assertTrue(all(x[2]==0 for x in r[bad:]))

    def test_unsigned_sequence_wrap_is_valid(self):
        v=Vectors(0xfffffffd).start();v.run(100)
        self.assertTrue(all(x[3]==0 for x in self.simulate(v)))

    def test_runtime_fault_holds_wdi_without_synthetic_falling_edge(self):
        v=Vectors().start();v.run(30,arm=1);bad=v.tick(arm=1,fault=1);v.run(70,arm=1)
        r=self.simulate(v);self.assertEqual(r[bad-1][0],1)
        self.assertTrue(all(x==(1,0,0,1) for x in r[bad:]))

    def test_fault_recovery_requires_explicit_session_then_rearm(self):
        v=Vectors().start();v.run(35,arm=1);bad=v.tick(fault=1,arm=1)
        no_restart=v.run(40,arm=1);v.tick(start=1,arm=0)
        v.run(35,arm=1);held=len(v.rows)-1;v.run(2,arm=0);armed=v.tick(arm=1)
        r=self.simulate(v)
        self.assertTrue(all(x[1:3]==(0,0) for x in r[bad:no_restart+1]))
        self.assertEqual(r[held][1:3],(0,1))
        self.assertEqual(r[armed][1:3],(1,1))

    def test_direct_disarm_does_not_stop_healthy_heartbeat(self):
        v=Vectors().start();on=v.run(35,arm=1);off=v.tick(arm=0);v.run(60)
        r=self.simulate(v);self.assertEqual(r[on][1],1)
        self.assertEqual(r[off][1:3],(0,1));self.assertEqual(r[-1][3],0)

    def test_session_restart_while_healthy_is_protocol_fault(self):
        v=Vectors().start();bad=v.tick(start=1);v.run(40)
        r=self.simulate(v);self.assertEqual(r[bad][3],128)
        self.assertFalse(r[-1][2])

    def test_session_with_arm_high_cannot_enable(self):
        v=Vectors();v.tick(start=1,arm=1);v.run(100,arm=1)
        r=self.simulate(v);self.assertEqual(r[0][3],128)
        self.assertTrue(all(x[1:3]==(0,0) for x in r))

    def test_live_runtime_fault_cannot_be_cleared_by_session(self):
        v=Vectors().start();v.tick(fault=1);bad=v.tick(start=1,fault=1);v.run(40)
        r=self.simulate(v);self.assertNotEqual(r[bad][3],0)
        self.assertTrue(all(x[1:3]==(0,0) for x in r[bad:]))

    def test_first_progress_is_required_from_every_source(self):
        for stream,code in [('plant',2),('io',4),('lease',8)]:
            v=Vectors();v.tick(start=1);v.run(100,**{stream:'missing'})
            r=self.simulate(v)
            self.assertTrue(all(x[:3]==(0,0,0) for x in r))
            self.assertEqual(r[-1][3],code)

if __name__=='__main__':
    unittest.main()
