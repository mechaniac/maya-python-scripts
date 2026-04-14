"""Keyframe engine -- batch keying with undo-chunk wrapper."""

import random

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
    """Cut keys and reset attrs on *ctrls*, covering the extended range."""
    if attrs is None:
        attrs = ['translateX', 'translateY', 'translateZ',
                 'rotateX', 'rotateY', 'rotateZ', 'Roll']
    start, end = timeline_range()
    span = end - start
    # clear generously: half the span beyond each side covers any offset
    clear_start = start - span
    clear_end = end + span
    for name in ctrls:
        node = resolver.resolve(name) or name
        if not cmds.objExists(node):
            continue
        for attr in attrs:
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue
            full = '{}.{}'.format(node, attr)
            cmds.cutKey(node, at=attr, time=(clear_start, clear_end))
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
    """Set keyframes for every channel (no undo-chunk management).

    Each channel gets one extra key before and after the timeline range
    to fake a looping curve.  If *frame_offset* is set, all keys shift.
    """
    keyed = []   # (node, attr) pairs for post-processing
    for ch in channels:
        node = resolver.resolve(ch.ctrl)
        if not node:
            continue
        if not cmds.attributeQuery(ch.attr, node=node, exists=True):
            continue
        values = ch.extended_evaluate()
        times = frame_times(ch.extended_normalized_times())
        for t, v in zip(times, values):
            _set_key(node, ch.attr, t + ch.frame_offset, v)
        keyed.append((node, ch.attr))
    return keyed


def _finalize_curves(keyed):
    """Set spline tangents and cycle post-infinity on all keyed curves."""
    start, end = timeline_range()
    for node, attr in keyed:
        try:
            cmds.keyTangent(node, at=attr, itt='spline', ott='spline')
            cmds.setInfinity(node, at=attr, poi='cycle', pri='cycle')
        except Exception:
            pass


def key_channels(channels):
    """Set keyframes for a list of Channel objects (with undo chunk)."""
    resolver.clear()
    cmds.undoInfo(openChunk=True, chunkName='AnimGenV2_key')
    try:
        keyed = _key_all(channels)
        _finalize_curves(keyed)
    finally:
        cmds.undoInfo(closeChunk=True)


# ── variation ──

def _apply_variation(channels, variation_pct):
    """Randomly perturb channel amplitudes / values by ±variation_pct %.

    Returns a new list of channels with modified copies; originals are
    not mutated.
    """
    if variation_pct <= 0:
        return channels
    from ..core.channel import Channel as _Ch
    from dataclasses import replace as _replace
    factor = variation_pct / 100.0
    out = []
    for ch in channels:
        mult = 1.0 + random.uniform(-factor, factor)
        if ch.values is not None:
            new_vals = [v * mult for v in ch.values]
            out.append(_replace(ch, values=new_vals))
        else:
            out.append(_replace(ch, amplitude=ch.amplitude * mult))
    return out


# ── main entry point ──

def generate(layers, clear=True, variation=0):
    """Full generation pass -- clear keys then key all enabled layers.

    *variation*: percentage (0-100) of random amplitude perturbation.
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
        if variation > 0:
            channels = _apply_variation(channels, variation)
        keyed = _key_all(channels)
        _finalize_curves(keyed)
        cmds.currentTime(saved)
    finally:
        cmds.undoInfo(closeChunk=True)
