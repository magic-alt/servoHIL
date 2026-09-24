"""Logic reference regressions; these are NOT an IC or board simulation."""
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sim' / 'safety'))
try:
    from logic import WindowWatchdog, SafetyChain
except ImportError:
    WindowWatchdog = SafetyChain = None


class SafetyLogicTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(WindowWatchdog, 'missing watchdog reference implementation')
        self.assertIsNotNone(SafetyChain, 'missing hardware-chain reference implementation')

    def ready(self):
        s = SafetyChain()
        s.step(0, clear_n=False, arm=False)
        s.step(1, falling=True)
        s.step(6, falling=True)
        self.assertFalse(s.step(25.9))
        self.assertFalse(s.step(26))  # no ARM edge yet
        self.assertTrue(s.step(27, arm=True))
        return s

    def test_valid_heartbeat_at_all_window_corners(self):
        for lower, upper, period in itertools.product((1.48, 2.22), (9.35, 12.65), (4, 5, 6)):
            with self.subTest(lower=lower, upper=upper, period=period):
                w = WindowWatchdog(lower_ms=lower, upper_ms=upper)
                for i in range(100):
                    self.assertTrue(w.step(201 + i * period, falling=True))

    def test_stuck_high_or_low_times_out_without_edges(self):
        for stuck in ('high', 'low'):
            w = WindowWatchdog()
            self.assertTrue(w.step(201, falling=True))
            self.assertTrue(w.step(211.9))
            self.assertFalse(w.step(212))
            self.assertFalse(w.step(300), stuck)

    def test_fast_pulse_is_not_a_valid_heartbeat(self):
        w = WindowWatchdog()
        self.assertTrue(w.step(201, falling=True))
        self.assertFalse(w.step(202, falling=True))
        self.assertFalse(w.step(203, falling=True))

    def test_reset_hold_and_first_edge_exception(self):
        w = WindowWatchdog()
        self.assertFalse(w.step(199, falling=True))
        self.assertTrue(w.step(200.1, falling=True))
        self.assertFalse(w.step(200.2, falling=True))
        self.assertFalse(w.step(400.19, falling=True))
        self.assertTrue(w.step(400.3, falling=True))

    def test_large_time_jump_and_no_heartbeat_never_implies_health(self):
        w = WindowWatchdog()
        self.assertFalse(w.step(1e9))

    def test_two_edges_and_delay_are_required_before_arm(self):
        s = SafetyChain()
        self.assertFalse(s.step(0, arm=False))
        self.assertFalse(s.step(1, falling=True))
        self.assertFalse(s.step(50, arm=True))
        self.assertFalse(s.step(51, arm=False, falling=True))
        self.assertFalse(s.step(70, arm=True))
        self.assertFalse(s.step(71, arm=True))  # arm held through qualification
        self.assertFalse(s.step(72, arm=False))
        self.assertTrue(s.step(73, arm=True))

    def test_each_fault_clears_latch(self):
        for fault in ('clear_n', 'aon_valid', 'interlock_ok', 'analog_rails_ok'):
            s = self.ready()
            self.assertFalse(s.step(28, arm=True, **{fault: False}), fault)
            self.assertFalse(s.arm_latch, fault)
            self.assertFalse(s.step(29, arm=True))

    def test_recovered_watchdog_with_arm_held_high_does_not_restart(self):
        s = self.ready()
        self.assertFalse(s.step(28, clear_n=False, arm=True))
        self.assertFalse(s.step(230, falling=True, arm=True))
        self.assertFalse(s.step(235, falling=True, arm=True))
        self.assertFalse(s.step(260, arm=True))
        self.assertFalse(s.step(261, arm=False))
        self.assertTrue(s.step(262, arm=True))

    def test_disarm_gates_output_even_if_arm_latch_is_set(self):
        s = self.ready()
        self.assertFalse(s.step(28, arm=False))
        self.assertTrue(s.arm_latch)

    def test_nonfinite_or_backwards_time_rejected(self):
        for cls in (WindowWatchdog, SafetyChain):
            for t in (math.nan, math.inf, -1):
                with self.assertRaises(ValueError):
                    cls().step(t)
            s = cls()
            s.step(20)
            with self.assertRaises(ValueError):
                s.step(19)

    def test_invalid_delay_configuration_rejected(self):
        for args in ({'lower_ms': 0}, {'upper_ms': 1}, {'reset_ms': -1}):
            with self.assertRaises(ValueError):
                WindowWatchdog(**args)
        with self.assertRaises(ValueError):
            SafetyChain(qualify_ms=math.nan)

    def test_all_qualifier_delay_corners(self):
        for delay in (12, 20, 28):
            s = SafetyChain(qualify_ms=delay)
            s.step(0, falling=True)
            s.step(5, falling=True)
            self.assertFalse(s.step(5 + delay - .01, arm=True))
            s.step(5 + delay, arm=False)
            self.assertTrue(s.step(6 + delay, arm=True))


if __name__ == '__main__':
    unittest.main()
