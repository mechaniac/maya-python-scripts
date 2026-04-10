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
    ctrl_grp = "Ctrl_GRP"
    if not cmds.objExists(ctrl_grp):
        cmds.warning("Ctrl_GRP not found.")
        return
    ctrls = cmds.listRelatives(ctrl_grp, ad=1, type="transform", f=1) or []
    for c in ctrls:
        shapes = cmds.listRelatives(c, s=1) or []
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
