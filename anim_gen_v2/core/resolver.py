"""Cached, case-insensitive Maya node resolution."""

import maya.cmds as cmds

_cache = {}

_ALIASES = {
    'fkscapula1_l': 'fkscapula_l',
    'fkscapula_l':  'fkscapula1_l',
    'fkscapula1_r': 'fkscapula_r',
    'fkscapula_r':  'fkscapula1_r',
}


def clear():
    """Clear the resolution cache (call at the start of each generate)."""
    _cache.clear()


def resolve(name):
    """Return the actual scene node matching *name* (case-insensitive).

    Handles scapula aliases and numbered-suffix variants automatically.
    Returns ``None`` if no match is found.
    """
    if not name:
        return None
    if name in _cache:
        return _cache[name]

    low = name.lower()
    candidates = [low]

    alt = _ALIASES.get(low)
    if alt:
        candidates.append(alt)

    if low.endswith(('_l', '_r', '_m')):
        no_one = low.replace('1_', '_')
        if no_one not in candidates:
            candidates.append(no_one)

    all_nodes = set((cmds.ls(type='transform') or [])
                    + (cmds.ls(type='joint') or []))
    lower_map = {n.lower(): n for n in all_nodes}

    for c in candidates:
        if c in lower_map:
            _cache[name] = lower_map[c]
            return _cache[name]

    # Fallback: strip '1' from numbered suffixes
    search = low.replace('1_', '_')
    for n in all_nodes:
        if n.lower().replace('1_', '_') == search:
            _cache[name] = n
            return n

    _cache[name] = None
    return None
