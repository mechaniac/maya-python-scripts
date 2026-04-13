"""Load / save slider range settings for the animation generator UI."""

import json
import os

_DIR = os.path.dirname(__file__)
_DEFAULT_PATH = os.path.join(_DIR, 'settings.json')

_DEFAULTS = {
    'rotation':    [-60,   60],
    'translation': [-20,   20],
    'roll':        [-90,   90],
    'stride':      [  0,   40],
    'stride_wh':   [  0,   20],
    'foot_raise':  [  0,   40],
}


def _load_raw():
    if os.path.isfile(_DEFAULT_PATH):
        with open(_DEFAULT_PATH, 'r') as f:
            data = json.load(f)
        return data.get('ranges', {})
    return {}


def load():
    """Return merged range dict (file overrides defaults).  Always reads from disk."""
    merged = dict(_DEFAULTS)
    merged.update(_load_raw())
    # ensure all values are lists of 2 numbers
    for k, v in list(merged.items()):
        if not (isinstance(v, list) and len(v) == 2):
            merged[k] = _DEFAULTS.get(k, [-60, 60])
    return merged


def save(ranges):
    """Write ranges dict to settings.json."""
    data = {'ranges': ranges}
    with open(_DEFAULT_PATH, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def reset():
    """Reset to defaults and save."""
    save(dict(_DEFAULTS))
    return load()


def invalidate():
    """No-op, kept for API compatibility."""
    pass


def get(name):
    """Return a single range as a tuple (min, max, field_min, field_max)."""
    return tuple(load()[name])
