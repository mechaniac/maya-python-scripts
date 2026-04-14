"""Run cycle primary layer -- built from scratch for run mechanics.

Structural differences from the walk generator:
  - Foot arc:    Short ground contact (~25 %), high aggressive peak.
                 Walk keeps foot on ground ~60 %.
  - Root bounce: LOW at foot-strike (impact absorption), HIGH during
                 flight phase.  Opposite phase to the walk's pendulum
                 vault where the body is highest at mid-stance.
  - Forward lean: Constant forward pitch on the root (run posture).
  - Ball-first contact with aggressive toe push-off.
  - No secondary detail channels (width, raise, bank, nod, lean, etc.)
    -- those can be re-introduced once the core feels right.
"""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer


class RunPrimary(Layer):
    """Minimal run cycle: stride, foot arc, roll, bounce, twist, lean."""

    name = 'Run \u2013 Primary'

    DEFAULTS = {
        'stride':           120.0,
        'stride_height':     35.0,
        'foot_roll_ball':   -10.0,
        'foot_roll_toe':     30.0,
        'root_bounce_hi':     5.0,   # flight apex (up)
        'root_bounce_lo':    -3.0,   # contact compression (down)
        'hip_twist':         30.0,
        'forward_lean':       5.0,   # constant root pitch (rotateZ)
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
        legs_off = int(p.get('legs_offset', 0))
        hip_off  = int(p.get('hip_offset', 0))
        root_off = int(p.get('root_offset', 0))

        # ── 1. stride (translateZ) ── cosine back-and-forth ──
        chs.append(Channel('IKLeg_R', 'translateZ', Wave.COSINE,
                           amplitude=half, n_points=3,
                           frame_offset=legs_off,
                           label='R Stride'))
        chs.append(Channel('IKLeg_L', 'translateZ', Wave.COSINE,
                           amplitude=half, phase=0.5, n_points=3,
                           frame_offset=legs_off,
                           label='L Stride'))

        # ── 2. foot arc (translateY) ──
        # 7 evenly-spaced keys: t = [0, 1/6, 2/6, 3/6, 4/6, 5/6, 1.0]
        #
        # R foot:  contact 0–2/6 (~33 %), peak at 4/6 (knee-drive phase),
        #          small 'arc' value at 5/6 on the way down.
        # L foot:  exact same shape shifted half a cycle (3 positions).
        #
        # At t=0: R = 0 (ground), L = arc (slightly elevated, descending).
        # Neither foot at max height at the cycle boundary.
        #
        # Walk comparison: [0, 0, 0, h, 0] → 60 % ground, symmetric bump.
        arc = h * 0.2   # flight-phase transition height at cycle seam

        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[0, 0, 0, arc, h, arc, 0],
                           frame_offset=legs_off,
                           label='R Foot Arc'))
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[arc, h, arc, 0, 0, 0, arc],
                           frame_offset=legs_off,
                           label='L Foot Arc'))

        # ── 3. foot roll (Roll) ── ball strike → toe push ──
        ball = p['foot_roll_ball']
        toe  = p['foot_roll_toe']
        chs.append(Channel('IKLeg_R', 'Roll',
                           values=[ball, toe, 0, 0, ball],
                           frame_offset=legs_off,
                           label='R Roll'))
        chs.append(Channel('IKLeg_L', 'Roll',
                           values=[0, 0, ball, toe, 0],
                           frame_offset=legs_off,
                           label='L Roll'))

        # ── 4. root bounce (translateX) ──
        # Run: LOW at contact (0, 0.5), HIGH during flight (0.25, 0.75).
        # Walk uses cosine freq=2 → HIGH at contact.  Opposite phase.
        lo = p['root_bounce_lo']
        hi = p['root_bounce_hi']
        chs.append(Channel('RootX_M', 'translateX',
                           values=[lo, hi, lo, hi, lo],
                           frame_offset=root_off,
                           label='Root Bounce'))

        # ── 5. hip twist (rotateX) ── counter-rotation, once per cycle ──
        chs.append(Channel('HipSwinger_M', 'rotateX', Wave.COSINE,
                           amplitude=p['hip_twist'],
                           frequency=1, n_points=3,
                           frame_offset=hip_off,
                           label='Hip Twist'))

        # ── 6. forward lean (rotateZ on root) ── constant run posture ──
        fwd = p.get('forward_lean', 0.0)
        if fwd:
            chs.append(Channel('RootX_M', 'rotateZ', Wave.CONSTANT,
                               amplitude=fwd, n_points=3,
                               frame_offset=root_off,
                               label='Forward Lean'))

        return chs
