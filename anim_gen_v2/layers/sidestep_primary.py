"""Sidestep (strafe) primary layer -- basic lateral stepping.

Core differences from walk/run:
  - Primary motion axis is lateral (translateX on IK legs) instead
    of forward (translateZ).  Both feet reach in the same direction,
    alternating like a shuffle step.
  - Direction switch: ``strafe_right`` flips the sign of all lateral
    channels so the same code produces left or right strafes.
  - Root sways laterally (translateZ) following the stepping pattern.
  - Hip leans into the travel direction (constant rotateY).
  - Root bounce uses walk-style phase (HIGH at mid-stance).
  - No secondary detail channels yet -- kept minimal on purpose.
"""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer, range_amp_off


class SidestepPrimary(Layer):
    """Minimal sidestep: lateral stride, foot arc, roll, bounce, sway, lean."""

    name = 'Sidestep \u2013 Primary'

    DEFAULTS = {
        'stride':            80.0,   # lateral reach distance
        'stride_height':     20.0,   # foot arc peak
        'foot_roll_heel':    -8.0,
        'foot_roll_toe':     15.0,
        'root_bounce_hi':     3.0,
        'root_bounce_lo':    -2.0,
        'root_sway':          5.0,   # lateral root shift (translateZ)
        'hip_lean':           8.0,   # lean into travel direction (rotateY)
        'strafe_right':       1.0,   # 1.0 = right, 0.0 = left
        'legs_offset':        0,
        'hip_offset':         0,
        'root_offset':        0,
    }

    def __init__(self):
        super().__init__()
        self._params = dict(self.DEFAULTS)

    def controls(self):
        return ['IKLeg_R', 'IKLeg_L', 'HipSwinger_M', 'RootX_M']

    def fkik_state(self):
        return {
            'FKIKLeg_L': 10,   # full IK
            'FKIKLeg_R': 10,
        }

    # ── channel generation ──

    def channels(self):
        p = self._params
        chs = []
        half = p['stride'] / 2.0
        h    = p['stride_height']
        d    = 1.0 if p.get('strafe_right', 1.0) >= 0.5 else -1.0
        legs_off = int(p.get('legs_offset', 0))
        hip_off  = int(p.get('hip_offset', 0))
        root_off = int(p.get('root_offset', 0))

        # ── 1. lateral stride (translateX) ── cosine shuffle ──
        # Both feet oscillate laterally in the same direction,
        # 180° out of phase so they alternate.
        chs.append(Channel('IKLeg_R', 'translateX', Wave.COSINE,
                           amplitude=half * d, n_points=3,
                           frame_offset=legs_off,
                           label='R Lateral Stride'))
        chs.append(Channel('IKLeg_L', 'translateX', Wave.COSINE,
                           amplitude=half * d, phase=0.5, n_points=3,
                           frame_offset=legs_off,
                           label='L Lateral Stride'))

        # ── 2. foot arc (translateY) ── walk-style 60 % ground contact ──
        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[0, 0, 0, h, 0],
                           frame_offset=legs_off,
                           label='R Foot Arc'))
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[0, h, 0, 0, 0],
                           frame_offset=legs_off,
                           label='L Foot Arc'))

        # ── 3. foot roll (Roll) ── heel strike → toe push ──
        heel = p['foot_roll_heel']
        toe  = p['foot_roll_toe']
        chs.append(Channel('IKLeg_R', 'Roll',
                           values=[heel, toe, 0, 0, heel],
                           frame_offset=legs_off,
                           label='R Roll'))
        chs.append(Channel('IKLeg_L', 'Roll',
                           values=[0, 0, heel, toe, 0],
                           frame_offset=legs_off,
                           label='L Roll'))

        # ── 4. root bounce (translateX) ── walk-style, HIGH at mid-stance ──
        amp, off = range_amp_off(p['root_bounce_hi'], p['root_bounce_lo'])
        chs.append(Channel('RootX_M', 'translateX', Wave.COSINE,
                           amplitude=amp, offset=off,
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Root Bounce'))

        # ── 5. root sway (translateZ) ── lateral shift following legs ──
        sway = p['root_sway']
        if sway:
            chs.append(Channel('RootX_M', 'translateZ', Wave.COSINE,
                               amplitude=sway * d,
                               frequency=1, n_points=3,
                               frame_offset=root_off,
                               label='Root Sway'))

        # ── 6. hip lean (rotateY) ── constant lean into travel direction ──
        lean = p.get('hip_lean', 0.0)
        if lean:
            chs.append(Channel('HipSwinger_M', 'rotateY', Wave.CONSTANT,
                               amplitude=lean * d, n_points=3,
                               frame_offset=hip_off,
                               label='Hip Lean'))

        return chs
