"""Cached, case-insensitive Maya node resolution."""

import maya.cmds as cmds

_cache = {}
_scene_map = {}   # lower-case name -> actual scene node

_ALIASES = {
    'fkscapula1_l': 'fkscapula_l',
    'fkscapula_l':  'fkscapula1_l',
    'fkscapula1_r': 'fkscapula_r',
    'fkscapula_r':  'fkscapula1_r',
}


def clear():
    """Clear the resolution cache (call at the start of each generate)."""
    _cache.clear()
    _scene_map.clear()
    all_nodes = set((cmds.ls(type='transform') or [])
                    + (cmds.ls(type='joint') or []))
    for n in all_nodes:
        _scene_map[n.lower()] = n


def resolve(name):
    """Return the actual scene node matching *name* (case-insensitive).

    Handles scapula aliases and numbered-suffix variants automatically.
    Returns ``None`` if no match is found.
    """
    if not name:
        return None
    if name in _cache:
        return _cache[name]

    # Lazy-populate scene map if clear() hasn't been called yet
    if not _scene_map:
        all_nodes = set((cmds.ls(type='transform') or [])
                        + (cmds.ls(type='joint') or []))
        for n in all_nodes:
            _scene_map[n.lower()] = n

    low = name.lower()
    candidates = [low]

    alt = _ALIASES.get(low)
    if alt:
        candidates.append(alt)

    if low.endswith(('_l', '_r', '_m')):
        no_one = low.replace('1_', '_')
        if no_one not in candidates:
            candidates.append(no_one)

    for c in candidates:
        if c in _scene_map:
            _cache[name] = _scene_map[c]
            return _cache[name]

    # Fallback: strip '1' from numbered suffixes
    search = low.replace('1_', '_')
    for k, v in _scene_map.items():
        if k.replace('1_', '_') == search:
            _cache[name] = v
            return v

    _cache[name] = None
    return None
