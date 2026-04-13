"""Walk cycle arm swing layer.

FK arm controls use circle normal (1,0,0) and inherit the skin
joint's world orientation:

    rotateX = twist  (axial roll along the bone)
    rotateY = droop  (up / down in the frontal plane)
    rotateZ = swing  (forward / back in the sagittal plane)
"""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer


class WalkArms(Layer):
    """Arm and scapula swing during a walk cycle."""

    name = 'Walk \u2013 Arms'

    DEFAULTS = {
        'shoulder_droop':        -30.0,   # rotateY -- arms hanging
        'scapula_droop':         -15.0,   # rotateY -- scapula offset
        'shoulder_swing_front':   20.0,   # rotateZ -- forward swing
        'shoulder_swing_back':   -10.0,   # rotateZ -- back swing
        'shoulder_twist':          0.0,   # rotateX -- axial roll
        'scapula_swing_front':     8.0,   # rotateZ -- scapula fore
        'scapula_swing_back':     -4.0,   # rotateZ -- scapula aft
        'elbow_bend_hi':          12.0,   # rotateZ -- max flexion
        'elbow_bend_lo':           0.0,   # rotateZ -- min flexion
        'wrist_swing_front':       6.0,   # rotateZ -- wrist fore
        'wrist_swing_back':       -3.0,   # rotateZ -- wrist aft
    }

    def __init__(self):
        super().__init__()
        self._params = dict(self.DEFAULTS)

    def controls(self):
        return [
            'FKScapula_R', 'FKShoulder_R', 'FKElbow_R', 'FKWrist_R',
            'FKScapula_L', 'FKShoulder_L', 'FKElbow_L', 'FKWrist_L',
        ]

    def fkik_state(self):
        return {
            'FKIKArm_L': 0,   # full FK
            'FKIKArm_R': 0,
        }

    def _arm_channels(self, side, phase):
        """Build channels for one arm.

        *phase* = 0 for R, 0.5 for L.

        The joint orient is mirrored between sides (bone X flips),
        which also flips M local Y.  We negate rotateY (droop) and
        rotateX (twist) for the left arm so the visual result is
        symmetric.  rotateZ (swing) keeps the same sign on both
        sides; phase opposition handles contra-lateral timing.
        """
        p = self._params
        sfx = '_' + side
        mir = 1 if side == 'R' else -1

        chs = []
        # Scapula / shoulder static droop (rotateY, constant)
        chs.append(Channel('FKScapula' + sfx, 'rotateY', Wave.CONSTANT,
                           amplitude=p['scapula_droop'] * mir, n_points=2,
                           label='{} Scap Droop'.format(side)))
        chs.append(Channel('FKShoulder' + sfx, 'rotateY', Wave.CONSTANT,
                           amplitude=p['shoulder_droop'] * mir, n_points=2,
                           label='{} Sh Droop'.format(side)))

        # Scapula swing (rotateZ) -- range slider
        scap_amp = (p['scapula_swing_front'] - p['scapula_swing_back']) / 2.0
        scap_off = (p['scapula_swing_front'] + p['scapula_swing_back']) / 2.0
        chs.append(Channel('FKScapula' + sfx, 'rotateZ', Wave.COSINE,
                           amplitude=scap_amp, offset=scap_off,
                           phase=phase, frequency=1, n_points=3,
                           label='{} Scap Swing'.format(side)))

        # Shoulder twist / swing
        chs.append(Channel('FKShoulder' + sfx, 'rotateX', Wave.COSINE,
                           amplitude=p['shoulder_twist'] * mir, phase=phase,
                           frequency=1, n_points=3,
                           label='{} Sh Twist'.format(side)))
        sh_amp = (p['shoulder_swing_front'] - p['shoulder_swing_back']) / 2.0
        sh_off = (p['shoulder_swing_front'] + p['shoulder_swing_back']) / 2.0
        chs.append(Channel('FKShoulder' + sfx, 'rotateZ', Wave.COSINE,
                           amplitude=sh_amp, offset=sh_off,
                           phase=phase, frequency=1, n_points=3,
                           label='{} Sh Swing'.format(side)))

        # Elbow bend -- peaks at mid-swing (explicit values, rotateZ)
        elb_hi = p['elbow_bend_hi']
        elb_lo = p['elbow_bend_lo']
        if side == 'R':
            elb = [elb_lo, elb_hi, elb_lo]
        else:
            elb = [elb_hi, elb_lo, elb_hi]
        chs.append(Channel('FKElbow' + sfx, 'rotateZ',
                           values=elb,
                           label='{} Elbow'.format(side)))

        # Wrist swing (rotateZ) -- range slider
        wr_amp = (p['wrist_swing_front'] - p['wrist_swing_back']) / 2.0
        wr_off = (p['wrist_swing_front'] + p['wrist_swing_back']) / 2.0
        chs.append(Channel('FKWrist' + sfx, 'rotateZ', Wave.COSINE,
                           amplitude=wr_amp, offset=wr_off,
                           phase=phase, frequency=1, n_points=3,
                           label='{} Wrist'.format(side)))
        return chs

    def channels(self):
        return self._arm_channels('R', 0.0) + self._arm_channels('L', 0.5)
