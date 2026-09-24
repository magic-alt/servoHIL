"""Discrete logic reference, NOT a vendor macromodel or a board safety proof.

TPS3430 timing: SBVS366A tables 6.6/8-3. Initial evaluation/startup,
propagation, metastability, ramps, parasitics and analogue behaviour are
excluded. clear_n represents the *settled* U501/U502/U510 reset path.
The second TPS3808's release delay is parameterised, not assumed exact.
"""
from dataclasses import dataclass, field
import math


def _positive(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError('timing parameters must be finite and positive')
    return value


def _time(value: float, previous: float) -> float:
    if not math.isfinite(value) or value < 0 or value < previous:
        raise ValueError('time must be finite, nonnegative and monotonic')
    return value


@dataclass
class WindowWatchdog:
    """Ideal falling-edge window timer with reset/retry, in milliseconds."""
    lower_ms: float = 1.85
    upper_ms: float = 11.0
    reset_ms: float = 200.0
    _time_ms: float = field(default=0, init=False)
    _last_edge: float | None = field(default=None, init=False)
    _reset_until: float = field(init=False)
    _deadline: float = field(init=False)

    def __post_init__(self):
        for value in (self.lower_ms, self.upper_ms, self.reset_ms):
            _positive(value)
        if self.lower_ms >= self.upper_ms:
            raise ValueError('lower window boundary must precede upper boundary')
        self._reset_until = self.reset_ms
        self._deadline = self.reset_ms + self.upper_ms

    def step(self, time_ms: float, *, falling: bool = False) -> bool:
        """Return ideal WDO high. High during grace alone does NOT permit ARM."""
        self._time_ms = _time(time_ms, self._time_ms)
        if time_ms >= self._deadline:
            # Collapse missed reset/retry cycles without an unbounded loop.
            cycle = self.reset_ms + self.upper_ms
            skipped = math.floor((time_ms - self._deadline) / cycle)
            self._reset_until = self._deadline + skipped * cycle + self.reset_ms
            self._deadline = self._reset_until + self.upper_ms
            self._last_edge = None
        if time_ms < self._reset_until:
            return False
        if falling:
            if self._last_edge is not None and time_ms - self._last_edge < self.lower_ms:
                self._last_edge = None
                self._reset_until = time_ms + self.reset_ms
                self._deadline = self._reset_until + self.upper_ms
                return False
            self._last_edge = time_ms
            self._deadline = time_ms + self.upper_ms
        return True


@dataclass
class SafetyChain:
    """Two-edge qualifier, delayed permission, async ARM clear, direct disarm.

    This truth/state reference excludes the first TPS3808 release delay:
    clear_n must already include it. It does not predict a measured shutdown
    latency or prove power-off behaviour of any selected IC.
    """
    qualify_ms: float = 20.0
    arm_latch: bool = field(default=False, init=False)
    _first: bool = field(default=False, init=False)
    _valid: bool = field(default=False, init=False)
    _qualified_at: float | None = field(default=None, init=False)
    _previous_arm: bool = field(default=False, init=False)
    _time_ms: float = field(default=0, init=False)

    def __post_init__(self):
        _positive(self.qualify_ms)

    def step(self, time_ms: float, *, clear_n: bool = True,
             aon_valid: bool = True, interlock_ok: bool = True,
             analog_rails_ok: bool = True, falling: bool = False,
             arm: bool = False) -> bool:
        self._time_ms = _time(time_ms, self._time_ms)
        clear = not (clear_n and aon_valid and interlock_ok)
        if clear:
            self._first = self._valid = False
            self._qualified_at = None
        elif falling:
            old_first = self._first
            self._first = True
            self._valid = old_first
        if self._valid and self._qualified_at is None:
            self._qualified_at = time_ms + self.qualify_ms
        qualified = (not clear and self._valid and self._qualified_at is not None
                     and time_ms >= self._qualified_at)
        rails_ok = qualified and analog_rails_ok and aon_valid
        if not rails_ok:
            self.arm_latch = False
        elif arm and not self._previous_arm:
            self.arm_latch = True
        self._previous_arm = arm
        return bool(rails_ok and self.arm_latch and arm)
