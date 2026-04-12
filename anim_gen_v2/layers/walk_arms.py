"""Walk cycle arm swing layer."""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer


class WalkArms(Layer):
    """Arm and scapula swing during a walk cycle."""

    name = 'Walk \u2013 Arms'

    DEFAULTS = {
        'shoulder_down':   -30.0,
        'scapula_down':    -15.0,
        'shoulder_swing':   20.0,
        'shoulder_twist':    0.0,
        'scapula_swing':     8.0,
        'elbow_bend':       12.0,
        'wrist_swing':       6.0,
    }

    def __init__(self):
        super().__init__()
        self._params = dict(self.DEFAULTS)

    def controls(self):
        return [
            'FKScapula_R', 'FKShoulder_R', 'FKElbow_R', 'FKWrist_R',
            'FKScapula_L', 'FKShoulder_L', 'FKElbow_L', 'FKWrist_L',
        ]

    def _arm_channels(self, side, phase):
        """Build channels for one arm.  *phase* = 0 for R, 0.5 for L."""
        p = self._params
        sfx = '_' + side

        chs = []
        # Scapula / shoulder static droop (constant at start + end)
        chs.append(Channel('FKScapula' + sfx, 'rotateZ', Wave.CONSTANT,
                           amplitude=p['scapula_down'], n_points=2,
                           label='{} Scap Down'.format(side)))
        chs.append(Channel('FKShoulder' + sfx, 'rotateZ', Wave.CONSTANT,
                           amplitude=p['shoulder_down'], n_points=2,
                           label='{} Sh Down'.format(side)))

        # Scapula swing
        chs.append(Channel('FKScapula' + sfx, 'rotateY', Wave.COSINE,
                           amplitude=p['scapula_swing'], phase=phase,
                           frequency=1, n_points=3,
                           label='{} Scap Swing'.format(side)))

        # Shoulder twist / swing
        chs.append(Channel('FKShoulder' + sfx, 'rotateX', Wave.COSINE,
                           amplitude=p['shoulder_twist'], phase=phase,
                           frequency=1, n_points=3,
                           label='{} Sh Twist'.format(side)))
        chs.append(Channel('FKShoulder' + sfx, 'rotateY', Wave.COSINE,
                           amplitude=p['shoulder_swing'], phase=phase,
                           frequency=1, n_points=3,
                           label='{} Sh Swing'.format(side)))

        # Elbow bend -- peaks at mid-swing (explicit values)
        if side == 'R':
            elb = [0, p['elbow_bend'], 0]
        else:
            elb = [p['elbow_bend'], 0, p['elbow_bend']]
        chs.append(Channel('FKElbow' + sfx, 'rotateY',
                           values=elb,
                           label='{} Elbow'.format(side)))

        # Wrist swing
        chs.append(Channel('FKWrist' + sfx, 'rotateY', Wave.COSINE,
                           amplitude=p['wrist_swing'], phase=phase,
                           frequency=1, n_points=3,
                           label='{} Wrist'.format(side)))
        return chs

    def channels(self):
        return self._arm_channels('R', 0.0) + self._arm_channels('L', 0.5)
