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
