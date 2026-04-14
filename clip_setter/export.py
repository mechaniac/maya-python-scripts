"""Export logic -- Game Exporter clip application + direct FBX clip export.

Two export paths:
  1. apply_clips()    -- set animation clips directly on the Game Exporter node
  2. export_clips()   -- directly export each clip as a separate FBX
"""

import os

import maya.cmds as cmds
import maya.mel as mel


# ── Game Exporter node ────────────────────────────────────────────

def _get_exporter_node(preset_name='Anim Default'):
    """Return the gameFbxExporter node for a given preset name.

    The Game Exporter stores a separate node per preset.  By default
    we target *Anim Default* (the animation preset).  If no node with
    that presetName exists, one is created.
    """
    plugin = 'gameFbxExporter'
    if not cmds.pluginInfo(plugin, q=True, loaded=True):
        cmds.loadPlugin(plugin)

    nodes = cmds.ls(type='gameFbxExporter')
    for n in nodes:
        try:
            name = cmds.getAttr('{}.presetName'.format(n))
            if name == preset_name:
                return n
        except (ValueError, RuntimeError):
            continue

    # Not found — create a new node and tag it
    node = cmds.createNode('gameFbxExporter')
    cmds.setAttr('{}.presetName'.format(node), preset_name, type='string')
    cmds.setAttr('{}.exportTypeIndex'.format(node), 2)   # Animation
    return node


def apply_clips(layout):
    """Set animation clips directly on the Game Exporter node.

    *layout* is the list returned by ``clips.layout_clips()``.
    Existing clips on the node are replaced.
    """
    node = _get_exporter_node()

    # ── clear existing clip entries ──
    indices = cmds.getAttr('{}.animClips'.format(node),
                           multiIndices=True) or []
    for idx in reversed(indices):
        cmds.removeMultiInstance('{}.animClips[{}]'.format(node, idx),
                                b=True)

    # ── write new clips ──
    for i, clip in enumerate(layout):
        prefix = '{}.animClips[{}]'.format(node, i)
        cmds.setAttr('{}.animClipName'.format(prefix),
                     clip['name'], type='string')
        cmds.setAttr('{}.animClipStart'.format(prefix), clip['start'])
        cmds.setAttr('{}.animClipEnd'.format(prefix),   clip['end'])
        cmds.setAttr('{}.exportAnimClip'.format(prefix), True)

    # ── standard export settings for Source 2 ──
    settings = {
        'exportTypeIndex': 2,       # Animation only
        'exportSetIndex': 1,
        'modelFileMode': 1,
        'moveToOrigin': 0,
        'smoothingGroups': 1,
        'splitVertexNormals': 0,
        'tangentsBinormals': 1,
        'smoothMesh': 0,
        'selectionSets': 0,
        'triangulate': 0,
        'fileSplitType': 2,         # Split by clip
        'bakeAnimation': 1,
        'skinning': 1,
        'blendshapes': 1,
        'curveFilters': 0,
        'constraints': 0,
        'includeCameras': 0,
        'upAxis': 1,                # Y-up
        'embedMedia': 1,
        'includeChildren': 0,
        'inputConnections': 0,
    }
    for attr, val in settings.items():
        try:
            cmds.setAttr('{}.{}'.format(node, attr), val)
        except RuntimeError:
            pass  # attribute may not exist on older Maya versions

    try:
        cmds.setAttr('{}.fileVersion'.format(node),
                     'FBX201800', type='string')
    except RuntimeError:
        pass

    print('// Applied {} clips to Game Exporter node: {}'.format(
        len(layout), node))
    return node


# ── Direct FBX clip export ────────────────────────────────────────

def export_clips(layout, output_dir, selection_only=True):
    """Export each clip as a separate FBX file.

    *output_dir* is the folder where ``<clip_name>.fbx`` files are written.
    If *selection_only* is True, only selected nodes are exported (typical
    for exporting just the skeleton + mesh).

    Returns a list of exported file paths.
    """
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Ensure FBX plugin is loaded
    if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
        cmds.loadPlugin('fbxmaya')

    exported = []
    for clip in layout:
        filepath = os.path.join(output_dir, '{}.fbx'.format(clip['name']))

        # Configure FBX export settings
        mel.eval('FBXExportBakeComplexAnimation -v true')
        mel.eval('FBXExportBakeComplexStart -v {}'.format(int(clip['start'])))
        mel.eval('FBXExportBakeComplexEnd -v {}'.format(int(clip['end'])))
        mel.eval('FBXExportBakeComplexStep -v 1')
        mel.eval('FBXExportSkins -v true')
        mel.eval('FBXExportShapes -v true')
        mel.eval('FBXExportConstraints -v false')
        mel.eval('FBXExportCameras -v false')
        mel.eval('FBXExportLights -v false')
        mel.eval('FBXExportSmoothingGroups -v true')
        mel.eval('FBXExportTangents -v true')
        mel.eval('FBXExportUpAxis y')
        mel.eval('FBXExportFileVersion -v FBX201800')
        mel.eval('FBXExportInAscii -v false')

        export_cmd = 'FBXExport -f "{}" -s'.format(filepath.replace('\\', '/'))
        if not selection_only:
            export_cmd = 'FBXExport -f "{}"'.format(filepath.replace('\\', '/'))

        mel.eval(export_cmd)
        exported.append(filepath)
        print('// Exported: {} (frames {}-{})'.format(
            clip['name'], clip['start'], clip['end']))

    return exported


# ── Timeline setup ────────────────────────────────────────────────

def setup_timeline(layout):
    """Set the Maya timeline to cover the full clip layout range.

    First clip's start becomes the playback min, last clip's end
    becomes the playback max.
    """
    if not layout:
        return
    start = layout[0]['start']
    end = layout[-1]['end']
    cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
    cmds.currentTime(start)
    print('// Timeline set: {} - {} ({} clips)'.format(start, end, len(layout)))


# ── Bind pose separators ──────────────────────────────────────────

def _default_value(node, attr):
    """Return the bind/default value for a channel.

    Transform channels: 0 for translate/rotate, 1 for scale.
    Custom attrs: query the default value set at creation time.
    """
    if attr in ('sx', 'sy', 'sz', 'scaleX', 'scaleY', 'scaleZ'):
        return 1.0
    if attr in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz',
                'translateX', 'translateY', 'translateZ',
                'rotateX', 'rotateY', 'rotateZ'):
        return 0.0
    # Custom / user-defined attr — query default
    try:
        return cmds.addAttr('{}.{}'.format(node, attr), q=True, dv=True)
    except (RuntimeError, ValueError):
        return 0.0


def _separator_frames(layout, buffer=60):
    """Compute frames where bind-pose keys should be placed.

    Returns a sorted list of integer frames:
      - One bookend *before* the first clip  (start − buffer/2)
      - One bookend *after*  the last  clip  (end   + buffer/2)
      - Midpoint of every buffer gap between consecutive clips
    """
    frames = []
    if not layout:
        return frames

    half = int(round(buffer / 2.0))

    # bookend before first clip
    frames.append(layout[0]['start'] - half)

    # midpoints between consecutive clips
    for i in range(len(layout) - 1):
        gap_start = layout[i]['end']
        gap_end = layout[i + 1]['start']
        mid = int(round((gap_start + gap_end) / 2.0))
        frames.append(mid)

    # bookend after last clip
    frames.append(layout[-1]['end'] + half)

    return sorted(set(frames))


def _gather_charset_channels(character_set):
    """Return a list of (node, attr) tuples for all keyable channels.

    Uses nodesOnly query then gathers keyable/unlocked attrs per node.
    This is more reliable than querying plug names from the character set.
    """
    nodes = cmds.character(character_set, q=True, nodesOnly=True) or []
    # Deduplicate while preserving order
    seen = set()
    unique_nodes = []
    for n in nodes:
        short = n.rsplit('|', 1)[-1]
        if short not in seen:
            seen.add(short)
            unique_nodes.append(short)

    # Attrs that are keyable on transforms but irrelevant for animation
    _SKIP_ATTRS = {'visibility'}

    channels = []
    for node in unique_nodes:
        if not cmds.objExists(node):
            continue
        keyable = cmds.listAttr(node, keyable=True) or []
        for attr in keyable:
            if attr in _SKIP_ATTRS:
                continue
            full = '{}.{}'.format(node, attr)
            try:
                if cmds.getAttr(full, lock=True):
                    continue
            except (ValueError, RuntimeError):
                continue
            channels.append((node, attr))
    return channels


def key_bind_pose_separators(layout, character_set, buffer=60):
    """Key every channel in *character_set* to its default value at separator frames.

    Separator frames are placed at the midpoint of each buffer gap between
    clips, plus bookends before the first and after the last clip.
    Keys use stepped tangents to create hard walls between clips.

    *character_set* is the name of an existing Maya character set.
    *buffer* is the buffer frame count used in the clip layout.
    """
    if not cmds.objExists(character_set):
        cmds.warning('Character set "{}" not found.'.format(character_set))
        return 0

    if not cmds.objectType(character_set, isType='character'):
        cmds.warning('"{}" is not a character set.'.format(character_set))
        return 0

    sep_frames = _separator_frames(layout, buffer=buffer)
    if not sep_frames:
        cmds.warning('No clips in layout.')
        return 0

    channels = _gather_charset_channels(character_set)
    if not channels:
        cmds.warning('No keyable channels found in character set.')
        return 0

    # Disable autoKeyframe so Maya doesn't also key at the current time
    auto_key_was_on = cmds.autoKeyframe(q=True, state=True)
    cmds.autoKeyframe(state=False)
    current_time = cmds.currentTime(q=True)

    cmds.undoInfo(openChunk=True, chunkName='ClipSetter_BindSeparators')
    key_count = 0
    try:
        for frame in sep_frames:
            for node, attr in channels:
                val = _default_value(node, attr)
                try:
                    cmds.setKeyframe(node, at=attr, t=(frame,), v=val)
                    cmds.keyTangent(node, at=attr, t=(frame, frame),
                                    itt='stepnext', ott='step')
                    key_count += 1
                except Exception:
                    pass

        # Remove accidental keys at the current time (setKeyframe + v=
        # can create side-effect keys at the current frame)
        if current_time not in sep_frames:
            for node, attr in channels:
                try:
                    cmds.cutKey(node, at=attr,
                                t=(current_time, current_time), clear=True)
                except Exception:
                    pass
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto_key_was_on)

    print('// Keyed {} bind-pose separators at {} frames across {} channels.'.format(
        key_count, len(sep_frames), len(channels)))
    return key_count
