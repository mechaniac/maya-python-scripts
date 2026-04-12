"""Walk cycle primary layer -- root, hip, and leg controls."""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer


class WalkPrimary(Layer):
    """Root translation/rotation, hip swing, and leg stride."""

    name = 'Walk \u2013 Primary'

    DEFAULTS = {
        'stride':          10.0,
        'stride_width':     2.0,
        'stride_height':    4.0,
        'foot_raise':      10.0,
        'hip_nod':         10.0,
        'hip_lean':         5.0,
        'hip_twist':        0.0,
        'root_bounce':      1.5,
        'root_nod':         1.0,
        'root_lean':        2.0,
        'root_twist':       0.0,
        'root_lr':          0.0,
        'root_bf':          0.0,
        'bounce_offset':    0.0,
        'root_nod_offset':  0.0,
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

        # ── feet stride (translateZ) ──
        chs.append(Channel('IKLeg_R', 'translateZ', Wave.COSINE,
                           amplitude=half, n_points=3,
                           label='R Stride'))
        chs.append(Channel('IKLeg_L', 'translateZ', Wave.COSINE,
                           amplitude=half, phase=0.5, n_points=3,
                           label='L Stride'))

        # ── feet width (translateX) ── constant
        chs.append(Channel('IKLeg_R', 'translateX', Wave.CONSTANT,
                           amplitude=p['stride_width'], n_points=3,
                           label='R Width'))
        chs.append(Channel('IKLeg_L', 'translateX', Wave.CONSTANT,
                           amplitude=-p['stride_width'], n_points=3,
                           label='L Width'))

        # ── foot lift (translateY) ── pulse at passing position
        # Right foot lifts at three_quarter (idx 3 of 5)
        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[0, 0, 0, p['stride_height'], 0],
                           label='R Foot Lift'))
        # Left foot lifts at quarter (idx 1 of 5)
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[0, p['stride_height'], 0, 0, 0],
                           label='L Foot Lift'))

        # ── foot raise (rotateX) ── peak between passing positions
        # V1 keys at 6 points with a mid-between peak.
        # Right: peak at (three_quarter + end) / 2 = t 0.875
        chs.append(Channel('IKLeg_R', 'rotateX',
                           values=[0, 0, 0, 0, p['foot_raise'], 0],
                           sample_at=[0, 0.25, 0.5, 0.75, 0.875, 1.0],
                           label='R Foot Raise'))
        # Left: peak at (quarter + mid) / 2 = t 0.375
        chs.append(Channel('IKLeg_L', 'rotateX',
                           values=[0, 0, p['foot_raise'], 0, 0, 0],
                           sample_at=[0, 0.25, 0.375, 0.5, 0.75, 1.0],
                           label='L Foot Raise'))

        # ── hip nod / lean / twist ──
        # HipSwinger_M joint-aligned (same as FK spine):
        #   rotateZ = nod (forward/back), rotateY = lean (side), rotateX = twist
        chs.append(Channel('HipSwinger_M', 'rotateZ', Wave.COSINE,
                           amplitude=p['hip_nod'],
                           frequency=2, n_points=5,
                           label='Hip Nod'))
        chs.append(Channel('HipSwinger_M', 'rotateY', Wave.COSINE,
                           amplitude=p['hip_lean'],
                           frequency=1, n_points=3,
                           label='Hip Lean'))
        chs.append(Channel('HipSwinger_M', 'rotateX', Wave.COSINE,
                           amplitude=p['hip_twist'],
                           frequency=1, n_points=3,
                           label='Hip Twist'))

        # ── root bounce ── freq-2 cosine (two bounces per cycle)
        # Joint-aligned: local X = up/down
        chs.append(Channel('RootX_M', 'translateX', Wave.COSINE,
                           amplitude=p['root_bounce'],
                           offset=p['bounce_offset'],
                           frequency=2, n_points=5,
                           label='Bounce'))

        # ── root left-right ── side movement, freq-1, 3-point
        # Joint-aligned: local Z = left/right
        chs.append(Channel('RootX_M', 'translateZ', Wave.COSINE,
                           amplitude=p['root_lr'],
                           frequency=1, n_points=3,
                           label='Root LR'))

        # ── root back-forth ── freq-2 cosine at 5 points
        # Joint-aligned: local Y = forward/back
        chs.append(Channel('RootX_M', 'translateY', Wave.COSINE,
                           amplitude=p['root_bf'],
                           frequency=2, n_points=5,
                           label='Root BF'))

        # ── root nod / lean / twist ──
        # RootX_M joint-aligned (same as FK spine):
        #   rotateZ = nod (forward/back), rotateY = lean (side), rotateX = twist
        chs.append(Channel('RootX_M', 'rotateZ', Wave.COSINE,
                           amplitude=p['root_nod'],
                           offset=p['root_nod_offset'],
                           frequency=2, n_points=5,
                           label='Root Nod'))
        chs.append(Channel('RootX_M', 'rotateY', Wave.COSINE,
                           amplitude=p['root_lean'],
                           frequency=1, n_points=3,
                           label='Root Lean'))
        chs.append(Channel('RootX_M', 'rotateX', Wave.COSINE,
                           amplitude=p['root_twist'],
                           frequency=1, n_points=3,
                           label='Root Twist'))

        return chs
