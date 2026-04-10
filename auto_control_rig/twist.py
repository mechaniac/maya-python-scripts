import maya.cmds as cmds


def setup_twist_joints(builder):
    twist_segs = [
        ("shoulder", "elbow", "UpperArm", "Arm"),
        ("elbow", "wrist", "LowerArm", "Arm"),
        ("hip", "knee", "UpperLeg", "Leg"),
        ("knee", "foot", "LowerLeg", "Leg"),
    ]

    sep_added = set()
    for s in ("l", "r"):
        S = s.upper()
        for parent_base, child_base, label, limb in twist_segs:
            parent_slot = parent_base + "_" + s
            child_slot = child_base + "_" + s
            skin_par = builder.m.get(parent_slot, "")
            skin_chi = builder.m.get(child_slot, "")
            if not skin_par or not skin_chi:
                continue
            if not cmds.objExists(skin_par) or not cmds.objExists(skin_chi):
                continue

            children = cmds.listRelatives(skin_par, c=1, type="joint") or []
            twist_jnts = sorted([c for c in children if "twist" in c.lower()])
            if not twist_jnts:
                continue

            # Put twist attrs on the limb's FKIK controller, fall back to RootX_M
            fkik_ctrl = "FKIK{}_{}".format(limb, S)
            if cmds.objExists(fkik_ctrl):
                host = fkik_ctrl
            else:
                host = "RootX_M"
                if not cmds.objExists(host):
                    continue

            if host not in sep_added:
                cmds.addAttr(host, ln="__twist__", nn="--- Twist ---",
                             at="enum", en=" ", k=1)
                cmds.setAttr(host + ".__twist__", l=1)
                sep_added.add(host)

            is_upper = (parent_base in ("shoulder", "hip"))

            mm = cmds.createNode("multMatrix",
                                 n="twistMM_{}_{}_{}".format(parent_base, label, S))
            cmds.connectAttr(skin_chi + ".worldMatrix[0]", mm + ".matrixIn[0]")
            cmds.connectAttr(skin_par + ".worldInverseMatrix[0]", mm + ".matrixIn[1]")

            dm = cmds.createNode("decomposeMatrix",
                                 n="twistDM_{}_{}_{}".format(parent_base, label, S))
            cmds.connectAttr(mm + ".matrixSum", dm + ".inputMatrix")
            builder.twist_nodes.extend([mm, dm])

            rest_rx = cmds.getAttr(dm + ".outputRotateX")

            ref = cmds.createNode("plusMinusAverage",
                                  n="twistRef_{}_{}_{}".format(parent_base, label, S))
            cmds.setAttr(ref + ".operation", 2)
            cmds.connectAttr(dm + ".outputRotateX", ref + ".input1D[0]")
            cmds.setAttr(ref + ".input1D[1]", rest_rx)
            builder.twist_nodes.append(ref)

            n = len(twist_jnts)
            for i, tj in enumerate(twist_jnts):
                frac = (n - i) / float(n + 1)

                bind_rx = cmds.getAttr(tj + ".rx")
                builder.bind_pose[tj] = {
                    "t": list(cmds.getAttr(tj + ".t")[0]),
                    "r": list(cmds.getAttr(tj + ".r")[0]),
                    "s": list(cmds.getAttr(tj + ".s")[0]),
                }

                attr_name = "twist{}_{}{}".format(label, S, i)
                cmds.addAttr(host, ln=attr_name, at="float",
                             min=0, max=1, dv=frac, k=1)

                md = cmds.createNode("multiplyDivide",
                                     n="twistMul_{}_{}{}".format(label, S, i))
                cmds.connectAttr(ref + ".output1D", md + ".input1X")

                if is_upper:
                    pma = cmds.createNode("plusMinusAverage",
                                          n="twistSub_{}_{}{}".format(label, S, i))
                    cmds.setAttr(pma + ".operation", 2)
                    cmds.connectAttr(host + "." + attr_name, pma + ".input1D[0]")
                    cmds.setAttr(pma + ".input1D[1]", 1.0)
                    cmds.connectAttr(pma + ".output1D", md + ".input2X")
                    builder.twist_nodes.append(pma)
                else:
                    cmds.connectAttr(host + "." + attr_name, md + ".input2X")

                add = cmds.createNode("plusMinusAverage",
                                      n="twistAdd_{}_{}{}".format(label, S, i))
                cmds.setAttr(add + ".input1D[0]", bind_rx)
                cmds.connectAttr(md + ".outputX", add + ".input1D[1]")
                cmds.connectAttr(add + ".output1D", tj + ".rx")

                builder.twist_nodes.extend([md, add])
