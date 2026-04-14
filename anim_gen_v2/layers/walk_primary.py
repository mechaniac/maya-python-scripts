"""Walk cycle primary layer -- root, hip, and leg controls."""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer, range_amp_off


class WalkPrimary(Layer):
    """Root translation/rotation, hip swing, and leg stride."""

    name = 'Walk \u2013 Primary'

    DEFAULTS = {
        'stride':          70.0,
        'stride_width':    -3.0,
        'stride_width_swing': -3.0,
        'stride_height':   23.0,
        'foot_raise':       5.0,
        'foot_roll_heel': -20.0,
        'foot_roll_toe':    0.0,
        'hip_nod_front':   15.0,
        'hip_nod_back':   -15.0,
        'hip_lean':         0.0,
        'hip_twist':       25.0,
        'root_bounce_hi':   0.0,
        'root_bounce_lo':   0.0,
        'root_nod_front':   0.0,
        'root_nod_back':    0.0,
        'root_lean':        0.0,
        'root_twist':       0.0,
        'root_lr':          0.0,
        'root_bf':          4.0,
        'foot_bank':        0.0,
        'legs_offset':      0,
        'hip_offset':       0,
        'root_offset':      0,
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

        # ── feet stride (translateZ) ──
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
        # R foot lifts at 3/4 (idx 3), L foot lifts at 1/4 (idx 1)
        chs.append(Channel('IKLeg_R', 'translateX',
                           values=[-w, -w, -w, -ws, -w],
                           frame_offset=legs_off,
                           label='R Width'))
        chs.append(Channel('IKLeg_L', 'translateX',
                           values=[w, ws, w, w, w],
                           frame_offset=legs_off,
                           label='L Width'))

        # ── foot lift (translateY) ── pulse at passing position
        # Right foot lifts at three_quarter (idx 3 of 5)
        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[0, 0, 0, p['stride_height'], 0],
                           frame_offset=legs_off,
                           label='R Foot Lift'))
        # Left foot lifts at quarter (idx 1 of 5)
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[0, p['stride_height'], 0, 0, 0],
                           frame_offset=legs_off,
                           label='L Foot Lift'))

        # ── foot raise (rotateX) ── peak between passing positions
        # V1 keys at 6 points with a mid-between peak.
        # Right: peak at (three_quarter + end) / 2 = t 0.875
        chs.append(Channel('IKLeg_R', 'rotateX',
                           values=[0, 0, 0, 0, -p['foot_raise'], 0],
                           sample_at=[0, 0.25, 0.5, 0.75, 0.875, 1.0],
                           frame_offset=legs_off,
                           label='R Foot Raise'))
        # Left: peak at (quarter + mid) / 2 = t 0.375
        chs.append(Channel('IKLeg_L', 'rotateX',
                           values=[0, 0, -p['foot_raise'], 0, 0, 0],
                           sample_at=[0, 0.25, 0.375, 0.5, 0.75, 1.0],
                           frame_offset=legs_off,
                           label='L Foot Raise'))

        # ── foot roll (Roll attr on IKLeg) ──
        # heel strike at contact, toe push at mid-stance
        # Right: heel at 0/1, toe push-off around 0.5
        chs.append(Channel('IKLeg_R', 'Roll',
                           values=[p['foot_roll_heel'], 0,
                                   p['foot_roll_toe'], 0,
                                   p['foot_roll_heel']],
                           frame_offset=legs_off,
                           label='R Foot Roll'))
        # Left: phase shifted by half
        chs.append(Channel('IKLeg_L', 'Roll',
                           values=[p['foot_roll_toe'], 0,
                                   p['foot_roll_heel'], 0,
                                   p['foot_roll_toe']],
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

        # ── root bounce ── freq-2 cosine (two bounces per cycle)
        # Joint-aligned: local X = up/down
        bounce_amp, bounce_off = range_amp_off(p['root_bounce_hi'],
                                                p['root_bounce_lo'])
        chs.append(Channel('RootX_M', 'translateX', Wave.COSINE,
                           amplitude=bounce_amp,
                           offset=bounce_off,
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Bounce'))

        # ── root left-right ── side movement, freq-1, 3-point
        # Joint-aligned: local Z = left/right
        chs.append(Channel('RootX_M', 'translateZ', Wave.COSINE,
                           amplitude=p['root_lr'],
                           frequency=1, n_points=3,
                           frame_offset=root_off,
                           label='Root LR'))

        # ── root back-forth ── freq-2 cosine at 5 points
        # Joint-aligned: local Y = forward/back
        chs.append(Channel('RootX_M', 'translateY', Wave.COSINE,
                           amplitude=p['root_bf'],
                           frequency=2, n_points=5,
                           frame_offset=root_off,
                           label='Root BF'))

        # ── root nod / lean / twist ──
        # RootX_M joint-aligned (same as FK spine):
        #   rotateZ = nod (forward/back), rotateY = lean (side), rotateX = twist
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

        # ── foot bank (rotateZ on IK leg) ── inward tilt during push-off
        bank = p.get('foot_bank', 0.0)
        if bank:
            # Right foot banks inward (+Z) at mid-stance (t=0.5)
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
