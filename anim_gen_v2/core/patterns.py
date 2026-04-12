"""Waveform shapes and sampling for animation oscillation patterns.

Every oscillation in the generator is described by a *Wave* shape
evaluated at normalised time positions in [0, 1].  The ``sample``
function returns raw multiplier values in [-1, 1]; amplitude and
offset scaling is applied later by the Channel.
"""

import math
from enum import Enum


class Wave(Enum):
    """Available waveform shapes."""
    COSINE = 'cosine'
    SINE = 'sine'
    CONSTANT = 'constant'


def evaluate(wave, t, frequency=1.0, phase=0.0):
    """Evaluate *wave* at normalised time *t* in [0, 1].

    Returns a float in [-1, 1] (CONSTANT always returns 1.0).

    The angle is computed as ``2 * pi * (frequency * t + phase)``
    so *phase* is in cycles (0.5 = 180 degrees).
    """
    if wave is Wave.CONSTANT:
        return 1.0
    angle = 2.0 * math.pi * (frequency * t + phase)
    if wave is Wave.COSINE:
        return math.cos(angle)
    if wave is Wave.SINE:
        return math.sin(angle)
    return 0.0


def sample(wave, n_points, frequency=1.0, phase=0.0):
    """Sample *wave* at *n_points* evenly spaced over [0, 1].

    Returns a list of floats.
    """
    if n_points < 1:
        return []
    if n_points == 1:
        return [evaluate(wave, 0.5, frequency, phase)]
    return [evaluate(wave, i / (n_points - 1), frequency, phase)
            for i in range(n_points)]
