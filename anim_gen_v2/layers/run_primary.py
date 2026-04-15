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
from . import Layer, range_amp_off


class RunPrimary(Layer):
    """Minimal run cycle: stride, foot arc, roll, bounce, twist, lean."""

    name = 'Run \u2013 Primary'

    DEFAULTS = {
        'stride_front':      60.0,
        'stride_back':      -60.0,
        'stride_width':      -3.0,
        'stride_width_swing': -3.0,
        'stride_height':     35.0,
        'stride_height_2':   20.0,
        'foot_raise_front': -10.0,
        'foot_raise_back':    5.0,
        'foot_roll_front':  -10.0,
        'foot_roll_back':    30.0,
        # Root translate
        'root_bounce_hi':     5.0,   # flight apex (up)  – tX
        'root_bounce_lo':    -3.0,   # contact compression (down) – tX
        'root_drive_front':   0.0,   # forward shift – tY
        'root_drive_back':    0.0,   # backward shift – tY
        'root_sway':          0.0,   # left/right shift – tZ
        # Root rotate
        'root_nod_front':     5.0,   # forward pitch – rZ (was forward_lean)
        'root_nod_back':      0.0,   # backward pitch – rZ
        'root_lean':          0.0,   # lateral tilt – rY
        'root_twist':         0.0,   # axial rotation – rX
        # Hip
        'hip_twist':         30.0,
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
        stride_amp, stride_off = range_amp_off(p['stride_back'],
                                                 p['stride_front'])
        h    = p['stride_height']
        legs_off = int(p.get('legs_offset', 0))
        hip_off  = int(p.get('hip_offset', 0))
        root_off = int(p.get('root_offset', 0))

        # ── 1. stride (translateZ) ── cosine back-and-forth ──
        chs.append(Channel('IKLeg_R', 'translateZ', Wave.COSINE,
                           amplitude=stride_amp, offset=stride_off,
                           n_points=3,
                           frame_offset=legs_off,
                           label='R Stride'))
        chs.append(Channel('IKLeg_L', 'translateZ', Wave.COSINE,
                           amplitude=stride_amp, offset=stride_off,
                           phase=0.5, n_points=3,
                           frame_offset=legs_off,
                           label='L Stride'))

        # ── 2. feet width (translateX) ── swing out at passing position
        w = p['stride_width']
        ws = p['stride_width_swing']
        # R foot lifts at 4/6, L foot lifts at 1/6 (7-pt arc)
        # Using 5-key approx: R swings at idx 3, L at idx 1
        chs.append(Channel('IKLeg_R', 'translateX',
                           values=[-w, -w, -w, -ws, -w],
                           frame_offset=legs_off,
                           label='R Width'))
        chs.append(Channel('IKLeg_L', 'translateX',
                           values=[w, ws, w, w, w],
                           frame_offset=legs_off,
                           label='L Width'))

        # ── 3. foot arc (translateY) ──
        # 5 evenly-spaced keys: t = [0, 0.25, 0.5, 0.75, 1.0]
        #
        # Each leg has only ONE ground-contact frame (0) and stays
        # raised the rest of the cycle.  Two height values let the
        # peak (v2) differ from the sustained raise (v1).
        #   L: v1, v2, v1,  0, v1
        #   R: v1,  0, v1, v2, v1
        h1 = p['stride_height']
        h2 = p['stride_height_2']

        chs.append(Channel('IKLeg_R', 'translateY',
                           values=[h1, 0, h1, h2, h1],
                           frame_offset=legs_off,
                           label='R Foot Arc'))
        chs.append(Channel('IKLeg_L', 'translateY',
                           values=[h1, h2, h1, 0, h1],
                           frame_offset=legs_off,
                           label='L Foot Arc'))

        # ── 3b. foot raise (rotateX) ── cosine pitch like stride ──
        raise_amp, raise_off = range_amp_off(p['foot_raise_front'],
                                              p['foot_raise_back'])
        chs.append(Channel('IKLeg_R', 'rotateX', Wave.COSINE,
                           amplitude=raise_amp, offset=raise_off,
                           n_points=3,
                           frame_offset=legs_off,
                           label='R Foot Raise'))
        chs.append(Channel('IKLeg_L', 'rotateX', Wave.COSINE,
                           amplitude=raise_amp, offset=raise_off,
                           phase=0.5, n_points=3,
                           frame_offset=legs_off,
                           label='L Foot Raise'))

        # ── 4. foot roll (Roll) ── cosine like stride/raise ──
        roll_amp, roll_off = range_amp_off(p['foot_roll_back'],
                                            p['foot_roll_front'])
        chs.append(Channel('IKLeg_R', 'Roll', Wave.COSINE,
                           amplitude=roll_amp, offset=roll_off,
                           n_points=3,
                           frame_offset=legs_off,
                           label='R Roll'))
        chs.append(Channel('IKLeg_L', 'Roll', Wave.COSINE,
                           amplitude=roll_amp, offset=roll_off,
                           phase=0.5, n_points=3,
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
                           label='Bounce'))

        # ── 5. root drive (translateY) ── forward/back shift, freq-2 ──
        drive_amp, drive_off = range_amp_off(p['root_drive_front'],
                                              p['root_drive_back'])
        if drive_amp or drive_off:
            chs.append(Channel('RootX_M', 'translateY', Wave.COSINE,
                               amplitude=drive_amp, offset=drive_off,
                               frequency=2, n_points=5,
                               frame_offset=root_off,
                               label='Drive'))

        # ── 6. root sway (translateZ) ── left/right shift, freq-1 ──
        if p['root_sway']:
            chs.append(Channel('RootX_M', 'translateZ', Wave.COSINE,
                               amplitude=p['root_sway'],
                               frequency=1, n_points=3,
                               frame_offset=root_off,
                               label='Sway'))

        # ── 7. root nod (rotateZ) ── forward/back pitch, freq-2 ──
        nod_amp, nod_off = range_amp_off(p['root_nod_front'],
                                          p['root_nod_back'])
        if nod_amp or nod_off:
            chs.append(Channel('RootX_M', 'rotateZ', Wave.COSINE,
                               amplitude=nod_amp, offset=nod_off,
                               frequency=2, n_points=5,
                               frame_offset=root_off,
                               label='Nod'))

        # ── 8. root lean (rotateY) ── lateral tilt, freq-1 ──
        if p['root_lean']:
            chs.append(Channel('RootX_M', 'rotateY', Wave.COSINE,
                               amplitude=p['root_lean'],
                               frequency=1, n_points=3,
                               frame_offset=root_off,
                               label='Lean'))

        # ── 9. root twist (rotateX) ── axial rotation, freq-1 ──
        if p['root_twist']:
            chs.append(Channel('RootX_M', 'rotateX', Wave.COSINE,
                               amplitude=p['root_twist'],
                               frequency=1, n_points=3,
                               frame_offset=root_off,
                               label='Twist'))

        # ── 10. hip twist (rotateX) ── counter-rotation, once per cycle ──
        chs.append(Channel('HipSwinger_M', 'rotateX', Wave.COSINE,
                           amplitude=p['hip_twist'],
                           frequency=1, n_points=3,
                           frame_offset=hip_off,
                           label='Hip Twist'))

        return chs
