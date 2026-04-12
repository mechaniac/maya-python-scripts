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
