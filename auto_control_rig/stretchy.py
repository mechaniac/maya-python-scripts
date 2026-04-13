"""Stretchy IK limbs — distance-based joint scale.

Adds a *Stretchy* (0-1 blend) attribute to IK limb controls.

Drives **scaleX** on start and mid IK driver joints (the standard
production approach — same as mGear/AdvancedSkeleton).

The rpIK solver creates an implicit DG cycle (it reads joint.worldMatrix
and writes joint.rotate).  Maya resolves this by evaluating cycled nodes
with their *default* output first.  A ``blendTwoAttr`` defaults to 0,
which would set scaleX = 0 and collapse the chain.

To make the cycle resolution safe, the blend is restructured as::

    final = Stretchy × (clampedRatio - 1) + 1

The ``+ 1`` at the end is a static ``plusMinusAverage`` (sum) whose
second input is the constant **1.0**, so even before the first
evaluation the scaleX is ≥ 1.0 — never zero.

Node network (no expressions, uses ``plusMinusAverage``):

    locator (under chain parent)  ──┐
                                     ├─ distanceBetween
    IK control locator            ──┘
         │
    globalScale compensate  →  ratio  →  clamp (≥ 1)
         │
    PMA subtract 1  →  × Stretchy  →  PMA + 1  →  scaleX on joints
"""

import maya.cmds as cmds
import math

from .utils import pos


def _dist(a, b):
    return math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))


def setup_stretchy_ik(ctrl, start_jnt, mid_jnt, end_jnt, label, builder):
    """Wire stretchy IK on an existing limb.

    Parameters
    ----------
    ctrl : str
        IK control transform (e.g. ``IKArm_L``).
    start_jnt, mid_jnt, end_jnt : str
        IK driver joints (shoulder/elbow/wrist or hip/knee/foot).
    label : str
        Unique suffix for node names (e.g. ``Arm_L``).
    builder : AutoControlRigBuilder
        Rig builder instance (misc_grp, main).
    """

    rest_len = _dist(pos(start_jnt), pos(mid_jnt)) + \
               _dist(pos(mid_jnt), pos(end_jnt))

    # ── Stretchy attribute on the IK control ──
    cmds.addAttr(ctrl, ln="__stretchy__", nn="─── Stretch ───",
                 at="enum", en=" ", k=True)
    cmds.setAttr(ctrl + ".__stretchy__", lock=True)
    cmds.addAttr(ctrl, ln="Stretchy", at="float", min=0, max=1, dv=1, k=True)

    # ── Stable start-point locator ──
    # Under start_jnt's *parent* (scapula for arms, root for legs)
    # so it follows the chain origin without depending on scaled joints.
    start_loc = cmds.spaceLocator(n="stretchStart_" + label)[0]
    cmds.xform(start_loc, ws=1, t=pos(start_jnt))
    start_par = cmds.listRelatives(start_jnt, p=True)
    if start_par:
        cmds.parent(start_loc, start_par[0])
    else:
        cmds.parent(start_loc, builder.misc_grp)
    cmds.setAttr(start_loc + ".v", 0)

    # End-point locator under misc_grp, point-constrained to IK control
    end_loc = cmds.spaceLocator(n="stretchEnd_" + label)[0]
    cmds.parent(end_loc, builder.misc_grp)
    cmds.pointConstraint(ctrl, end_loc)
    cmds.setAttr(end_loc + ".v", 0)

    # ── Distance ──
    dist = cmds.createNode("distanceBetween", n="stretchDist_" + label)
    cmds.connectAttr(start_loc + ".worldMatrix[0]", dist + ".inMatrix1")
    cmds.connectAttr(end_loc + ".worldMatrix[0]", dist + ".inMatrix2")

    # ── Global scale compensation ──
    main = getattr(builder, "main", "Main_M")
    gs_div = cmds.createNode("multiplyDivide", n="stretchGSDiv_" + label)
    cmds.setAttr(gs_div + ".operation", 2)  # divide
    cmds.connectAttr(dist + ".distance", gs_div + ".input1X")
    cmds.connectAttr(main + ".scaleX", gs_div + ".input2X")

    # ── Ratio: current / rest ──
    ratio = cmds.createNode("multiplyDivide", n="stretchRatio_" + label)
    cmds.setAttr(ratio + ".operation", 2)  # divide
    cmds.connectAttr(gs_div + ".outputX", ratio + ".input1X")
    cmds.setAttr(ratio + ".input2X", rest_len)

    # ── Clamp: stretch only, never squash (ratio ≥ 1) ──
    clamp = cmds.createNode("clamp", n="stretchClamp_" + label)
    cmds.setAttr(clamp + ".minR", 1.0)
    cmds.setAttr(clamp + ".maxR", 50.0)
    cmds.connectAttr(ratio + ".outputX", clamp + ".inputR")

    # ── Cycle-safe blend: Stretchy × (ratio - 1) + 1 ──
    #
    # Step 1: offset = clampedRatio - 1  (0 at rest)
    sub = cmds.createNode("plusMinusAverage", n="stretchSub_" + label)
    cmds.setAttr(sub + ".operation", 2)  # subtract
    cmds.connectAttr(clamp + ".outputR", sub + ".input1D[0]")
    cmds.setAttr(sub + ".input1D[1]", 1.0)

    # Step 2: scaledOffset = offset × Stretchy  (0 when off)
    mul = cmds.createNode("multiplyDivide", n="stretchMul_" + label)
    cmds.connectAttr(sub + ".output1D", mul + ".input1X")
    cmds.connectAttr(ctrl + ".Stretchy", mul + ".input2X")

    # Step 3: final = scaledOffset + 1  (always ≥ 1, even during cycle init)
    add = cmds.createNode("plusMinusAverage", n="stretchAdd_" + label)
    cmds.setAttr(add + ".operation", 1)  # sum
    cmds.connectAttr(mul + ".outputX", add + ".input1D[0]")
    cmds.setAttr(add + ".input1D[1]", 1.0)

    # ── Drive scaleX on upper and lower joints ──
    cmds.connectAttr(add + ".output1D", start_jnt + ".scaleX")
    cmds.connectAttr(add + ".output1D", mid_jnt + ".scaleX")
