import maya.cmds as cmds
import math

from .constants import SLOT_TO_CTRL, COL_M, COL_IK, COL_R
from .utils import pos, color, side_color, circle, box, cross, diamond, snap, offset, shift_cvs, pole_pos


# ---------------------------------------------------------------------------
# Main (world) controller
# ---------------------------------------------------------------------------
def build_main(builder):
    c = circle("Main_M", r=builder.sz * 12)
    cmds.xform(c, ws=1, t=(0, 0, 0), ro=(0, 0, 0))
    color(c, COL_M)
    o = offset(c)
    cmds.parent(o, builder.top)
    for grp in [builder.ctrl_grp, builder.drv_grp, builder.ik_grp, builder.misc_grp]:
        cmds.parent(grp, c)
    builder.main = c


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
        builder.fk_offsets[slot] = o
        cmds.parentConstraint(c, dj, mo=1)
        par = c


# ---------------------------------------------------------------------------
# IK Spline Spine
# ---------------------------------------------------------------------------
def build_ik_spine(builder):
    spine_ik = builder.ik_dj.get("spine")
    chest_ik = builder.ik_dj.get("chest")
    if not spine_ik or not chest_ik:
        return

    ikh, eff, crv = cmds.ikHandle(
        n="ikh_Spine_M", sj=spine_ik, ee=chest_ik,
        sol="ikSplineSolver", ccv=True, scv=False, pcv=False,
    )
    crv = cmds.rename(crv, "ikSplineCrv_Spine")
    cmds.parent(ikh, builder.ik_grp)
    cmds.parent(crv, builder.misc_grp)
    cmds.setAttr(crv + ".inheritsTransform", 0)

    ik_key = "Spine_M"
    builder.ik_offsets.setdefault(ik_key, [])

    root_ctrl = "RootX_M" if cmds.objExists("RootX_M") else builder.ctrl_grp

    # --- Bottom IK control (hip-level) ---
    ik_spine = circle("IKSpine_M", r=builder.sz * 9, n=(1, 0, 0))
    snap(ik_spine, spine_ik)
    color(ik_spine, COL_IK)
    ik_spine_off = offset(ik_spine)
    cmds.parent(ik_spine_off, root_ctrl)
    builder.ik_offsets[ik_key].append(ik_spine_off)

    # --- Mid IK control (between spine and chest) ---
    spine1_ik = builder.ik_dj.get("spine_1")
    mid_ref = spine1_ik if spine1_ik else spine_ik
    ik_mid = circle("IKSpineMid_M", r=builder.sz * 7.5, n=(1, 0, 0))
    snap(ik_mid, mid_ref)
    color(ik_mid, COL_IK)
    ik_mid_off = offset(ik_mid)
    cmds.parent(ik_mid_off, root_ctrl)
    builder.ik_offsets[ik_key].append(ik_mid_off)

    # --- Top IK control (chest-level) ---
    ik_chest = circle("IKChest_M", r=builder.sz * 9, n=(1, 0, 0))
    snap(ik_chest, chest_ik)
    color(ik_chest, COL_IK)
    ik_chest_off = offset(ik_chest)
    cmds.parent(ik_chest_off, root_ctrl)
    builder.ik_offsets[ik_key].append(ik_chest_off)

    # Cluster each CV: CV0 → bottom, CV1 → mid, CV2 → mid, CV3 → top
    num_cvs = cmds.getAttr(crv + ".cp", s=1)
    for i in range(num_cvs):
        cls, cls_h = cmds.cluster(
            "{}.cv[{}]".format(crv, i), n="spineCls_{}_M".format(i),
        )
        if i == 0:
            parent_ctrl = ik_spine
        elif i == num_cvs - 1:
            parent_ctrl = ik_chest
        else:
            parent_ctrl = ik_mid
        cmds.parent(cls_h, parent_ctrl)

    # Advanced twist controls (object rotation up start/end)
    cmds.setAttr(ikh + ".dTwistControlEnable", 1)
    cmds.setAttr(ikh + ".dWorldUpType", 4)
    cmds.connectAttr(ik_spine + ".worldMatrix[0]", ikh + ".dWorldUpMatrix")
    cmds.connectAttr(ik_chest + ".worldMatrix[0]", ikh + ".dWorldUpMatrixEnd")

    # Store chest IK ctrl name so build_spaces can use it
    builder.ik_chest_ctrl = ik_chest


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

    # Determine blend slots and reference joint per limb type
    if limb == "Spine":
        blend_slots = ["spine", "spine_1", "chest"]
        ref = builder.dj.get("chest")
    elif limb == "Leg":
        blend_slots = ["hip_" + s, "knee_" + s, "foot_" + s, "toe_" + s]
        ref = builder.dj.get("foot_" + s)
    else:
        blend_slots = ["shoulder_" + s, "elbow_" + s, "wrist_" + s]
        ref = builder.dj.get("wrist_" + s)
    if not ref:
        return

    c = diamond("FKIK{}_{}".format(limb, side), sz=builder.sz * 2)
    ref_p = pos(ref)
    sign = 1 if ref_p[0] > 0 else -1
    if limb == "Spine":
        spine_dj = builder.dj.get("spine")
        spine_p = pos(spine_dj) if spine_dj else ref_p
        cmds.xform(c, ws=1, t=(spine_p[0] + builder.sz * 10,
                                spine_p[1], spine_p[2]))
    elif limb == "Leg":
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
    color(c, COL_M if limb == "Spine" else side_color(side))
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
    for sl in blend_slots:
        sc = builder.skin_con.get(sl)
        if not sc or not cmds.objExists(sc):
            continue
        w = cmds.parentConstraint(sc, q=1, wal=1)
        if len(w) >= 2:
            cmds.connectAttr(rev + ".outputX", "{}.{}".format(sc, w[0]))
            cmds.connectAttr(norm + ".outputX", "{}.{}".format(sc, w[1]))

    # Visibility — FK side
    fk_vis = cmds.createNode("condition", n="fkVis_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", fk_vis + ".firstTerm")
    cmds.setAttr(fk_vis + ".secondTerm", 1)
    cmds.setAttr(fk_vis + ".operation", 4)
    cmds.setAttr(fk_vis + ".colorIfTrueR", 1)
    cmds.setAttr(fk_vis + ".colorIfFalseR", 0)

    if limb == "Spine":
        # Spine FK forms a parent chain shared with neck/head,
        # so hide only the shape nodes (not the offset groups).
        for sl in blend_slots:
            ctrl = SLOT_TO_CTRL.get(sl)
            if ctrl and cmds.objExists(ctrl):
                for shp in cmds.listRelatives(ctrl, s=1) or []:
                    cmds.connectAttr(fk_vis + ".outColorR", shp + ".v")
    else:
        for sl in blend_slots:
            off = builder.fk_offsets.get(sl)
            if off and cmds.objExists(off):
                cmds.connectAttr(fk_vis + ".outColorR", off + ".v")

    ik_vis = cmds.createNode("condition", n="ikVis_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", ik_vis + ".firstTerm")
    cmds.setAttr(ik_vis + ".secondTerm", 0)
    cmds.setAttr(ik_vis + ".operation", 2)
    cmds.setAttr(ik_vis + ".colorIfTrueR", 1)
    cmds.setAttr(ik_vis + ".colorIfFalseR", 0)

    ik_key = "{}_{}".format(limb, side)
    for off in builder.ik_offsets.get(ik_key, []):
        if cmds.objExists(off):
            cmds.connectAttr(ik_vis + ".outColorR", off + ".v")

    # Driver joint drawStyle — hide the inactive chain's bones without
    # affecting child visibility (drawStyle 0=Bone, 2=None).
    fk_drv_ds = cmds.createNode("condition",
                                n="fkDrvDs_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", fk_drv_ds + ".firstTerm")
    cmds.setAttr(fk_drv_ds + ".secondTerm", 1)
    cmds.setAttr(fk_drv_ds + ".operation", 4)   # less than
    cmds.setAttr(fk_drv_ds + ".colorIfTrueR", 0)   # Bone
    cmds.setAttr(fk_drv_ds + ".colorIfFalseR", 2)   # None

    ik_drv_ds = cmds.createNode("condition",
                                n="ikDrvDs_{}_{}".format(limb, side))
    cmds.connectAttr(norm + ".outputX", ik_drv_ds + ".firstTerm")
    cmds.setAttr(ik_drv_ds + ".secondTerm", 0)
    cmds.setAttr(ik_drv_ds + ".operation", 2)   # greater than
    cmds.setAttr(ik_drv_ds + ".colorIfTrueR", 0)   # Bone
    cmds.setAttr(ik_drv_ds + ".colorIfFalseR", 2)   # None

    for sl in blend_slots:
        dj = builder.dj.get(sl)
        if dj and cmds.objExists(dj):
            cmds.connectAttr(fk_drv_ds + ".outColorR", dj + ".drawStyle")
        ik_dj = builder.ik_dj.get(sl)
        if ik_dj and cmds.objExists(ik_dj):
            cmds.connectAttr(ik_drv_ds + ".outColorR", ik_dj + ".drawStyle")


# ---------------------------------------------------------------------------
# Chest follow & IK space switching (called after FKIK blends)
# ---------------------------------------------------------------------------
def build_spaces(builder):
    main_ctrl = getattr(builder, "main", "Main_M")

    # --- Chest Follow ---
    # Creates a group that always follows the *result* chest position,
    # regardless of FK/IK mode.  Neck, head, and arm FK offset groups
    # are reparented under this so they automatically follow the spine.
    #
    # When IK spine is active, the IK chest control (IKChest_M) drives
    # the ik_drv_chest joint via the spline solver.  We parentConstraint
    # chestFollow to both FK and IK chest drivers, blended by the FKIK
    # weight so appendages always track the active mode.
    chest_fk = builder.dj.get("chest")
    chest_ik = builder.ik_dj.get("chest")
    ik_chest_ctrl = getattr(builder, "ik_chest_ctrl", None)
    chest_follow = None

    if chest_fk and chest_ik and cmds.objExists("fkikN_Spine_M"):
        cf = cmds.group(em=1, n="chestFollow_M")
        snap(cf, chest_fk)
        cmds.parent(cf, builder.ctrl_grp)

        # ParentConstraint to the FK chest *control* (not driver joint)
        # and to the IK chest *control*.  This way chestFollow always
        # inherits the full transform of whichever mode is active,
        # including any user rotations on the IK/FK control.
        fk_chest_ctrl = "FKChest_M"
        ik_tgt = ik_chest_ctrl if ik_chest_ctrl and cmds.objExists(ik_chest_ctrl) else chest_ik
        fk_tgt = fk_chest_ctrl if cmds.objExists(fk_chest_ctrl) else chest_fk

        con = cmds.parentConstraint(fk_tgt, ik_tgt, cf, mo=1)[0]
        w = cmds.parentConstraint(con, q=1, wal=1)
        if len(w) >= 2:
            cmds.connectAttr("fkikR_Spine_M.outputX",
                             "{}.{}".format(con, w[0]))
            cmds.connectAttr("fkikN_Spine_M.outputX",
                             "{}.{}".format(con, w[1]))

        # Reparent neck and scapula FK offsets under chestFollow so the
        # entire FK arm/neck/head chain inherits the blended chest.
        for slot in ["neck", "scapula_l", "scapula_r"]:
            off = builder.fk_offsets.get(slot)
            if off and cmds.objExists(off):
                cmds.parent(off, cf)
        chest_follow = cf

    elif chest_fk and not chest_ik:
        # No IK spine — chestFollow is just FKChest_M directly
        chest_follow = "FKChest_M" if cmds.objExists("FKChest_M") else None

    # --- IK Leg spaces: Main (default) / Root ---
    for side in "LR":
        _build_ik_space(builder, "Leg_" + side, "IKLeg_" + side,
                        [(main_ctrl, "Main"), ("RootX_M", "Root")], 0)

    # --- IK Arm spaces: Main (default) / Root / Chest / Head ---
    chest_target = chest_follow if chest_follow else "FKChest_M"
    for side in "LR":
        _build_ik_space(builder, "Arm_" + side, "IKArm_" + side,
                        [(main_ctrl, "Main"), ("RootX_M", "Root"),
                         (chest_target, "Chest"), ("FKHead_M", "Head")], 0)


def _build_ik_space(builder, ik_key, ctrl_name, targets, default_idx):
    offsets = builder.ik_offsets.get(ik_key, [])
    if not offsets or not cmds.objExists(ctrl_name):
        return
    # Verify all targets exist
    targets = [(t, lbl) for t, lbl in targets if cmds.objExists(t)]
    if not targets:
        return

    space = cmds.group(em=1, n="space_" + ik_key)
    cmds.parent(space, builder.ctrl_grp)
    for off in offsets:
        if cmds.objExists(off):
            cmds.parent(off, space)

    enum_str = ":".join(lbl for _, lbl in targets)
    cmds.addAttr(ctrl_name, ln="Space", at="enum", en=enum_str,
                 dv=default_idx, k=1)

    target_nodes = [t for t, _ in targets]
    con = cmds.parentConstraint(*target_nodes, space, mo=1)[0]
    w = cmds.parentConstraint(con, q=1, wal=1)

    for i, wa in enumerate(w):
        cond = cmds.createNode("condition",
                               n="spaceCond_{}_{}".format(ik_key, targets[i][1]))
        cmds.connectAttr(ctrl_name + ".Space", cond + ".firstTerm")
        cmds.setAttr(cond + ".secondTerm", i)
        cmds.setAttr(cond + ".operation", 0)  # Equal
        cmds.setAttr(cond + ".colorIfTrueR", 1)
        cmds.setAttr(cond + ".colorIfFalseR", 0)
        cmds.connectAttr(cond + ".outColorR", "{}.{}".format(con, wa))
