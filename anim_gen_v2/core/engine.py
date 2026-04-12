"""Keyframe engine -- batch keying with undo-chunk wrapper."""

import maya.cmds as cmds

from . import resolver


# ── timeline helpers ──

def timeline_range():
    """Return ``(start, end)`` from playback options."""
    return (cmds.playbackOptions(q=True, min=True),
            cmds.playbackOptions(q=True, max=True))


def frame_times(normalized, start=None, end=None):
    """Map normalised [0-1] times to actual frame numbers."""
    if start is None or end is None:
        s, e = timeline_range()
        start = start if start is not None else s
        end = end if end is not None else e
    span = end - start
    return [start + t * span for t in normalized]


# ── clear ──

def clear_keys(ctrls, attrs=None):
    """Cut keys and reset attrs on *ctrls* within the playback range."""
    if attrs is None:
        attrs = ['translateX', 'translateY', 'translateZ',
                 'rotateX', 'rotateY', 'rotateZ', 'Roll']
    start, end = timeline_range()
    for name in ctrls:
        node = resolver.resolve(name) or name
        if not cmds.objExists(node):
            continue
        for attr in attrs:
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue
            full = '{}.{}'.format(node, attr)
            cmds.cutKey(node, at=attr, time=(start, end))
            if not cmds.getAttr(full, lock=True) \
               and not cmds.connectionInfo(full, isDestination=True):
                try:
                    cmds.setAttr(full, 0)
                except Exception:
                    pass


# ── single-key helper ──

def _set_key(node, attr, t, v):
    """Set one keyframe, handling locked and connected attributes."""
    full = '{}.{}'.format(node, attr)
    locked = cmds.getAttr(full, lock=True)
    if locked:
        try:
            cmds.setKeyframe(node, at=attr, t=t)
        except Exception:
            pass
        return
    connected = cmds.connectionInfo(full, isDestination=True)
    try:
        if connected:
            cmds.setKeyframe(node, at=attr, t=t)
            cmds.keyframe(node, at=attr, e=True, t=(t, t), vc=float(v))
        else:
            cmds.setKeyframe(node, at=attr, t=t, v=float(v))
    except Exception as e:
        print('!! key failed {}.{} @ {}: {}'.format(node, attr, t, e))


# ── FKIK blend keying ──

def _key_fkik(layers):
    """Set and key FKIKBlend attributes required by each enabled layer.

    Keyed at start and end of the playback range so the blend holds
    for the entire cycle.  Also sets the attribute value immediately
    so the correct controls are visible during generation.
    """
    start, end = timeline_range()
    merged = {}
    for layer in layers:
        if not layer.enabled:
            continue
        merged.update(layer.fkik_state())
    for ctrl_name, value in merged.items():
        node = resolver.resolve(ctrl_name)
        if not node or not cmds.objExists(node):
            continue
        if not cmds.attributeQuery('FKIKBlend', node=node, exists=True):
            continue
        full = '{}.FKIKBlend'.format(node)
        try:
            cmds.setAttr(full, value)
            cmds.setKeyframe(node, at='FKIKBlend', t=start, v=float(value))
            cmds.setKeyframe(node, at='FKIKBlend', t=end, v=float(value))
        except Exception as e:
            print('!! FKIK key failed {}: {}'.format(full, e))


# ── batch keying ──

def _key_all(channels):
    """Set keyframes for every channel (no undo-chunk management)."""
    for ch in channels:
        node = resolver.resolve(ch.ctrl)
        if not node:
            continue
        if not cmds.attributeQuery(ch.attr, node=node, exists=True):
            continue
        values = ch.evaluate()
        times = frame_times(ch.normalized_times())
        for t, v in zip(times, values):
            _set_key(node, ch.attr, t, v)


def key_channels(channels):
    """Set keyframes for a list of Channel objects (with undo chunk)."""
    resolver.clear()
    cmds.undoInfo(openChunk=True, chunkName='AnimGenV2_key')
    try:
        _key_all(channels)
    finally:
        cmds.undoInfo(closeChunk=True)


# ── main entry point ──

def generate(layers, clear=True):
    """Full generation pass -- clear keys then key all enabled layers.

    Everything runs inside a single undo chunk so one Ctrl-Z reverts it all.
    """
    channels = []
    ctrls = set()
    for layer in layers:
        if not layer.enabled:
            continue
        channels.extend(layer.channels())
        ctrls.update(layer.controls())

    resolver.clear()
    cmds.undoInfo(openChunk=True, chunkName='AnimGenV2')
    try:
        saved = cmds.currentTime(q=True)
        _key_fkik(layers)
        if clear:
            clear_keys(list(ctrls))
        _key_all(channels)
        cmds.currentTime(saved)
    finally:
        cmds.undoInfo(closeChunk=True)
