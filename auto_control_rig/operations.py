import maya.cmds as cmds
import json

from .constants import RIG_GRP
from .utils import pos, color, side_color


def remove_control_rig():
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found.")
        return

    bind_pose = {}
    if cmds.attributeQuery("bind_pose", node=RIG_GRP, exists=True):
        try:
            bind_pose = json.loads(cmds.getAttr(RIG_GRP + ".bind_pose"))
        except Exception:
            pass

    if cmds.attributeQuery("skin_constraints", node=RIG_GRP, exists=True):
        try:
            names = json.loads(cmds.getAttr(RIG_GRP + ".skin_constraints"))
            for n in names:
                if cmds.objExists(n):
                    cmds.delete(n)
        except Exception:
            pass

    if cmds.attributeQuery("twist_nodes", node=RIG_GRP, exists=True):
        try:
            nodes = json.loads(cmds.getAttr(RIG_GRP + ".twist_nodes"))
            for n in nodes:
                if cmds.objExists(n):
                    cmds.delete(n)
        except Exception:
            pass

    cmds.delete(RIG_GRP)

    for jnt, xf in bind_pose.items():
        if not cmds.objExists(jnt):
            continue
        try:
            cmds.setAttr(jnt + ".t", *xf["t"])
            cmds.setAttr(jnt + ".r", *xf["r"])
            cmds.setAttr(jnt + ".s", *xf["s"])
        except Exception:
            pass

    print("// AutoControlRig removed — bind pose restored.")


def reset_to_bind_pose():
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found.")
        return

    # Collect controls under Ctrl_GRP + Main_M (which is above Ctrl_GRP).
    # Only include curve-shape transforms (controls), never joints.
    ctrl_grp = "Ctrl_GRP"
    all_transforms = []

    if cmds.objExists(ctrl_grp):
        descendants = cmds.listRelatives(ctrl_grp, ad=1, type="transform", f=1) or []
        all_transforms.extend(descendants)

    # Main_M lives above Ctrl_GRP — add it explicitly.
    if cmds.objExists("Main_M"):
        all_transforms.append("Main_M")

    # Sort by depth (shallowest first → top-down reset so parents
    # settle before children, avoiding transient double-offsets).
    all_transforms = list(dict.fromkeys(all_transforms))  # dedupe
    all_transforms.sort(key=lambda p: p.count("|"))

    for c in all_transforms:
        # Only reset nodes that have curve shapes (actual controls).
        # Skip joints, offset groups, constraint groups, etc.
        shapes = cmds.listRelatives(c, s=1, type="nurbsCurve") or []
        if not shapes:
            continue
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz"):
            try:
                if not cmds.getAttr(c + "." + attr, l=1):
                    cmds.setAttr(c + "." + attr, 0)
            except Exception:
                pass
        for attr in ("sx", "sy", "sz"):
            try:
                if not cmds.getAttr(c + "." + attr, l=1):
                    cmds.setAttr(c + "." + attr, 1)
            except Exception:
                pass
        ud = cmds.listAttr(c, ud=1, k=1) or []
        for attr in ud:
            try:
                dv = cmds.addAttr(c + "." + attr, q=1, dv=1)
                cmds.setAttr(c + "." + attr, dv)
            except Exception:
                pass

    # Force complete scene evaluation.  dgdirty alone is not enough —
    # foot-roll expressions only fire on a time change, so the heel /
    # ball / toetip pivot groups keep stale rotations.  The IK solver
    # then computes with the wrong handle position, leaving feet
    # displaced and stretchy joints un-settled.
    #
    # Bumping currentTime forces expressions + IK solvers + full DG
    # pull.  A second bump lets the IK solver converge after the
    # stretchy joint scales snap back to 1.
    cur = cmds.currentTime(q=True)
    cmds.currentTime(cur, e=True)
    cmds.currentTime(cur, e=True)

    cmds.select(cl=1)
    print("// All controls reset to bind pose.")


def create_foot_roll_locators(mapping):
    created = 0
    for s, S in [("l", "L"), ("r", "R")]:
        foot_jnt = mapping.get("foot_" + s, "")
        toe_jnt = mapping.get("toe_" + s, "")
        if not foot_jnt or not cmds.objExists(foot_jnt):
            continue
        fp = pos(foot_jnt)
        heel_n = "footRoll_heel_" + S
        if not cmds.objExists(heel_n):
            h = cmds.spaceLocator(n=heel_n)[0]
            cmds.xform(h, ws=1, t=[fp[0], 0, fp[2] - 5])
            color(h, side_color(S))
            created += 1
        toetip_n = "footRoll_toetip_" + S
        if not cmds.objExists(toetip_n):
            t = cmds.spaceLocator(n=toetip_n)[0]
            if toe_jnt and cmds.objExists(toe_jnt):
                tp = pos(toe_jnt)
                cmds.xform(t, ws=1, t=[tp[0], 0, tp[2] + 5])
            else:
                cmds.xform(t, ws=1, t=[fp[0], 0, fp[2] + 15])
            color(t, side_color(S))
            created += 1
    if created:
        print("// Created {} foot roll locator(s). Adjust positions as needed.".format(created))
    else:
        print("// Foot roll locators already exist or no foot joints mapped.")


# ── Channel lock/hide ─────────────────────────────────────────────

# Which channels each control *actually uses*.  Anything not listed
# gets locked + hidden.  Keyed by control name prefix/pattern.
# "t" = translateXYZ, "r" = rotateXYZ, "s" = scaleXYZ

_CHAN_MAP = {
    # Center body
    'Main_M':           'trs',
    'RootX_M':          'tr',
    'HipSwinger_M':     'r',
    'FKSpine_M':        'r',       # translate does NOT propagate (half_grp intermediary)
    'FKChest_M':        'tr',
    'FKNeck_M':         'tr',
    'FKHead_M':         'tr',
    # IK Spine
    'IKSpine_M':        'tr',
    'IKSpineMid_M':     'tr',
    'IKChest_M':        'tr',
    # FK Arms — parentConstraint passes both T+R
    'FKScapula_':       'tr',
    'FKShoulder_':      'tr',
    'FKElbow_':         'tr',
    'FKWrist_':         'tr',
    # FK Legs
    'FKHip_':           'tr',
    'FKKnee_':          'tr',
    'FKFoot_':          'tr',
    'FKToe_':           'tr',
    # IK Limbs
    'IKArm_':           'tr',
    'IKLeg_':           'tr',
    # Pole vectors
    'PoleArm_':         't',
    'PoleLeg_':         't',
    # FKIK switches — no transform channels, only custom attrs
    'FKIKSpine_M':      '',
    'FKIKLeg_':         '',
    'FKIKArm_':         '',
    # Fingers — parentConstraint passes T+R
    'Fingers_':         '',        # master finger ctrl — custom attrs only
    'FKFinger':         'tr',
    # Eyes
    'EyeAim_M':        't',
    'EyeAim_':         't',
    # Eyelids
    'FKEyelidUpper_':   'tr',
    'FKEyelidLower_':   'tr',
    # Ears
    'FKEar_':           'tr',
}

_T = ('tx', 'ty', 'tz')
_R = ('rx', 'ry', 'rz')
_S = ('sx', 'sy', 'sz')


def _used_channels(ctrl_name):
    """Return the set of channel short-names a control should keep open."""
    # Try exact match first, then prefix match (longest prefix wins)
    if ctrl_name in _CHAN_MAP:
        flags = _CHAN_MAP[ctrl_name]
    else:
        flags = None
        best_len = 0
        for pattern, f in _CHAN_MAP.items():
            if ctrl_name.startswith(pattern) and len(pattern) > best_len:
                flags = f
                best_len = len(pattern)
    if flags is None:
        return None  # unknown control — leave it alone
    used = set()
    if 't' in flags:
        used.update(_T)
    if 'r' in flags:
        used.update(_R)
    if 's' in flags:
        used.update(_S)
    return used


def lock_hide_channels():
    """Lock and hide unused transform channels on all rig controls."""
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found.")
        return

    ctrl_grp = "Ctrl_GRP"
    all_nodes = []
    if cmds.objExists(ctrl_grp):
        all_nodes = cmds.listRelatives(ctrl_grp, ad=True,
                                       type="transform", fullPath=True) or []
    if cmds.objExists("Main_M"):
        all_nodes.append("Main_M")

    all_channels = set(_T + _R + _S)
    count = 0
    for node in all_nodes:
        shapes = cmds.listRelatives(node, s=True, type="nurbsCurve") or []
        if not shapes:
            continue
        short = node.rsplit('|', 1)[-1]
        used = _used_channels(short)
        if used is None:
            continue
        to_lock = all_channels - used
        for ch in to_lock:
            try:
                cmds.setAttr('{}.{}'.format(node, ch), lock=True,
                             keyable=False, channelBox=False)
            except Exception:
                pass
        count += 1
    print("// Locked/hid unused channels on {} controls.".format(count))


def unlock_all_channels():
    """Unlock and show all transform channels on rig controls (undo lock_hide)."""
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found.")
        return

    ctrl_grp = "Ctrl_GRP"
    all_nodes = []
    if cmds.objExists(ctrl_grp):
        all_nodes = cmds.listRelatives(ctrl_grp, ad=True,
                                       type="transform", fullPath=True) or []
    if cmds.objExists("Main_M"):
        all_nodes.append("Main_M")

    all_channels = list(_T + _R + _S)
    count = 0
    for node in all_nodes:
        shapes = cmds.listRelatives(node, s=True, type="nurbsCurve") or []
        if not shapes:
            continue
        for ch in all_channels:
            try:
                cmds.setAttr('{}.{}'.format(node, ch), lock=False,
                             keyable=True)
            except Exception:
                pass
        count += 1
    print("// Unlocked all channels on {} controls.".format(count))


# ── Character Set ─────────────────────────────────────────────────

def _gather_controls():
    """Return a list of (short_name, node_path) for all rig controls."""
    ctrl_grp = "Ctrl_GRP"
    all_nodes = []
    if cmds.objExists(ctrl_grp):
        all_nodes = cmds.listRelatives(ctrl_grp, ad=True,
                                       type="transform", fullPath=True) or []
    if cmds.objExists("Main_M"):
        all_nodes.append("Main_M")
    result = []
    for node in all_nodes:
        shapes = cmds.listRelatives(node, s=True, type="nurbsCurve") or []
        if not shapes:
            continue
        short = node.rsplit('|', 1)[-1]
        result.append((short, node))
    return result


def create_character_set(name="AutoCtrlRig"):
    """Create a Maya Character Set from all rig controls.

    Only keyable, unlocked channels are included.
    Existing character set with the same name is replaced.
    """
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found. Build the control rig first.")
        return None

    # Remove existing character set
    if cmds.objExists(name):
        cmds.delete(name)

    controls = _gather_controls()
    if not controls:
        cmds.warning("No controls found.")
        return None

    # Build flat list of node.attr for all keyable channels
    members = []
    for short, node in controls:
        keyable = cmds.listAttr(node, keyable=True) or []
        for attr in keyable:
            full = '{}.{}'.format(node, attr)
            if cmds.getAttr(full, lock=True):
                continue
            members.append(full)

    if not members:
        cmds.warning("No keyable channels found on controls.")
        return None

    char_set = cmds.character(members, name=name)
    print("// Character Set '{}' created with {} channels from {} controls.".format(
        name, len(members), len(controls)))
    return char_set
