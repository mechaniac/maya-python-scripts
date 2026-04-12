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
from . import Layer

# (part_key, ctrl_name, nod_front, nod_back, lean, twist)
_PARTS = (
    ('spine', 'FKSpine_M',  5.0, -5.0, 2.0, 1.5),
    ('chest',  'FKChest_M',  7.0, -7.0, 3.0, 2.0),
    ('neck',   'FKNeck_M',   4.0, -4.0, 2.0, 1.0),
    ('head',   'FKHead_M',   3.0, -3.0, 1.5, 1.5),
)


class WalkSecondary(Layer):
    """Spine chain counter-rotation driven by walk rhythm."""

    name = 'Walk \u2013 Secondary'

    def __init__(self):
        super().__init__()
        self._params = {}
        self._ctrl_map = {}
        for part, ctrl, nod_f, nod_b, lean, twist in _PARTS:
            self._ctrl_map[part] = ctrl
            self._params['{}_nod_front'.format(part)] = nod_f
            self._params['{}_nod_back'.format(part)] = nod_b
            self._params['{}_lean'.format(part)] = lean
            self._params['{}_twist'.format(part)] = twist

    def controls(self):
        return list(self._ctrl_map.values())

    def fkik_state(self):
        return {'FKIKSpine_M': 0}   # full FK

    def channels(self):
        p = self._params
        chs = []
        for part, ctrl in self._ctrl_map.items():
            nod_f = p['{}_nod_front'.format(part)]
            nod_b = p['{}_nod_back'.format(part)]
            lean = p['{}_lean'.format(part)]
            twist = p['{}_twist'.format(part)]
            nod_amp = (nod_f - nod_b) / 2.0
            nod_off = (nod_f + nod_b) / 2.0

            # rotateZ = nod (forward/back pitch) -- 5-point, twice per cycle
            chs.append(Channel(ctrl, 'rotateZ', Wave.COSINE,
                               amplitude=nod_amp, offset=nod_off,
                               frequency=2, n_points=5,
                               label='{} Nod'.format(part)))
            # rotateY = lean (lateral side bend) -- 3-point, once per cycle
            chs.append(Channel(ctrl, 'rotateY', Wave.COSINE,
                               amplitude=lean, frequency=1, n_points=3,
                               label='{} Lean'.format(part)))
            # rotateX = twist (axial roll) -- 3-point, once per cycle
            chs.append(Channel(ctrl, 'rotateX', Wave.COSINE,
                               amplitude=twist,
                               frequency=1, n_points=3,
                               label='{} Twist'.format(part)))
        return chs
