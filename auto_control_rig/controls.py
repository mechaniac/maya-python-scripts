import maya.cmds as cmds
import math

from .constants import SLOT_TO_CTRL, COL_M, COL_IK, COL_R
from .utils import pos, color, side_color, circle, box, cross, diamond, snap, offset, shift_cvs, pole_pos


# ---------------------------------------------------------------------------
# Root / Hip
# ---------------------------------------------------------------------------
def build_root(builder):
    dj = builder.dj.get("root")
    if not dj:
        return
    c = circle("RootX_M", r=builder.sz * 8)
    snap(c, dj)
    color(c, COL_M)
    cmds.xform(c, ws=1, ro=(0, 0, 0))
    o = offset(c)
    cmds.parent(o, builder.ctrl_grp)
    cmds.pointConstraint(c, dj, mo=1)

    h = circle("HipSwinger_M", r=builder.sz * 5)
    snap(h, dj)
    color(h, COL_M)
    cmds.xform(h, ws=1, ro=(0, 0, 0))
    ho = offset(h)
    cmds.parent(ho, c)
    cmds.orientConstraint(h, dj, mo=1)


# ---------------------------------------------------------------------------
# FK Spine
# ---------------------------------------------------------------------------
def build_fk_spine(builder):
    ik_spine = builder.opts.get("create_ik_spine", True)
    ik_spine_slots = {"spine", "spine_1", "chest"} if ik_spine else set()
    par = "RootX_M" if cmds.objExists("RootX_M") else builder.ctrl_grp
    for slot in ["spine", "spine_1", "chest", "neck", "head"]:
        dj = builder.dj.get(slot)
        if not dj:
            continue
        c = circle(SLOT_TO_CTRL[slot], r=builder.sz * 8, n=(1, 0, 0))
        snap(c, dj)
        color(c, COL_M)
        o = offset(c)
        cmds.parent(o, par if cmds.objExists(par) else builder.ctrl_grp)
        if slot not in ik_spine_slots:
            cmds.parentConstraint(c, dj, mo=1)
        par = c


# ---------------------------------------------------------------------------
# IK Spline Spine
# ---------------------------------------------------------------------------
def build_ik_spine(builder):
    spine_dj = builder.dj.get("spine")
    chest_dj = builder.dj.get("chest")
    mid_dj = builder.dj.get("spine_1")
    if not spine_dj or not chest_dj or not mid_dj:
        return

    ikh, eff = cmds.ikHandle(
        n="ikh_Spine_M", sj=spine_dj, ee=chest_dj,
        sol="ikSplineSolver", ccv=True, scv=False, pcv=False,
    )
    # The auto-created curve is the third item in listConnections
    crv = cmds.ikHandle(ikh, q=1, c=1)
    crv = cmds.rename(crv, "ikSplineCrv_Spine")
    cmds.parent(ikh, builder.ik_grp)
    cmds.parent(crv, builder.misc_grp)

    # Cluster each CV and parent to the matching FK control
    num_cvs = cmds.getAttr(crv + ".cp", s=1)
    ctrl_list = ["HipSwinger_M", "FKSpine1_M", "FKSpine2_M", "FKChest_M"]
    # Trim or pad to match the actual CV count
    ctrl_list = ctrl_list[:num_cvs]

    for i in range(num_cvs):
        cls, cls_h = cmds.cluster(
            "{}.cv[{}]".format(crv, i), n="spineCls_{}_M".format(i),
        )
        ctrl = ctrl_list[i] if i < len(ctrl_list) else None
        if ctrl and cmds.objExists(ctrl):
            cmds.parent(cls_h, ctrl)
        else:
            cmds.parent(cls_h, builder.misc_grp)

    # Advanced twist controls (object rotation up start/end)
    cmds.setAttr(ikh + ".dTwistControlEnable", 1)
    cmds.setAttr(ikh + ".dWorldUpType", 4)
    hip_ctrl = "HipSwinger_M" if cmds.objExists("HipSwinger_M") else "RootX_M"
    chest_ctrl = "FKChest_M"
    if cmds.objExists(hip_ctrl):
        cmds.connectAttr(hip_ctrl + ".worldMatrix[0]", ikh + ".dWorldUpMatrix")
    if cmds.objExists(chest_ctrl):
        cmds.connectAttr(chest_ctrl + ".worldMatrix[0]", ikh + ".dWorldUpMatrixEnd")


# ---------------------------------------------------------------------------
# FK Arm
# ---------------------------------------------------------------------------
def build_fk_arm(builder, side):
    s = side.lower()
    col = side_color(side)
    par = "FKChest_M" if cmds.objExists("FKChest_M") else builder.ctrl_grp
    chain = [("scapula_" + s, "FKScapula_" + side),
             ("shoulder_" + s, "FKShoulder_" + side),
             ("elbow_" + s, "FKElbow_" + side),
             ("wrist_" + s, "FKWrist_" + side)]
    n = len(chain)
    for i, (slot, ctrl_name) in enumerate(chain):
        dj = builder.dj.get(slot)
        if not dj:
            continue
        r = builder.sz * 2.5 * (builder.taper ** (n - 1 - i))
        c = circle(ctrl_name, r=r, n=(1, 0, 0))
        snap(c, dj)
        color(c, col)
        o = offset(c)
        cmds.parent(o, par if cmds.objExists(par) else builder.ctrl_grp)
        builder.fk_offsets[slot] = o
        cmds.parentConstraint(c, dj, mo=1)
        par = c


# ---------------------------------------------------------------------------
# FK Leg
# ---------------------------------------------------------------------------
def build_fk_leg(builder, side):
    s = side.lower()
    col = side_color(side)
    par = "RootX_M" if cmds.objExists("RootX_M") else builder.ctrl_grp
    chain = [("hip_" + s, "FKHip_" + side),
             ("knee_" + s, "FKKnee_" + side),
             ("foot_" + s, "FKFoot_" + side),
             ("toe_" + s, "FKToe_" + side)]
    n = len(chain)
    for i, (slot, ctrl_name) in enumerate(chain):
        dj = builder.dj.get(slot)
        if not dj:
            continue
        r = builder.sz * 2.5 * (builder.taper ** (n - 1 - i))
        c = circle(ctrl_name, r=r, n=(1, 0, 0))
        snap(c, dj)
        color(c, col)
        o = offset(c)
        cmds.parent(o, par if cmds.objExists(par) else builder.ctrl_grp)
        builder.fk_offsets[slot] = o
        cmds.parentConstraint(c, dj, mo=1)
        par = c


# ---------------------------------------------------------------------------
# IK Leg (with reverse foot roll)
# ---------------------------------------------------------------------------
def build_ik_leg(builder, side):
    s = side.lower()
    hip, knee, foot = [builder.ik_dj.get(k + "_" + s) for k in ("hip", "knee", "foot")]
    if not all([hip, knee, foot]):
        return

    c = box("IKLeg_" + side, sz=builder.sz * 6)
    cmds.xform(c, ws=1, t=pos(foot))
    cmds.xform(c, ws=1, ro=(0, 0, 0))
    foot_y = pos(foot)[1]
    shift_cvs(c, dy=-foot_y)
    color(c, COL_IK if side == "L" else COL_R)
    o = offset(c)
    cmds.parent(o, builder.ctrl_grp)
    ik_key = "Leg_" + side
    builder.ik_offsets.setdefault(ik_key, []).append(o)

    ikh, _ = cmds.ikHandle(n="ikh_Leg_" + side, sj=hip, ee=foot, sol="ikRPsolver")

    toe_dj = builder.ik_dj.get("toe_" + s)
    if toe_dj:
        foot_p = pos(foot)
        toe_p = pos(toe_dj)
        heel_loc = "footRoll_heel_" + side
        toetip_loc = "footRoll_toetip_" + side
        heel_p = pos(heel_loc) if cmds.objExists(heel_loc) else [foot_p[0], 0, foot_p[2] - builder.sz * 5]
        toetip_p = pos(toetip_loc) if cmds.objExists(toetip_loc) else [toe_p[0], 0, toe_p[2] + builder.sz * 5]
        ball_p = [toe_p[0], 0, toe_p[2]]

        foot_follow = cmds.group(em=1, n="footFollow_" + side, p=builder.ik_grp)
        cmds.xform(foot_follow, ws=1, t=pos(foot))
        cmds.parentConstraint(c, foot_follow, mo=1)

        heel_grp = cmds.group(em=1, n="heelPiv_" + side, p=foot_follow)
        cmds.xform(heel_grp, ws=1, t=heel_p)
        toetip_grp = cmds.group(em=1, n="toetipPiv_" + side, p=heel_grp)
        cmds.xform(toetip_grp, ws=1, t=toetip_p)
        ball_grp = cmds.group(em=1, n="ballPiv_" + side, p=toetip_grp)
        cmds.xform(ball_grp, ws=1, t=ball_p)

        cmds.parent(ikh, ball_grp)

        ik_orient_foot = cmds.group(em=1, n="ikOrientFoot_" + side, p=ball_grp)
        cmds.xform(ik_orient_foot, ws=1, ro=cmds.xform(foot, q=1, ws=1, ro=1))
        ik_orient_toe = cmds.group(em=1, n="ikOrientToe_" + side, p=toetip_grp)
        cmds.xform(ik_orient_toe, ws=1, ro=cmds.xform(toe_dj, q=1, ws=1, ro=1))

        cmds.orientConstraint(ik_orient_foot, foot, mo=1)
        cmds.orientConstraint(ik_orient_toe, toe_dj, mo=1)

        start = builder.opts.get("roll_start_angle", 30)
        end = builder.opts.get("roll_end_angle", 60)
        cmds.addAttr(c, ln="Roll", at="float", dv=0, k=1)
        cmds.addAttr(c, ln="RollStartAngle", at="float", dv=start, k=1)
        cmds.addAttr(c, ln="RollEndAngle", at="float", dv=end, k=1)

        expr_str = (
            "float $roll  = {c}.Roll;\n"
            "float $start = {c}.RollStartAngle;\n"
            "float $end   = {c}.RollEndAngle;\n"
            "float $range = max(0.001, $end - $start);\n"
            "\n"
            "// Heel: negative roll\n"
            "{heel}.rx = clamp(-90, 0, $roll);\n"
            "\n"
            "// Ball: ramp up 0->start, ramp down start->end\n"
            "if ($roll <= 0)\n"
            "    {ball}.rx = 0;\n"
            "else if ($roll <= $start)\n"
            "    {ball}.rx = $roll;\n"
            "else if ($roll <= $end)\n"
            "    {ball}.rx = $start * ($end - $roll) / $range;\n"
            "else\n"
            "    {ball}.rx = 0;\n"
            "\n"
            "// Toetip: flat until start, then ramp up\n"
            "if ($roll <= $start)\n"
            "    {toetip}.rx = 0;\n"
            "else if ($roll <= $end)\n"
            "    {toetip}.rx = $roll - $start;\n"
            "else\n"
            "    {toetip}.rx = $end - $start;\n"
        ).format(c=c, heel=heel_grp, ball=ball_grp, toetip=toetip_grp)
        cmds.expression(n="footRoll_expr_" + side, s=expr_str, ae=1)
    else:
        cmds.parent(ikh, builder.ik_grp)
        cmds.pointConstraint(c, ikh)
        cmds.orientConstraint(c, foot, mo=1)

    pole = cross("PoleLeg_" + side, sz=builder.sz * 3)
    cmds.xform(pole, ws=1, t=pole_pos(knee, builder.sz * 20, (0, 0, 1)))
    color(pole, side_color(side))
    po = offset(pole)
    cmds.parent(po, builder.ctrl_grp)
    builder.ik_offsets[ik_key].append(po)
    cmds.poleVectorConstraint(pole, ikh)


# ---------------------------------------------------------------------------
# IK Arm
# ---------------------------------------------------------------------------
def build_ik_arm(builder, side):
    s = side.lower()
    sho, elb, wri = [builder.ik_dj.get(k + "_" + s) for k in ("shoulder", "elbow", "wrist")]
    if not all([sho, elb, wri]):
        return

    wri_rest_ro = cmds.xform(wri, q=1, ws=1, ro=1)

    box_sz = builder.sz * 5
    c = box("IKArm_" + side, sz=box_sz)
    cmds.xform(c, ws=1, t=pos(wri))
    skin_wri = builder.m.get("wrist_" + s)
    if skin_wri and cmds.objExists(skin_wri):
        cmds.xform(c, ws=1, ro=cmds.xform(skin_wri, q=1, ws=1, ro=1))
    else:
        cmds.xform(c, ws=1, ro=wri_rest_ro)
    half = box_sz * 0.5
    shift_cvs(c, dx=half, dy=-half)
    color(c, COL_IK if side == "L" else COL_R)
    o = offset(c)
    cmds.parent(o, builder.ctrl_grp)
    ik_key = "Arm_" + side
    builder.ik_offsets.setdefault(ik_key, []).append(o)

    ikh, _ = cmds.ikHandle(n="ikh_Arm_" + side, sj=sho, ee=wri, sol="ikRPsolver")
    cmds.parent(ikh, builder.ik_grp)
    cmds.pointConstraint(c, ikh)

    pole = cross("PoleArm_" + side, sz=builder.sz * 3)
    cmds.xform(pole, ws=1, t=pole_pos(elb, builder.sz * 20, (0, 0, -1)))
    color(pole, side_color(side))
    po = offset(pole)
    cmds.parent(po, builder.ctrl_grp)
    builder.ik_offsets[ik_key].append(po)
    cmds.poleVectorConstraint(pole, ikh)

    ik_orient_wrist = cmds.group(em=1, n="ikOrientWrist_" + side, p=c)
    cmds.xform(ik_orient_wrist, ws=1, ro=wri_rest_ro)
    cmds.orientConstraint(ik_orient_wrist, wri, mo=1)


# ---------------------------------------------------------------------------
# FK/IK Blend Switch
# ---------------------------------------------------------------------------
def build_fkik(builder, limb, side):
    s = side.lower()
    end_slot = ("foot_" if limb == "Leg" else "wrist_") + s
    ref = builder.dj.get(end_slot)
    if not ref:
        return

    c = diamond("FKIK{}_{}".format(limb, side), sz=builder.sz * 2)
    ref_p = pos(ref)
    sign = 1 if ref_p[0] > 0 else -1
    if limb == "Leg":
        knee = builder.dj.get("knee_" + s)
        hip = builder.dj.get("hip_" + s)
        if knee and hip:
            knee_p = pos(knee)
            hip_p = pos(hip)
            mid_y = (hip_p[1] + knee_p[1]) * 0.5
            cmds.xform(c, ws=1, t=(knee_p[0] + builder.sz * 6 * sign, mid_y, knee_p[2]))
        else:
            cmds.xform(c, ws=1, t=(ref_p[0] + builder.sz * 6 * sign, ref_p[1], ref_p[2]))
    else:
        sho = builder.dj.get("shoulder_" + s)
        sho_p = pos(sho) if sho else ref_p
        sign = 1 if sho_p[0] > 0 else -1
        cmds.xform(c, ws=1, t=(sho_p[0] + builder.sz * 5 * sign,
                                sho_p[1] + builder.sz * 8, sho_p[2]))
    color(c, side_color(side))
    o = offset(c)
    cmds.parent(o, builder.ctrl_grp)

    cmds.addAttr(c, ln="FKIKBlend", at="float", min=0, max=10, dv=10, k=1)

    norm = cmds.createNode("multiplyDivide", n="fkikN_{}_{}".format(limb, side))
    cmds.setAttr(norm + ".operation", 2)
    cmds.connectAttr(c + ".FKIKBlend", norm + ".input1X")
    cmds.setAttr(norm + ".input2X", 10)

    rev = cmds.createNode("reverse", n="fkikR_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", rev + ".inputX")

    ikh = "ikh_{}_{}".format(limb, side)
    if cmds.objExists(ikh):
        cmds.connectAttr(norm + ".outputX", ikh + ".ikBlend")

    # Blend weights on skin joint parentConstraints (FK driver + IK driver)
    if limb == "Leg":
        blend_slots = ["hip_" + s, "knee_" + s, "foot_" + s, "toe_" + s]
    else:
        blend_slots = ["shoulder_" + s, "elbow_" + s, "wrist_" + s]

    for sl in blend_slots:
        sc = builder.skin_con.get(sl)
        if not sc or not cmds.objExists(sc):
            continue
        w = cmds.parentConstraint(sc, q=1, wal=1)
        if len(w) >= 2:
            cmds.connectAttr(rev + ".outputX", "{}.{}".format(sc, w[0]))
            cmds.connectAttr(norm + ".outputX", "{}.{}".format(sc, w[1]))

    # Visibility
    fk_vis = cmds.createNode("condition", n="fkVis_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", fk_vis + ".firstTerm")
    cmds.setAttr(fk_vis + ".secondTerm", 1)
    cmds.setAttr(fk_vis + ".operation", 4)
    cmds.setAttr(fk_vis + ".colorIfTrueR", 1)
    cmds.setAttr(fk_vis + ".colorIfFalseR", 0)

    ik_vis = cmds.createNode("condition", n="ikVis_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", ik_vis + ".firstTerm")
    cmds.setAttr(ik_vis + ".secondTerm", 0)
    cmds.setAttr(ik_vis + ".operation", 2)
    cmds.setAttr(ik_vis + ".colorIfTrueR", 1)
    cmds.setAttr(ik_vis + ".colorIfFalseR", 0)

    if limb == "Leg":
        vis_fk = ["hip_" + s, "knee_" + s, "foot_" + s, "toe_" + s]
    else:
        vis_fk = ["shoulder_" + s, "elbow_" + s, "wrist_" + s]
    for sl in vis_fk:
        off = builder.fk_offsets.get(sl)
        if off and cmds.objExists(off):
            cmds.connectAttr(fk_vis + ".outColorR", off + ".v")

    ik_key = "{}_{}".format(limb, side)
    for off in builder.ik_offsets.get(ik_key, []):
        if cmds.objExists(off):
            cmds.connectAttr(ik_vis + ".outColorR", off + ".v")
