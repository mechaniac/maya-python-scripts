"""Walk cycle secondary layer -- spine, chest, neck, head.

FK spine controls use circle normal (1,0,0) and inherit the skin
joint's world orientation.  With ``oj='xyz'`` the local X axis runs
along the bone (upward through the spine), giving:

    rotateX = twist   (axial roll around the spine)
    rotateY = lean    (lateral side bend)
    rotateZ = nod     (forward / back pitch)
"""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer, range_amp_off


class WalkSecondary(Layer):
    """Spine chain counter-rotation driven by walk rhythm."""

    name = 'Walk \u2013 Secondary'

    DEFAULTS = {
        'spine_nod_front':  5.0,  'spine_nod_back':  0.0,
        'spine_lean': 0.0, 'spine_twist': 0.0, 'spine_offset': 0,
        'chest_nod_front':  0.0,  'chest_nod_back':  0.0,
        'chest_lean': 0.0, 'chest_twist': 0.0, 'chest_offset': 0,
        'neck_nod_front':   0.0,  'neck_nod_back':   0.0,
        'neck_lean': 0.0, 'neck_twist': 0.0, 'neck_offset': 0,
        'head_nod_front':   0.0,  'head_nod_back':   0.0,
        'head_lean': 0.0, 'head_twist': 0.0, 'head_offset': 0,
    }

    _CTRL_MAP = {
        'spine': 'FKSpine_M',
        'chest': 'FKChest_M',
        'neck':  'FKNeck_M',
        'head':  'FKHead_M',
    }

    def __init__(self):
        super().__init__()
        self._params = dict(self.DEFAULTS)

    def controls(self):
        return list(self._CTRL_MAP.values())

    def fkik_state(self):
        return {'FKIKSpine_M': 0}   # full FK

    def channels(self):
        p = self._params
        chs = []
        for part, ctrl in self._CTRL_MAP.items():
            nod_f = p['{}_nod_front'.format(part)]
            nod_b = p['{}_nod_back'.format(part)]
            lean = p['{}_lean'.format(part)]
            twist = p['{}_twist'.format(part)]
            off = int(p.get('{}_offset'.format(part), 0))
            nod_amp, nod_off = range_amp_off(nod_f, nod_b)

            # rotateZ = nod (forward/back pitch) -- 5-point, twice per cycle
            chs.append(Channel(ctrl, 'rotateZ', Wave.COSINE,
                               amplitude=nod_amp, offset=nod_off,
                               frequency=2, n_points=5,
                               frame_offset=off,
                               label='{} Nod'.format(part)))
            # rotateY = lean (lateral side bend) -- 3-point, once per cycle
            chs.append(Channel(ctrl, 'rotateY', Wave.COSINE,
                               amplitude=lean, frequency=1, n_points=3,
                               frame_offset=off,
                               label='{} Lean'.format(part)))
            # rotateX = twist (axial roll) -- 3-point, once per cycle
            chs.append(Channel(ctrl, 'rotateX', Wave.COSINE,
                               amplitude=-twist,
                               frequency=1, n_points=3,
                               frame_offset=off,
                               label='{} Twist'.format(part)))
        return chs
