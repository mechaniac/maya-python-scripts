"""Channel dataclass -- one animated control.attribute."""

from dataclasses import dataclass
from typing import List, Optional

from .patterns import Wave, evaluate as wave_eval


@dataclass
class Channel:
    """Describes how a single control attribute oscillates over a cycle.

    If *values* is provided the explicit list is used directly.
    Otherwise values are computed from *wave*, *amplitude*, *offset*,
    *phase* and *frequency*, sampled at either *sample_at* normalised
    times or *n_points* evenly-spaced times.
    """

    ctrl: str
    attr: str
    wave: Wave = Wave.COSINE
    amplitude: float = 0.0
    offset: float = 0.0
    phase: float = 0.0
    frequency: float = 1.0
    n_points: int = 5
    values: Optional[List[float]] = None
    sample_at: Optional[List[float]] = None
    label: str = ''
    frame_offset: int = 0

    # ── query helpers ──

    def count(self):
        """Number of keyframe values this channel produces."""
        if self.values is not None:
            return len(self.values)
        if self.sample_at is not None:
            return len(self.sample_at)
        return self.n_points

    def normalized_times(self):
        """Return normalised [0-1] time positions for keying."""
        if self.sample_at is not None:
            return list(self.sample_at)
        n = self.count()
        if n < 2:
            return [0.5]
        return [i / (n - 1) for i in range(n)]

    def evaluate(self):
        """Return the list of keying values (amplitude-scaled + offset)."""
        if self.values is not None:
            return list(self.values)
        times = self.normalized_times()
        raw = [wave_eval(self.wave, t, self.frequency, self.phase)
               for t in times]
        return [v * self.amplitude + self.offset for v in raw]

    # ── extended keys (for curve offset / looping) ──

    def _interval(self):
        """Normalised interval between adjacent keys."""
        n = self.count()
        if n < 2:
            return 1.0
        times = self.normalized_times()
        # use the first gap as the canonical interval
        return times[1] - times[0]

    def extended_normalized_times(self):
        """Normalized times with one extra key before t=0 and after t=1."""
        times = self.normalized_times()
        ivl = self._interval()
        return [times[0] - ivl] + times + [times[-1] + ivl]

    def extended_evaluate(self):
        """Values list matching extended_normalized_times().

        Wave-based channels evaluate naturally at extended times.
        Explicit *values* lists wrap: prepend second-to-last, append second.
        """
        ext_times = self.extended_normalized_times()
        if self.values is not None:
            vals = list(self.values)
            # wrap: the curve is periodic so value before first = second-to-last,
            # value after last = second
            pre = vals[-2] if len(vals) >= 2 else vals[0]
            post = vals[1] if len(vals) >= 2 else vals[-1]
            return [pre] + vals + [post]
        raw = [wave_eval(self.wave, t, self.frequency, self.phase)
               for t in ext_times]
        return [v * self.amplitude + self.offset for v in raw]
