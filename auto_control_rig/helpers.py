import maya.cmds as cmds


def setup_helper_joints(builder):
    """
    Drive elbow/knee helper joints from limb bend.

    The helper rotates opposite to its parent limb at a user-controllable
    factor, clamped to only the natural bending direction.

    Node network per helper:
        delta  = skin_joint.rZ - bind_rZ
        clamp  = only natural bend direction (positive for elbow, negative for knee)
        scaled = clamped * factor
        result = bind_helper_rZ - scaled   -->  helper.rZ
    """

    helper_defs = [
        # skin_slot_base, name_hint, positive_bend, limb_type
        ("elbow", "elbow_helper", True, "Arm"),
        ("knee", "knee_helper", False, "Leg"),
    ]

    sep_added = set()

    for s in ("l", "r"):
        S = s.upper()
        for slot_base, hint, pos_bend, limb in helper_defs:
            skin_jnt = builder.m.get(slot_base + "_" + s)
            if not skin_jnt or not cmds.objExists(skin_jnt):
                continue

            helper = _find_helper(skin_jnt, hint, s)
            if not helper:
                continue

            bind_parent_rz = cmds.getAttr(skin_jnt + ".rotateZ")
            bind_helper_rz = cmds.getAttr(helper + ".rotateZ")

            # Store bind pose so removal can restore it
            builder.bind_pose[helper] = {
                "t": list(cmds.getAttr(helper + ".t")[0]),
                "r": list(cmds.getAttr(helper + ".r")[0]),
                "s": list(cmds.getAttr(helper + ".s")[0]),
            }

            # Host the factor attribute on the limb's FKIK controller
            fkik_ctrl = "FKIK{}_{}".format(limb, S)
            if not cmds.objExists(fkik_ctrl):
                continue

            if fkik_ctrl not in sep_added:
                cmds.addAttr(fkik_ctrl, ln="__helpers__",
                             nn="--- Helpers ---", at="enum", en=" ", k=1)
                cmds.setAttr(fkik_ctrl + ".__helpers__", l=1)
                sep_added.add(fkik_ctrl)

            attr_name = "{}BendFactor".format(slot_base.title())
            cmds.addAttr(fkik_ctrl, ln=attr_name, at="float",
                         min=0, max=2, dv=0.5, k=1)

            tag = "{}_{}".format(slot_base, S)

            # 1) delta = skin_jnt.rZ - bind_rZ
            delta = cmds.createNode("plusMinusAverage",
                                    n="helperDelta_" + tag)
            cmds.setAttr(delta + ".operation", 2)
            cmds.connectAttr(skin_jnt + ".rotateZ", delta + ".input1D[0]")
            cmds.setAttr(delta + ".input1D[1]", bind_parent_rz)

            # 2) clamp to natural bend direction only
            clmp = cmds.createNode("clamp", n="helperClamp_" + tag)
            if pos_bend:
                # elbow: forward bend = positive delta
                cmds.setAttr(clmp + ".minR", 0)
                cmds.setAttr(clmp + ".maxR", 1e6)
            else:
                # knee: natural bend = negative delta
                cmds.setAttr(clmp + ".minR", -1e6)
                cmds.setAttr(clmp + ".maxR", 0)
            cmds.connectAttr(delta + ".output1D", clmp + ".inputR")

            # 3) scaled = clamped * factor
            mul = cmds.createNode("multiplyDivide",
                                  n="helperMul_" + tag)
            cmds.connectAttr(clmp + ".outputR", mul + ".input1X")
            cmds.connectAttr(fkik_ctrl + "." + attr_name, mul + ".input2X")

            # 4) result = bind_helper_rZ - scaled
            #    (subtracting a positive bend gives negative helper rotation
            #     and subtracting a negative bend gives positive helper rotation)
            result = cmds.createNode("plusMinusAverage",
                                     n="helperResult_" + tag)
            cmds.setAttr(result + ".operation", 2)
            cmds.setAttr(result + ".input1D[0]", bind_helper_rz)
            cmds.connectAttr(mul + ".outputX", result + ".input1D[1]")

            cmds.connectAttr(result + ".output1D", helper + ".rotateZ")

            builder.twist_nodes.extend([delta, clmp, mul, result])


def _find_helper(skin_jnt, hint, side):
    """Find a helper joint that is a child, sibling, or anywhere in scene."""
    suffix = "_" + side

    # Check children of the skin joint
    for child in (cmds.listRelatives(skin_jnt, c=1, type="joint") or []):
        if hint in child.lower():
            return child

    # Check siblings (parent's children)
    parents = cmds.listRelatives(skin_jnt, p=1, type="joint")
    if parents:
        for sib in (cmds.listRelatives(parents[0], c=1, type="joint") or []):
            if hint in sib.lower():
                return sib

    # Fallback: scene-wide search
    for j in cmds.ls(type="joint"):
        short = j.split("|")[-1].lower()
        if hint in short and short.endswith(suffix):
            return j

    return None
