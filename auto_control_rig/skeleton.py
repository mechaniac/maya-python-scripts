import maya.cmds as cmds
import math

from .utils import pos
from .constants import FINGER_NAMES


def make_driver_joint(skin_jnt, name, parent):
    cmds.select(cl=1)
    dj = cmds.joint(n=name)
    cmds.xform(dj, ws=1, t=pos(skin_jnt))
    cmds.parent(dj, parent)
    return dj


def orient_chain(joints):
    if len(joints) < 2:
        return
    for j in joints[:-1]:
        cmds.joint(j, e=1, oj="xyz", sao="yup", zso=1)
    po = cmds.getAttr(joints[-2] + ".jointOrient")[0]
    cmds.setAttr(joints[-1] + ".jointOrient", *po)


def orient_ik_chain(start, mid, end, bend_dir):
    orient_chain([start, mid, end])
    end_pos = pos(end)
    cmds.xform(mid, r=1, ro=(0, 0, 2), os=1)
    a, b, c = pos(start), pos(mid), pos(end)
    mp = [(a[i] + c[i]) * 0.5 for i in range(3)]
    v = [b[i] - mp[i] for i in range(3)]
    dot = sum(v[i] * bend_dir[i] for i in range(3))
    if dot < 0:
        cmds.xform(mid, r=1, ro=(0, 0, -4), os=1)
    cmds.joint(mid, e=1, spa=1)
    cmds.xform(end, ws=1, t=end_pos)


def _copy_skin_orient(builder, dj, slot):
    """Copy the world rotation of the skin joint onto the driver joint
    and bake it into jointOrient."""
    skin = builder.m.get(slot, "")
    if skin and cmds.objExists(skin):
        cmds.xform(dj, ws=1, ro=cmds.xform(skin, q=1, ws=1, ro=1))
        cmds.makeIdentity(dj, a=1, r=1)


def set_preferred_angle(start, mid, end, bend_dir):
    """Set IK preferred angle by finding which local-axis rotation
    displaces *end* toward *bend_dir*.  Works with any joint orient."""
    end_rest = pos(end)
    saved_ro = cmds.getAttr(mid + ".rotate")[0]

    best_axis = 0
    best_score = 0
    for ax in range(3):
        ro = [0, 0, 0]
        ro[ax] = 5
        cmds.xform(mid, r=1, ro=ro, os=1)
        end_p = pos(end)
        cmds.setAttr(mid + ".rotate", *saved_ro)

        delta = [end_p[i] - end_rest[i] for i in range(3)]
        score = sum(delta[i] * bend_dir[i] for i in range(3))
        if abs(score) > abs(best_score):
            best_score = score
            best_axis = ax

    ro = [0, 0, 0]
    ro[best_axis] = 2 if best_score > 0 else -2
    cmds.xform(mid, r=1, ro=ro, os=1)
    cmds.joint(mid, e=1, spa=1)
    cmds.xform(end, ws=1, t=end_rest)


def _drv(builder, slot, parent):
    skin = builder.m.get(slot, "")
    if not skin or not cmds.objExists(skin):
        return
    dj = make_driver_joint(skin, "drv_" + slot, parent)
    _copy_skin_orient(builder, dj, slot)
    builder.dj[slot] = dj


def _driver_arm(builder, s, S):
    chest = builder.dj.get("chest", builder.drv_grp)
    _drv(builder, "scapula_" + s, chest)
    par = builder.dj.get("scapula_" + s, chest)
    for sl in ["shoulder_" + s, "elbow_" + s, "wrist_" + s]:
        _drv(builder, sl, par)
        par = builder.dj.get(sl, par)


def _driver_leg(builder, s, S):
    root = builder.dj.get("root", builder.drv_grp)
    for sl in ["hip_" + s, "knee_" + s, "foot_" + s]:
        _drv(builder, sl, root)
        root = builder.dj.get(sl, root)

    foot_drv = builder.dj.get("foot_" + s, root)
    _drv(builder, "toe_" + s, foot_drv)


# ---------------------------------------------------------------------------
# IK driver chains (separate from FK for clean FK/IK separation)
# ---------------------------------------------------------------------------
def _ik_drv(builder, slot, parent):
    """Create an IK driver joint (parallel chain for IK solving)."""
    skin = builder.m.get(slot, "")
    if not skin or not cmds.objExists(skin):
        return
    dj = make_driver_joint(skin, "ik_drv_" + slot, parent)
    _copy_skin_orient(builder, dj, slot)
    builder.ik_dj[slot] = dj


def build_ik_driver_arm(builder, s):
    """Build IK driver arm chain, parented under FK scapula."""
    scap = builder.dj.get("scapula_" + s, builder.drv_grp)
    par = scap
    for sl in ["shoulder_" + s, "elbow_" + s, "wrist_" + s]:
        _ik_drv(builder, sl, par)
        par = builder.ik_dj.get(sl, par)
    arm = [builder.ik_dj[k] for k in
           ["shoulder_" + s, "elbow_" + s, "wrist_" + s]
           if k in builder.ik_dj]
    if len(arm) == 3:
        set_preferred_angle(arm[0], arm[1], arm[2], bend_dir=(0, 0, -1))


def build_ik_driver_leg(builder, s):
    """Build IK driver leg chain, parented under FK root."""
    root = builder.dj.get("root", builder.drv_grp)
    par = root
    for sl in ["hip_" + s, "knee_" + s, "foot_" + s]:
        _ik_drv(builder, sl, par)
        par = builder.ik_dj.get(sl, par)
    leg = [builder.ik_dj[k] for k in
           ["hip_" + s, "knee_" + s, "foot_" + s]
           if k in builder.ik_dj]
    if len(leg) == 3:
        set_preferred_angle(leg[0], leg[1], leg[2], bend_dir=(0, 0, 1))
    foot_ik = builder.ik_dj.get("foot_" + s, par)
    _ik_drv(builder, "toe_" + s, foot_ik)


def build_ik_driver_spine(builder):
    """Build IK driver spine chain, parented under FK root."""
    root = builder.dj.get("root", builder.drv_grp)
    par = root
    for sl in ["spine", "spine_1", "chest"]:
        _ik_drv(builder, sl, par)
        par = builder.ik_dj.get(sl, par)


def build_driver_skeleton(builder):
    _drv(builder, "root", builder.drv_grp)

    spine = ["spine", "spine_1", "chest", "neck", "head"]
    par = builder.dj.get("root", builder.drv_grp)
    for sl in spine:
        _drv(builder, sl, par)
        par = builder.dj.get(sl, par)

    for s in ("l", "r"):
        S = s.upper()
        _driver_arm(builder, s, S)
        _driver_leg(builder, s, S)

    # Eyes, eyelids, ears — parented under head driver
    head = builder.dj.get("head", builder.drv_grp)
    for sl in ("eye_l", "eye_r",
               "eyelid_upper_l", "eyelid_lower_l",
               "eyelid_upper_r", "eyelid_lower_r",
               "ear_l", "ear_r"):
        _drv(builder, sl, head)


# ---------------------------------------------------------------------------
# Finger driver chains (auto-discovered from wrist descendants)
# ---------------------------------------------------------------------------
def build_finger_drivers(builder, side):
    """Auto-discover finger joints under wrist and create driver chains."""
    s = side.lower()
    wrist_skin = builder.m.get("wrist_" + s, "")
    if not wrist_skin or not cmds.objExists(wrist_skin):
        return
    wrist_drv = builder.dj.get("wrist_" + s)
    if not wrist_drv:
        return

    fingers = _discover_fingers(wrist_skin)
    if not hasattr(builder, "finger_chains"):
        builder.finger_chains = {}
    builder.finger_chains[side] = {}

    for fname, skin_chain in fingers.items():
        drv_chain = []
        par = wrist_drv
        for idx, jnt in enumerate(skin_chain):
            slot = "finger_{}_{}_{}".format(fname, idx, s)
            dj = make_driver_joint(jnt, "drv_" + slot, par)
            cmds.xform(dj, ws=1, ro=cmds.xform(jnt, q=1, ws=1, ro=1))
            cmds.makeIdentity(dj, a=1, r=1)
            builder.dj[slot] = dj
            builder.m[slot] = jnt
            drv_chain.append(slot)
            par = dj
        builder.finger_chains[side][fname] = drv_chain


def _discover_fingers(wrist_skin):
    """Find finger chains as branches under the wrist joint."""
    children = cmds.listRelatives(wrist_skin, c=True, type="joint") or []
    kw_map = {
        "thumb": ["thumb"],
        "index": ["index"],
        "middle": ["middle", "mid"],
        "ring": ["ring"],
        "pinky": ["pinky", "little"],
    }
    fingers = {}
    for child in children:
        chain = _trace_chain(child)
        if len(chain) < 2:
            continue
        name = None
        for fn in FINGER_NAMES:
            for jnt in chain:
                if any(kw in jnt.lower() for kw in kw_map.get(fn, [])):
                    name = fn
                    break
            if name:
                break
        if name and name not in fingers:
            fingers[name] = chain
    return fingers


def _trace_chain(root):
    """Follow first-child joints to build a linear chain."""
    chain = [root]
    cur = root
    while True:
        ch = cmds.listRelatives(cur, c=True, type="joint") or []
        if not ch:
            break
        chain.append(ch[0])
        cur = ch[0]
    return chain
