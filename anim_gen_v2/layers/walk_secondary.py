"""Walk cycle secondary layer -- spine, chest, neck, head."""

from ..core.channel import Channel
from ..core.patterns import Wave
from . import Layer

# Control names and default amplitudes per body part.
# Parameter naming: {part}_rz -> rotateZ, {part}_rx -> rotateX,
# {part}_ry -> rotateY, {part}_ry_offset -> rotateY offset.
_PARTS = (
    ('spine1', 'FKSpine1_M', 5.0, 2.0, 1.5, 0.0),
    ('chest',  'FKChest_M',  7.0, 3.0, 2.0, 0.0),
    ('neck',   'FKNeck_M',   4.0, 2.0, 1.0, 0.0),
    ('head',   'FKHead_M',   3.0, 1.5, 1.5, 0.0),
)


class WalkSecondary(Layer):
    """Spine chain counter-rotation driven by walk rhythm."""

    name = 'Walk \u2013 Secondary'

    def __init__(self):
        super().__init__()
        self._params = {}
        self._ctrl_map = {}
        for part, ctrl, rz, rx, ry, ry_off in _PARTS:
            self._ctrl_map[part] = ctrl
            self._params['{}_rz'.format(part)] = rz
            self._params['{}_rx'.format(part)] = rx
            self._params['{}_ry'.format(part)] = ry
            self._params['{}_ry_offset'.format(part)] = ry_off

    def controls(self):
        return list(self._ctrl_map.values())

    def channels(self):
        p = self._params
        chs = []
        for part, ctrl in self._ctrl_map.items():
            rz = p['{}_rz'.format(part)]
            rx = p['{}_rx'.format(part)]
            ry = p['{}_ry'.format(part)]
            ry_off = p['{}_ry_offset'.format(part)]

            # rotateZ -- 3-point alternating (freq 1)
            chs.append(Channel(ctrl, 'rotateZ', Wave.COSINE,
                               amplitude=rz, frequency=1, n_points=3,
                               label='{} rZ'.format(part)))
            # rotateX -- 3-point alternating (freq 1)
            chs.append(Channel(ctrl, 'rotateX', Wave.COSINE,
                               amplitude=rx, frequency=1, n_points=3,
                               label='{} rX'.format(part)))
            # rotateY -- 5-point alternating (freq 2) with offset
            chs.append(Channel(ctrl, 'rotateY', Wave.COSINE,
                               amplitude=ry, offset=ry_off,
                               frequency=2, n_points=5,
                               label='{} rY'.format(part)))
        return chs
