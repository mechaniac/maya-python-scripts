import maya.cmds as cmds
import math

from .utils import pos


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


def _drv(builder, slot, parent, copy_orient=False):
    skin = builder.m.get(slot, "")
    if not skin or not cmds.objExists(skin):
        return
    dj = make_driver_joint(skin, "drv_" + slot, parent)
    if copy_orient:
        cmds.xform(dj, ws=1, ro=cmds.xform(skin, q=1, ws=1, ro=1))
        cmds.makeIdentity(dj, a=1, r=1)
    builder.dj[slot] = dj


def _driver_arm(builder, s, S):
    chest = builder.dj.get("chest", builder.drv_grp)
    _drv(builder, "scapula_" + s, chest)
    par = builder.dj.get("scapula_" + s, chest)
    for sl in ["shoulder_" + s, "elbow_" + s, "wrist_" + s]:
        _drv(builder, sl, par)
        par = builder.dj.get(sl, par)

    arm = [builder.dj[k] for k in ["shoulder_" + s, "elbow_" + s, "wrist_" + s] if k in builder.dj]
    if len(arm) == 3:
        orient_ik_chain(arm[0], arm[1], arm[2], bend_dir=(0, 0, -1))

    sc = builder.dj.get("scapula_" + s)
    if sc and arm:
        cmds.joint(sc, e=1, oj="xyz", sao="yup", zso=1)


def _driver_leg(builder, s, S):
    root = builder.dj.get("root", builder.drv_grp)
    for sl in ["hip_" + s, "knee_" + s, "foot_" + s]:
        _drv(builder, sl, root)
        root = builder.dj.get(sl, root)

    leg = [builder.dj[k] for k in ["hip_" + s, "knee_" + s, "foot_" + s] if k in builder.dj]
    if len(leg) == 3:
        orient_ik_chain(leg[0], leg[1], leg[2], bend_dir=(0, 0, 1))

    foot_drv = builder.dj.get("foot_" + s, root)
    _drv(builder, "toe_" + s, foot_drv)
    toe = builder.dj.get("toe_" + s)
    if toe and len(leg) == 3:
        fo = cmds.getAttr(leg[2] + ".jointOrient")[0]
        cmds.setAttr(toe + ".jointOrient", *fo)


def build_driver_skeleton(builder):
    _drv(builder, "root", builder.drv_grp, copy_orient=True)

    spine = ["spine", "chest", "neck", "head"]
    par = builder.dj.get("root", builder.drv_grp)
    for sl in spine:
        _drv(builder, sl, par)
        par = builder.dj.get(sl, par)
    chain = [builder.dj[s] for s in spine if s in builder.dj]
    if chain:
        orient_chain(chain)

    for s in ("l", "r"):
        S = s.upper()
        _driver_arm(builder, s, S)
        _driver_leg(builder, s, S)
