"""Run cycle primary layer -- root, hip, and leg controls.

Key differences from WalkPrimary:
  - Flight phase (both feet airborne) instead of double support.
  - Ball strike instead of heel strike.
  - Sharper, higher foot-lift arc.
  - Forward lean on root.
"""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer, range_amp_off


class RunPrimary(Layer):
    """Root translation/rotation, hip swing, and leg stride for a run."""

    name = 'Run \u2013 Primary'

    DEFAULTS = {
        'stride':           120.0,
        'stride_width':      -4.0,
        'stride_width_swing': -4.0,
        'stride_height':     35.0,
        'foot_raise':        12.0,
        'foot_roll_ball':   -10.0,   # ball strike angle (negative = toe up)
        'foot_roll_toe':     30.0,   # toe push-off angle
        'hip_nod_front':     18.0,
        'hip_nod_back':     -18.0,
        'hip_lean':           0.0,
        'hip_twist':         30.0,
        'root_bounce_hi':     4.0,
        'root_bounce_lo':    -2.0,
        'root_nod_front':     5.0,
        'root_nod_back':     -3.0,
        'root_lean':          0.0,
        'root_twist':         0.0,
        'root_lr':            0.0,
        'root_bf':            6.0,
        'foot_bank':          0.0,
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

    def channels(self):
        p = self._params
        chs = []
        half = p['stride'] / 2.0
        legs_off = int(p.get('legs_offset', 0))
        hip_off = int(p.get('hip_offset', 0))
        root_off = int(p.get('root_offset', 0))

        # ── feet stride (translateZ) ── cosine, same as walk
        chs.append(Channel('IKLeg_R', 'translateZ', Wave.COSINE,
                           amplitude=half, n_points=3,
                           frame_offset=legs_off,
                           label='R Stride'))
        chs.append(Channel('IKLeg_L', 'translateZ', Wave.COSINE,
                           amplitude=half, phase=0.5, n_points=3,
                           frame_offset=legs_off,
                           label='L Stride'))

        # ── feet width (translateX) ── swing out at passing position
        w = p['stride_width']
        ws = p['stride_width_swing']
        chs.append(Channel('IKLeg_R', 'translateX',
                           values=[-w, -w, -w, -ws, -w],
                           frame_offset=legs_off,
                           label='R Width'))
        chs.append(Channel('IKLeg_L', 'translateX',
                           values=[w, ws, w, w, w],
                           frame_offset=legs_off,
                           label='L Width'))

        # ── foot lift (translateY) ── flight phase: BOTH feet leave ground
        # Run has a sharper, peakier arc than walk.
        # Right foot: airborne from ~0.5 to ~1.0, peak at 0.75
        # Left foot:  airborne from ~0.0 to ~0.5, peak at 0.25
        # Small flight lift on the OTHER foot during push-off overlap
        h = p['stride_height']
        flight = h * 0.15  # subtle opposite-foot lift during flight phase
        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[0, flight, 0, h, 0],
                           frame_offset=legs_off,
                           label='R Foot Lift'))
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[0, h, 0, flight, 0],
                           frame_offset=legs_off,
                           label='L Foot Lift'))

        # ── foot raise (rotateX) ── more aggressive toe lift during swing
        fr = p['foot_raise']
        chs.append(Channel('IKLeg_R', 'rotateX',
                           values=[0, 0, 0, -fr, -fr * 0.5, 0],
                           sample_at=[0, 0.25, 0.5, 0.75, 0.875, 1.0],
                           frame_offset=legs_off,
                           label='R Foot Raise'))
        chs.append(Channel('IKLeg_L', 'rotateX',
                           values=[0, -fr, -fr * 0.5, 0, 0, 0],
                           sample_at=[0, 0.25, 0.375, 0.5, 0.75, 1.0],
                           frame_offset=legs_off,
                           label='L Foot Raise'))

        # ── foot roll (Roll attr) ── ball strike, no heel
        # Run: ball contacts first (slight negative), then rolls to toe push
        ball = p['foot_roll_ball']
        toe = p['foot_roll_toe']
        # Right foot: contact at 0, push-off ~0.25, airborne 0.5-1.0
        chs.append(Channel('IKLeg_R', 'Roll',
                           values=[ball, toe, 0, 0, ball],
                           frame_offset=legs_off,
                           label='R Foot Roll'))
        # Left foot: phase shifted by half
        chs.append(Channel('IKLeg_L', 'Roll',
                           values=[0, 0, ball, toe, 0],
                           frame_offset=legs_off,
                           label='L Foot Roll'))

        # ── hip nod / lean / twist ──
        hip_nod_amp, hip_nod_off = range_amp_off(p['hip_nod_front'],
                                                  p['hip_nod_back'])
        chs.append(Channel('HipSwinger_M', 'rotateZ', Wave.COSINE,
                           amplitude=hip_nod_amp, offset=hip_nod_off,
                           frequency=2, n_points=5,
                           frame_offset=hip_off,
                           label='Hip Nod'))
        chs.append(Channel('HipSwinger_M', 'rotateY', Wave.COSINE,
                           amplitude=p['hip_lean'],
                           frequency=1, n_points=3,
                           frame_offset=hip_off,
                           label='Hip Lean'))
        chs.append(Channel('HipSwinger_M', 'rotateX', Wave.COSINE,
                           amplitude=p['hip_twist'],
                           frequency=1, n_points=3,
                           frame_offset=hip_off,
                           label='Hip Twist'))

        # ── root bounce ── more exaggerated than walk
        bounce_amp, bounce_off = range_amp_off(p['root_bounce_hi'],
                                                p['root_bounce_lo'])
        chs.append(Channel('RootX_M', 'translateX', Wave.COSINE,
                           amplitude=bounce_amp,
                           offset=bounce_off,
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Bounce'))

        # ── root left-right ──
        chs.append(Channel('RootX_M', 'translateZ', Wave.COSINE,
                           amplitude=p['root_lr'],
                           frequency=1, n_points=3,
                           frame_offset=root_off,
                           label='Root LR'))

        # ── root back-forth ──
        chs.append(Channel('RootX_M', 'translateY', Wave.COSINE,
                           amplitude=p['root_bf'],
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Root BF'))

        # ── root nod / lean / twist ──
        nod_amp, nod_off = range_amp_off(p['root_nod_front'],
                                          p['root_nod_back'])
        chs.append(Channel('RootX_M', 'rotateZ', Wave.COSINE,
                           amplitude=nod_amp, offset=nod_off,
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Root Nod'))
        chs.append(Channel('RootX_M', 'rotateY', Wave.COSINE,
                           amplitude=p['root_lean'],
                           frequency=1, n_points=3,
                           frame_offset=root_off,
                           label='Root Lean'))
        chs.append(Channel('RootX_M', 'rotateX', Wave.COSINE,
                           amplitude=p['root_twist'],
                           frequency=1, n_points=3,
                           frame_offset=root_off,
                           label='Root Twist'))

        # ── foot bank (rotateZ on IK leg) ──
        bank = p.get('foot_bank', 0.0)
        if bank:
            chs.append(Channel('IKLeg_R', 'rotateZ', Wave.COSINE,
                               amplitude=-bank,
                               frequency=1, n_points=3,
                               frame_offset=legs_off,
                               label='R Foot Bank'))
            chs.append(Channel('IKLeg_L', 'rotateZ', Wave.COSINE,
                               amplitude=bank,
                               phase=0.5, frequency=1, n_points=3,
                               frame_offset=legs_off,
                               label='L Foot Bank'))

        return chs
