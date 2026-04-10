import maya.cmds as cmds
import math

from .constants import COL_L, COL_R, COL_M


def pos(jnt):
    return cmds.xform(jnt, q=1, ws=1, t=1)


def color(ctrl, idx):
    for s in (cmds.listRelatives(ctrl, s=1, f=1) or []):
        cmds.setAttr(s + ".overrideEnabled", 1)
        cmds.setAttr(s + ".overrideColor", idx)


def side_color(side):
    return COL_L if side == "L" else (COL_R if side == "R" else COL_M)


def circle(name, r=1, n=(0, 1, 0)):
    return cmds.circle(n=name, r=r, nr=n, ch=0)[0]


def box(name, sz=1):
    h = sz
    s = sz * 0.5
    pts = [(-s, 0, -s), (-s, 0, s), (s, 0, s), (s, 0, -s), (-s, 0, -s),
           (-s, h, -s), (-s, h, s), (s, h, s), (s, h, -s), (-s, h, -s)]
    c = cmds.curve(n=name, d=1, p=pts)
    for a, b in [(1, 6), (2, 7), (3, 8)]:
        ex = cmds.curve(d=1, p=[pts[a], pts[b]])
        cmds.parent(cmds.listRelatives(ex, s=1)[0], c, s=1, r=1)
        cmds.delete(ex)
    return c


def diamond(name, sz=1):
    s = sz
    return cmds.curve(n=name, d=1, p=[(0, s, 0), (s, 0, 0), (0, -s, 0), (-s, 0, 0),
                                       (0, s, 0), (0, 0, s), (0, -s, 0), (0, 0, -s), (0, s, 0)])


def snap(node, jnt):
    cmds.xform(node, ws=1, t=pos(jnt))
    cmds.xform(node, ws=1, ro=cmds.xform(jnt, q=1, ws=1, ro=1))


def offset(ctrl):
    grp = cmds.group(em=1, n=ctrl + "_offset")
    cmds.xform(grp, ws=1, t=cmds.xform(ctrl, q=1, ws=1, t=1))
    cmds.xform(grp, ws=1, ro=cmds.xform(ctrl, q=1, ws=1, ro=1))
    cmds.parent(ctrl, grp)
    cmds.xform(ctrl, t=(0, 0, 0), ro=(0, 0, 0))
    return grp


def shift_cvs(ctrl, dx=0, dy=0, dz=0):
    for shp in (cmds.listRelatives(ctrl, s=1, f=1) or []):
        ncv = cmds.getAttr(shp + ".cp", size=1)
        for i in range(ncv):
            p = cmds.getAttr("{}.cp[{}]".format(shp, i))[0]
            cmds.setAttr("{}.cp[{}]".format(shp, i), p[0] + dx, p[1] + dy, p[2] + dz)


def sdk(driven_attr, driver_attr, keys):
    for dv, v in keys:
        cmds.setDrivenKeyframe(driven_attr, cd=driver_attr, dv=dv, v=v)
    curves = cmds.listConnections(driven_attr, type="animCurveUU", s=1, d=0) or []
    for crv in curves:
        cmds.keyTangent(crv, itt="linear", ott="linear")


def pole_pos(j_mid, dist, direction):
    p = pos(j_mid)
    ln = math.sqrt(sum(d * d for d in direction)) or 1
    return [p[i] + (direction[i] / ln) * dist for i in range(3)]
