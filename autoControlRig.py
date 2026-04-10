"""
autoControlRig.py  —  Auto Control Rig for Maya (Driver-Skeleton approach)

Generates AdvancedSkeleton-compatible controls on any joint hierarchy.
A clean intermediate "driver" skeleton is built with proper orientations,
IK/FK controls drive those driver joints, and the original skin joints
are simply parent-constrained to follow.

Usage:
    import autoControlRig; autoControlRig.show()
"""

import maya.cmds as cmds
import json, math, os

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RIG_GRP = "AutoCtrlRig_GRP"

SLOT_DEFS = [
    ("root",       "Root / Pelvis",        "M", ["pelvis","hips","root"]),
    ("spine",      "Spine",                "M", ["spine_01","spine1","spine"]),
    ("chest",      "Chest",                "M", ["spine_02","spine2","chest"]),
    ("neck",       "Neck",                 "M", ["neck"]),
    ("head",       "Head",                 "M", ["head"]),
    ("scapula_l",  "Scapula / Clavicle L", "L", ["clavicle_l","l_clavicle","shoulder_l","leftshoulder"]),
    ("shoulder_l", "Upper Arm L",          "L", ["upperarm_l","l_upperarm","arm_l","leftarm"]),
    ("elbow_l",    "Lower Arm L",          "L", ["lowerarm_l","l_lowerarm","forearm_l","leftforearm"]),
    ("wrist_l",    "Hand L",               "L", ["hand_l","l_hand","lefthand"]),
    ("scapula_r",  "Scapula / Clavicle R", "R", ["clavicle_r","r_clavicle","shoulder_r","rightshoulder"]),
    ("shoulder_r", "Upper Arm R",          "R", ["upperarm_r","r_upperarm","arm_r","rightarm"]),
    ("elbow_r",    "Lower Arm R",          "R", ["lowerarm_r","r_lowerarm","forearm_r","rightforearm"]),
    ("wrist_r",    "Hand R",               "R", ["hand_r","r_hand","righthand"]),
    ("hip_l",      "Upper Leg L",          "L", ["thigh_l","l_thigh","upperleg_l","leftupleg"]),
    ("knee_l",     "Lower Leg L",          "L", ["calf_l","l_calf","lowerleg_l","shin_l","leftleg"]),
    ("foot_l",     "Foot L",               "L", ["foot_l","l_foot","leftfoot"]),
    ("toe_l",      "Toe L",                "L", ["toe_l","l_toe","ball_l","lefttoebase"]),
    ("hip_r",      "Upper Leg R",          "R", ["thigh_r","r_thigh","upperleg_r","rightupleg"]),
    ("knee_r",     "Lower Leg R",          "R", ["calf_r","r_calf","lowerleg_r","shin_r","rightleg"]),
    ("foot_r",     "Foot R",               "R", ["foot_r","r_foot","rightfoot"]),
    ("toe_r",      "Toe R",                "R", ["toe_r","r_toe","ball_r","righttoebase"]),
]

SLOT_TO_CTRL = {
    "root":"RootX_M", "spine":"FKSpine1_M", "chest":"FKChest_M",
    "neck":"FKNeck_M", "head":"FKHead_M",
    "scapula_l":"FKScapula_L", "shoulder_l":"FKShoulder_L",
    "elbow_l":"FKElbow_L", "wrist_l":"FKWrist_L",
    "scapula_r":"FKScapula_R", "shoulder_r":"FKShoulder_R",
    "elbow_r":"FKElbow_R", "wrist_r":"FKWrist_R",
    "hip_l":"FKHip_L", "knee_l":"FKKnee_L", "foot_l":"FKFoot_L", "toe_l":"FKToe_L",
    "hip_r":"FKHip_R", "knee_r":"FKKnee_R", "foot_r":"FKFoot_R", "toe_r":"FKToe_R",
}

COL_L, COL_R, COL_M, COL_IK, COL_POLE = 13, 6, 17, 18, 9


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------
def _pos(jnt):
    return cmds.xform(jnt, q=1, ws=1, t=1)

def _color(ctrl, idx):
    for s in (cmds.listRelatives(ctrl, s=1, f=1) or []):
        cmds.setAttr(s+".overrideEnabled", 1)
        cmds.setAttr(s+".overrideColor", idx)

def _side_color(side):
    return COL_L if side == "L" else (COL_R if side == "R" else COL_M)

def _circle(name, r=1, n=(0,1,0)):
    return cmds.circle(n=name, r=r, nr=n, ch=0)[0]

def _box(name, sz=1):
    h = sz; s = sz * 0.5
    pts = [(-s,0,-s),(-s,0,s),(s,0,s),(s,0,-s),(-s,0,-s),
           (-s,h,-s),(-s,h,s),(s,h,s),(s,h,-s),(-s,h,-s)]
    c = cmds.curve(n=name, d=1, p=pts)
    for a, b in [(1,6),(2,7),(3,8)]:
        ex = cmds.curve(d=1, p=[pts[a], pts[b]])
        cmds.parent(cmds.listRelatives(ex, s=1)[0], c, s=1, r=1)
        cmds.delete(ex)
    return c

def _diamond(name, sz=1):
    s = sz
    return cmds.curve(n=name, d=1, p=[(0,s,0),(s,0,0),(0,-s,0),(-s,0,0),
                                       (0,s,0),(0,0,s),(0,-s,0),(0,0,-s),(0,s,0)])

def _snap(node, jnt):
    cmds.xform(node, ws=1, t=_pos(jnt))
    cmds.xform(node, ws=1, ro=cmds.xform(jnt, q=1, ws=1, ro=1))

def _offset(ctrl):
    """Create an offset (zero) group above ctrl. Returns group name."""
    grp = cmds.group(em=1, n=ctrl+"_offset")
    cmds.xform(grp, ws=1, t=cmds.xform(ctrl, q=1, ws=1, t=1))
    cmds.xform(grp, ws=1, ro=cmds.xform(ctrl, q=1, ws=1, ro=1))
    cmds.parent(ctrl, grp)
    cmds.xform(ctrl, t=(0,0,0), ro=(0,0,0))
    return grp

def _shift_cvs(ctrl, dx=0, dy=0, dz=0):
    """Move all CVs of a curve control without moving its pivot."""
    for shp in (cmds.listRelatives(ctrl, s=1, f=1) or []):
        ncv = cmds.getAttr(shp+".cp", size=1)
        for i in range(ncv):
            p = cmds.getAttr("{}.cp[{}]".format(shp, i))[0]
            cmds.setAttr("{}.cp[{}]".format(shp, i), p[0]+dx, p[1]+dy, p[2]+dz)


# ---------------------------------------------------------------------------
# Driver-skeleton utilities
# ---------------------------------------------------------------------------
def _make_driver_joint(skin_jnt, name, parent):
    cmds.select(cl=1)
    dj = cmds.joint(n=name)
    cmds.xform(dj, ws=1, t=_pos(skin_jnt))
    cmds.parent(dj, parent)
    return dj


def _orient_chain(joints):
    """Orient a joint chain: X aim down bone, Y up = world-Y."""
    if len(joints) < 2:
        return
    for j in joints[:-1]:
        cmds.joint(j, e=1, oj="xyz", sao="yup", zso=1)
    # Last joint copies parent orient
    po = cmds.getAttr(joints[-2]+".jointOrient")[0]
    cmds.setAttr(joints[-1]+".jointOrient", *po)


def _orient_ik_chain(start, mid, end, bend_dir):
    """Orient a 3-joint chain and inject a tiny pre-bend toward bend_dir."""
    _orient_chain([start, mid, end])
    # Save end joint position before pre-bend (bend shifts children)
    end_pos = _pos(end)
    # Small bend to break collinearity
    cmds.xform(mid, r=1, ro=(0, 0, 2), os=1)
    # Check direction — flip if wrong
    a, b, c = _pos(start), _pos(mid), _pos(end)
    mp = [(a[i]+c[i])*0.5 for i in range(3)]
    v = [b[i]-mp[i] for i in range(3)]
    dot = sum(v[i]*bend_dir[i] for i in range(3))
    if dot < 0:
        cmds.xform(mid, r=1, ro=(0, 0, -4), os=1)
    cmds.joint(mid, e=1, spa=1)
    # Restore end joint to exact skin position (pre-bend displaced it)
    cmds.xform(end, ws=1, t=end_pos)


def _pole_pos(j_mid, dist, direction):
    """Pole vector at mid-joint, pushed along a known direction."""
    p = _pos(j_mid)
    ln = math.sqrt(sum(d*d for d in direction)) or 1
    return [p[i] + (direction[i]/ln)*dist for i in range(3)]

def _sdk(driven_attr, driver_attr, keys):
    """Set driven keys with linear tangents.  keys = [(driver_val, driven_val), ...]"""
    for dv, v in keys:
        cmds.setDrivenKeyframe(driven_attr, cd=driver_attr, dv=dv, v=v)
    curves = cmds.listConnections(driven_attr, type="animCurveUU", s=1, d=0) or []
    for crv in curves:
        cmds.keyTangent(crv, itt="linear", ott="linear")


# ---------------------------------------------------------------------------
# Hierarchy scan & auto-map
# ---------------------------------------------------------------------------
def get_hierarchy_joints(root):
    desc = cmds.listRelatives(root, ad=1, type="joint", f=1) or []
    return [j.split("|")[-1] for j in [root] + desc]


def auto_map_joints(joint_list):
    mapping = {}
    lmap = {j.lower(): j for j in joint_list}
    for key, _, _, hints in SLOT_DEFS:
        found = ""
        for h in hints:
            hl = h.lower()
            if hl in lmap:
                found = lmap[hl]; break
            for jl, jn in lmap.items():
                if hl in jl:
                    found = jn; break
            if found:
                break
        mapping[key] = found
    return mapping


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
class AutoControlRigBuilder:
    """
    Architecture:
        Controls  -->  Driver joints (clean orient, IK-friendly)
                            |
                       parentConstraint (maintainOffset)
                            v
                       Skin joints (untouched)
    """
    def __init__(self, mapping, opts):
        self.m = mapping            # slot -> skin joint name
        self.opts = opts
        self.sz = opts.get("control_size", 1.0)
        self.taper = opts.get("scale_taper", 1.3)
        self.dj = {}                # slot -> driver joint
        self.fk_con = {}            # slot -> orient constraint on driver
        self.ik_con = {}            # end slot -> orient constraint on driver
        self.fk_offsets = {}        # slot -> FK offset group
        self.ik_offsets = {}        # "Limb_Side" -> list of IK offset groups
        self.ik_fk_oc = {}          # end slot -> orient constraint (IK ctrl -> FK ctrl)
        self.skin_constraints = []  # list of constraint names on skin joints
        self.twist_nodes = []       # utility nodes for twist joint drivers

    # ----- public ----------------------------------------------------------
    def build(self):
        if cmds.objExists(RIG_GRP):
            cmds.warning("Rig exists — remove it first."); return

        # Top groups
        self.top = cmds.group(em=1, n=RIG_GRP)
        self.ctrl_grp = cmds.group(em=1, n="Ctrl_GRP", p=self.top)
        self.drv_grp  = cmds.group(em=1, n="Driver_GRP", p=self.top)
        self.ik_grp   = cmds.group(em=1, n="IK_GRP", p=self.top)
        self.misc_grp = cmds.group(em=1, n="Misc_GRP", p=self.top)
        cmds.setAttr(self.ik_grp+".v", 0)
        cmds.setAttr(self.misc_grp+".v", 0)

        # 1) Driver skeleton
        self._driver_skeleton()
        # 2) Controls
        self._ctrl_root()
        self._ctrl_fk_spine()
        for s in "LR":
            if self.opts.get("create_fk_arms", True):  self._ctrl_fk_arm(s)
            if self.opts.get("create_fk_legs", True):  self._ctrl_fk_leg(s)
            if self.opts.get("create_ik_legs", True):  self._ctrl_ik_leg(s)
            if self.opts.get("create_ik_arms", True):  self._ctrl_ik_arm(s)
        for s in "LR":
            if self.opts.get("create_fkik_blend", True):
                if self.opts.get("create_ik_legs") and self.opts.get("create_fk_legs"):
                    self._ctrl_fkik("Leg", s)
                if self.opts.get("create_ik_arms") and self.opts.get("create_fk_arms"):
                    self._ctrl_fkik("Arm", s)
        # 3) Bind skin joints to driver
        self._bind_skin()
        # 3.25) Twist joint drivers
        if self.opts.get("create_twist_drivers", True):
            self._setup_twist_joints()
        # 3.5) Debug visualization
        if self.opts.get("show_debug", False):
            self._create_debug_vis()
        # 4) Store data for clean removal
        cmds.addAttr(self.top, ln="skin_constraints", dt="string")
        cmds.setAttr(self.top+".skin_constraints",
                     json.dumps(self.skin_constraints), type="string")
        cmds.addAttr(self.top, ln="twist_nodes", dt="string")
        cmds.setAttr(self.top+".twist_nodes",
                     json.dumps(self.twist_nodes), type="string")
        cmds.addAttr(self.top, ln="bind_pose", dt="string")
        cmds.setAttr(self.top+".bind_pose",
                     json.dumps(self.bind_pose), type="string")

        cmds.select(cl=1)
        print("// AutoControlRig built.")

    # ----- driver skeleton -------------------------------------------------
    def _driver_skeleton(self):
        m, dj, grp = self.m, self.dj, self.drv_grp

        # Root
        self._drv("root", grp, copy_orient=True)

        # Spine
        spine = ["spine","chest","neck","head"]
        par = dj.get("root", grp)
        for sl in spine:
            self._drv(sl, par); par = dj.get(sl, par)
        chain = [dj[s] for s in spine if s in dj]
        if chain: _orient_chain(chain)

        # Arms & legs
        for s in ("l","r"):
            S = s.upper()
            self._driver_arm(s, S)
            self._driver_leg(s, S)

    def _drv(self, slot, parent, copy_orient=False):
        """Create one driver joint for slot if mapped."""
        skin = self.m.get(slot, "")
        if not skin or not cmds.objExists(skin):
            return
        dj = _make_driver_joint(skin, "drv_"+slot, parent)
        if copy_orient:
            cmds.xform(dj, ws=1, ro=cmds.xform(skin, q=1, ws=1, ro=1))
            cmds.makeIdentity(dj, a=1, r=1)
        self.dj[slot] = dj

    def _driver_arm(self, s, S):
        chest = self.dj.get("chest", self.drv_grp)
        self._drv("scapula_"+s, chest)
        par = self.dj.get("scapula_"+s, chest)
        for sl in ["shoulder_"+s, "elbow_"+s, "wrist_"+s]:
            self._drv(sl, par); par = self.dj.get(sl, par)

        arm = [self.dj[k] for k in ["shoulder_"+s,"elbow_"+s,"wrist_"+s] if k in self.dj]
        if len(arm) == 3:
            _orient_ik_chain(arm[0], arm[1], arm[2], bend_dir=(0,0,-1))

        sc = self.dj.get("scapula_"+s)
        if sc and arm:
            cmds.joint(sc, e=1, oj="xyz", sao="yup", zso=1)

    def _driver_leg(self, s, S):
        root = self.dj.get("root", self.drv_grp)
        # Create hip, knee, foot first (NOT toe — it would shift during orient)
        for sl in ["hip_"+s, "knee_"+s, "foot_"+s]:
            self._drv(sl, root); root = self.dj.get(sl, root)

        leg = [self.dj[k] for k in ["hip_"+s,"knee_"+s,"foot_"+s] if k in self.dj]
        if len(leg) == 3:
            _orient_ik_chain(leg[0], leg[1], leg[2], bend_dir=(0,0,1))

        # Create toe AFTER orienting the IK chain so foot orient doesn't displace it
        foot_drv = self.dj.get("foot_"+s, root)
        self._drv("toe_"+s, foot_drv)
        toe = self.dj.get("toe_"+s)
        if toe and len(leg) == 3:
            fo = cmds.getAttr(leg[2]+".jointOrient")[0]
            cmds.setAttr(toe+".jointOrient", *fo)

    # ----- bind skin joints ------------------------------------------------
    def _bind_skin(self):
        self.bind_pose = {}
        for slot, dj in self.dj.items():
            skin = self.m.get(slot, "")
            if skin and cmds.objExists(skin):
                self.bind_pose[skin] = {
                    "t": list(cmds.getAttr(skin+".t")[0]),
                    "r": list(cmds.getAttr(skin+".r")[0]),
                    "s": list(cmds.getAttr(skin+".s")[0]),
                }
                c = cmds.parentConstraint(dj, skin, mo=1)[0]
                self.skin_constraints.append(c)

    # ----- debug visualization ---------------------------------------------
    def _create_debug_vis(self):
        dbg = cmds.group(em=1, n="Debug_GRP", p=self.top)
        lsz = self.sz * 3
        for slot, dj in self.dj.items():
            loc = cmds.spaceLocator(n="dbg_"+slot)[0]
            for ax in ("X","Y","Z"):
                cmds.setAttr(loc+".localScale"+ax, lsz)
            cmds.parentConstraint(dj, loc, mo=0)
            cmds.parent(loc, dbg)
        # Foot roll pivot locators (heel, ball, toetip)
        for side in ("L","R"):
            roll_pivots = [
                ("heelPiv_"+side,   "dbg_heelPiv_"+side,   COL_IK),
                ("ballPiv_"+side,   "dbg_ballPiv_"+side,   COL_M),
                ("toetipPiv_"+side, "dbg_toetipPiv_"+side, COL_POLE),
            ]
            for grp_name, loc_name, col in roll_pivots:
                if not cmds.objExists(grp_name):
                    continue
                loc = cmds.spaceLocator(n=loc_name)[0]
                for ax in ("X","Y","Z"):
                    cmds.setAttr(loc+".localScale"+ax, lsz)
                _color(loc, col)
                cmds.parentConstraint(grp_name, loc, mo=0)
                cmds.parent(loc, dbg)

    # ----- twist joint drivers ---------------------------------------------
    def _setup_twist_joints(self):
        """Counter-rotate twist joints for smooth twist distribution.

        Twist joints are children of skin joints and inherit 100% of the
        parent's rotation.  To make twist_i sit at *fraction* of the full
        twist we apply:  twist.rx = drv.rx * (fraction - 1.0)
        Fraction attributes are exposed on RootX_M for runtime tuning.
        """
        root_ctrl = "RootX_M"
        if not cmds.objExists(root_ctrl):
            return

        twist_segs = [
            ("shoulder", "UpperArm"),
            ("elbow",    "LowerArm"),
            ("hip",      "UpperLeg"),
            ("knee",     "LowerLeg"),
        ]

        has_sep = False
        for s in ("l", "r"):
            S = s.upper()
            for slot_base, label in twist_segs:
                slot = slot_base + "_" + s
                skin_jnt = self.m.get(slot, "")
                drv_jnt = self.dj.get(slot)
                if not skin_jnt or not drv_jnt or not cmds.objExists(skin_jnt):
                    continue

                children = cmds.listRelatives(skin_jnt, c=1, type="joint") or []
                twist_jnts = sorted([c for c in children if "twist" in c.lower()])
                if not twist_jnts:
                    continue

                if not has_sep:
                    cmds.addAttr(root_ctrl, ln="__twist__", nn="--- Twist ---",
                                 at="enum", en=" ", k=1)
                    cmds.setAttr(root_ctrl + ".__twist__", l=1)
                    has_sep = True

                n = len(twist_jnts)
                for i, tj in enumerate(twist_jnts):
                    frac = (n - i) / float(n + 1)

                    attr_name = "twist{}_{}{}".format(label, S, i)
                    cmds.addAttr(root_ctrl, ln=attr_name, at="float",
                                 min=0, max=1, dv=frac, k=1)

                    # PMA: fraction - 1.0
                    pma = cmds.createNode("plusMinusAverage",
                        n="twistSub_{}_{}{}".format(label, S, i))
                    cmds.setAttr(pma + ".operation", 2)  # subtract
                    cmds.connectAttr(root_ctrl + "." + attr_name,
                                     pma + ".input1D[0]")
                    cmds.setAttr(pma + ".input1D[1]", 1.0)

                    # MD: drv.rx * (fraction - 1) -> twist.rx
                    md = cmds.createNode("multiplyDivide",
                        n="twistMul_{}_{}{}".format(label, S, i))
                    cmds.connectAttr(drv_jnt + ".rx", md + ".input1X")
                    cmds.connectAttr(pma + ".output1D", md + ".input2X")
                    cmds.connectAttr(md + ".outputX", tj + ".rx")

                    self.twist_nodes.extend([pma, md])
                    self.bind_pose[tj] = {
                        "t": list(cmds.getAttr(tj + ".t")[0]),
                        "r": list(cmds.getAttr(tj + ".r")[0]),
                        "s": list(cmds.getAttr(tj + ".s")[0]),
                    }

    # ----- Root / Hip controls ---------------------------------------------
    def _ctrl_root(self):
        dj = self.dj.get("root")
        if not dj: return
        c = _circle("RootX_M", r=self.sz*8)
        _snap(c, dj); _color(c, COL_M)
        cmds.xform(c, ws=1, ro=(0,0,0))  # keep horizontal
        o = _offset(c); cmds.parent(o, self.ctrl_grp)
        cmds.pointConstraint(c, dj, mo=1)

        h = _circle("HipSwinger_M", r=self.sz*5)
        _snap(h, dj); _color(h, COL_M)
        cmds.xform(h, ws=1, ro=(0,0,0))  # keep horizontal
        ho = _offset(h); cmds.parent(ho, c)
        cmds.orientConstraint(h, dj, mo=1)

    # ----- FK spine --------------------------------------------------------
    def _ctrl_fk_spine(self):
        par = "RootX_M" if cmds.objExists("RootX_M") else self.ctrl_grp
        for slot in ["spine","chest","neck","head"]:
            dj = self.dj.get(slot)
            if not dj: continue
            c = _circle(SLOT_TO_CTRL[slot], r=self.sz*8)
            _snap(c, dj); _color(c, COL_M)
            cmds.xform(c, ws=1, ro=(0,0,0))  # keep horizontal
            o = _offset(c)
            cmds.parent(o, par if cmds.objExists(par) else self.ctrl_grp)
            cmds.orientConstraint(c, dj, mo=1)
            par = c

    # ----- FK arm ----------------------------------------------------------
    def _ctrl_fk_arm(self, side):
        s = side.lower(); col = _side_color(side)
        ik_too = self.opts.get("create_ik_arms", False)
        ik_slots = {"shoulder_"+s, "elbow_"+s}
        par = "FKChest_M" if cmds.objExists("FKChest_M") else self.ctrl_grp
        chain = [("scapula_"+s, "FKScapula_"+side),
                 ("shoulder_"+s,"FKShoulder_"+side),
                 ("elbow_"+s,   "FKElbow_"+side),
                 ("wrist_"+s,   "FKWrist_"+side)]
        n = len(chain)
        for i, (slot, ctrl_name) in enumerate(chain):
            dj = self.dj.get(slot)
            if not dj: continue
            r = self.sz * 2.5 * (self.taper ** (n-1-i))
            c = _circle(ctrl_name, r=r, n=(1,0,0))
            _snap(c, dj); _color(c, col)
            o = _offset(c)
            cmds.parent(o, par if cmds.objExists(par) else self.ctrl_grp)
            self.fk_offsets[slot] = o
            con = cmds.orientConstraint(c, dj, mo=1)[0]
            self.fk_con[slot] = con
            if ik_too and slot in ik_slots:
                w = cmds.orientConstraint(con, q=1, wal=1)
                if w: cmds.setAttr("{}.{}".format(con, w[0]), 0)
            par = c

    # ----- FK leg ----------------------------------------------------------
    def _ctrl_fk_leg(self, side):
        s = side.lower(); col = _side_color(side)
        ik_too = self.opts.get("create_ik_legs", False)
        par = "RootX_M" if cmds.objExists("RootX_M") else self.ctrl_grp
        chain = [("hip_"+s, "FKHip_"+side),
                 ("knee_"+s,"FKKnee_"+side),
                 ("foot_"+s,"FKFoot_"+side),
                 ("toe_"+s, "FKToe_"+side)]
        n = len(chain)
        for i, (slot, ctrl_name) in enumerate(chain):
            dj = self.dj.get(slot)
            if not dj: continue
            r = self.sz * 2.5 * (self.taper ** (n-1-i))
            c = _circle(ctrl_name, r=r, n=(1,0,0))
            _snap(c, dj); _color(c, col)
            o = _offset(c)
            cmds.parent(o, par if cmds.objExists(par) else self.ctrl_grp)
            self.fk_offsets[slot] = o
            con = cmds.orientConstraint(c, dj, mo=1)[0]
            self.fk_con[slot] = con
            if ik_too and slot in ("hip_"+s, "knee_"+s):
                w = cmds.orientConstraint(con, q=1, wal=1)
                if w: cmds.setAttr("{}.{}".format(con, w[0]), 0)
            par = c

    # ----- IK leg ----------------------------------------------------------
    def _ctrl_ik_leg(self, side):
        s = side.lower()
        hip, knee, foot = [self.dj.get(k+"_"+s) for k in ("hip","knee","foot")]
        if not all([hip, knee, foot]): return

        # IK control at DRIVER foot position
        c = _box("IKLeg_"+side, sz=self.sz*4)
        cmds.xform(c, ws=1, t=_pos(foot))
        cmds.xform(c, ws=1, ro=(0,0,0))
        foot_y = _pos(foot)[1]
        _shift_cvs(c, dy=-foot_y)
        _color(c, COL_IK if side=="L" else COL_R)
        o = _offset(c); cmds.parent(o, self.ctrl_grp)
        ik_key = "Leg_"+side
        self.ik_offsets.setdefault(ik_key, []).append(o)

        ikh, _ = cmds.ikHandle(n="ikh_Leg_"+side, sj=hip, ee=foot, sol="ikRPsolver")

        # --- Reverse Foot Roll ---
        toe_dj = self.dj.get("toe_"+s)
        if toe_dj:
            foot_p = _pos(foot)
            toe_p  = _pos(toe_dj)
            # Heel / toe-tip positions from locators or defaults
            heel_loc   = "footRoll_heel_"+side
            toetip_loc = "footRoll_toetip_"+side
            heel_p   = _pos(heel_loc)   if cmds.objExists(heel_loc)   else [foot_p[0], 0, foot_p[2] - self.sz*5]
            toetip_p = _pos(toetip_loc) if cmds.objExists(toetip_loc) else [toe_p[0],  0, toe_p[2]  + self.sz*5]
            ball_p   = [toe_p[0], 0, toe_p[2]]

            # Follow group — tracks IK control position + rotation
            foot_follow = cmds.group(em=1, n="footFollow_"+side, p=self.ik_grp)
            cmds.xform(foot_follow, ws=1, t=_pos(foot))
            cmds.parentConstraint(c, foot_follow, mo=1)

            # Reverse hierarchy: heel → toetip → ball → [ik handle]
            heel_grp   = cmds.group(em=1, n="heelPiv_"+side,   p=foot_follow)
            cmds.xform(heel_grp, ws=1, t=heel_p)
            toetip_grp = cmds.group(em=1, n="toetipPiv_"+side, p=heel_grp)
            cmds.xform(toetip_grp, ws=1, t=toetip_p)
            ball_grp   = cmds.group(em=1, n="ballPiv_"+side,   p=toetip_grp)
            cmds.xform(ball_grp, ws=1, t=ball_p)

            cmds.parent(ikh, ball_grp)

            # IK orient targets — drive foot/toe via orient constraints
            # (no IK solver on foot/toe — avoids conflict with FK constraints)
            ik_orient_foot = cmds.group(em=1, n="ikOrientFoot_"+side, p=ball_grp)
            cmds.xform(ik_orient_foot, ws=1, ro=cmds.xform(foot, q=1, ws=1, ro=1))
            ik_orient_toe = cmds.group(em=1, n="ikOrientToe_"+side, p=toetip_grp)
            cmds.xform(ik_orient_toe, ws=1, ro=cmds.xform(toe_dj, q=1, ws=1, ro=1))

            # Add IK orient as second target to existing FK orient constraints
            fc_foot = self.fk_con.get("foot_"+s)
            if fc_foot:
                cmds.orientConstraint(ik_orient_foot, foot, e=1, mo=1)
                w = cmds.orientConstraint(fc_foot, q=1, wal=1)
                if len(w) >= 2:
                    cmds.setAttr("{}.{}".format(fc_foot, w[0]), 0)   # FK off
                    cmds.setAttr("{}.{}".format(fc_foot, w[1]), 1)   # IK on

            fc_toe = self.fk_con.get("toe_"+s)
            if fc_toe:
                cmds.orientConstraint(ik_orient_toe, toe_dj, e=1, mo=1)
                w = cmds.orientConstraint(fc_toe, q=1, wal=1)
                if len(w) >= 2:
                    cmds.setAttr("{}.{}".format(fc_toe, w[0]), 0)
                    cmds.setAttr("{}.{}".format(fc_toe, w[1]), 1)

            # Roll attributes
            start = self.opts.get("roll_start_angle", 30)
            end   = self.opts.get("roll_end_angle", 60)
            cmds.addAttr(c, ln="Roll",           at="float", dv=0,     k=1)
            cmds.addAttr(c, ln="RollStartAngle", at="float", dv=start, k=1)
            cmds.addAttr(c, ln="RollEndAngle",   at="float", dv=end,   k=1)

            # Expression-driven foot roll (respects dynamic RollStartAngle/RollEndAngle)
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
            cmds.expression(n="footRoll_expr_"+side, s=expr_str, ae=1)
        else:
            cmds.parent(ikh, self.ik_grp)
            cmds.pointConstraint(c, ikh)
            # No SC solver — orient foot via FK control routing
            fk_foot = SLOT_TO_CTRL.get("foot_"+s)
            if fk_foot and cmds.objExists(fk_foot):
                oc = cmds.orientConstraint(c, fk_foot, mo=1)[0]
                w = cmds.orientConstraint(oc, q=1, wal=1)
                if w: cmds.setAttr("{}.{}".format(oc, w[0]), 0)
                self.ik_fk_oc["foot_"+s] = oc

        # Pole vector — knees forward (+Z)
        pole = cmds.spaceLocator(n="PoleLeg_"+side)[0]
        cmds.xform(pole, ws=1, t=_pole_pos(knee, self.sz*20, (0,0,1)))
        _color(pole, COL_POLE)
        po = _offset(pole); cmds.parent(po, self.ctrl_grp)
        self.ik_offsets[ik_key].append(po)
        cmds.poleVectorConstraint(pole, ikh)

    # ----- IK arm ----------------------------------------------------------
    def _ctrl_ik_arm(self, side):
        s = side.lower()
        sho, elb, wri = [self.dj.get(k+"_"+s) for k in ("shoulder","elbow","wrist")]
        if not all([sho, elb, wri]): return

        # IK control at DRIVER wrist position, oriented along the arm chain
        c = _box("IKArm_"+side, sz=self.sz*5)
        cmds.xform(c, ws=1, t=_pos(wri))
        # Orient controller to follow arm direction (shoulder→elbow→wrist)
        sho_p, elb_p, wri_p = _pos(sho), _pos(elb), _pos(wri)
        arm = [wri_p[i] - sho_p[i] for i in range(3)]
        se  = [elb_p[i] - sho_p[i] for i in range(3)]
        up  = [arm[1]*se[2] - arm[2]*se[1],
               arm[2]*se[0] - arm[0]*se[2],
               arm[0]*se[1] - arm[1]*se[0]]
        _tmp = cmds.spaceLocator()[0]
        cmds.xform(_tmp, ws=1, t=sho_p)
        _ac = cmds.aimConstraint(_tmp, c, aim=(0, 1, 0), u=(0, 0, 1),
                                 wut="vector", wu=up)[0]
        cmds.delete(_ac, _tmp)
        # Shift box shape to sit past wrist (on top of hand)
        _shift_cvs(c, dy=-self.sz*5)
        _color(c, COL_IK if side=="L" else COL_R)
        o = _offset(c); cmds.parent(o, self.ctrl_grp)
        ik_key = "Arm_"+side
        self.ik_offsets.setdefault(ik_key, []).append(o)

        ikh, _ = cmds.ikHandle(n="ikh_Arm_"+side, sj=sho, ee=wri, sol="ikRPsolver")
        cmds.parent(ikh, self.ik_grp)
        cmds.pointConstraint(c, ikh)  # zero offset — both at driver wrist

        # Pole vector — elbows backward (-Z)
        pole = cmds.spaceLocator(n="PoleArm_"+side)[0]
        cmds.xform(pole, ws=1, t=_pole_pos(elb, self.sz*20, (0,0,-1)))
        _color(pole, COL_POLE)
        po = _offset(pole); cmds.parent(po, self.ctrl_grp)
        self.ik_offsets[ik_key].append(po)
        cmds.poleVectorConstraint(pole, ikh)

        # IK control drives wrist orientation via FK control
        fk_wrist = SLOT_TO_CTRL.get("wrist_"+s)
        if fk_wrist and cmds.objExists(fk_wrist):
            oc = cmds.orientConstraint(c, fk_wrist, mo=1)[0]
            w = cmds.orientConstraint(oc, q=1, wal=1)
            if w: cmds.setAttr("{}.{}".format(oc, w[0]), 0)
            self.ik_fk_oc["wrist_"+s] = oc

    # ----- FK/IK blend switch ----------------------------------------------
    def _ctrl_fkik(self, limb, side):
        s = side.lower()
        end_slot = ("foot_" if limb=="Leg" else "wrist_") + s
        ref = self.dj.get(end_slot)
        if not ref: return

        c = _diamond("FKIK{}_{}".format(limb, side), sz=self.sz*2)
        ref_p = _pos(ref)
        sign = 1 if ref_p[0] > 0 else -1
        if limb == "Leg":
            # Position on the leg's own side, offset slightly outward from foot
            cmds.xform(c, ws=1, t=(ref_p[0] + self.sz*4*sign, ref_p[1], ref_p[2]))
        else:
            # Position above the shoulder, offset outward
            sho = self.dj.get("shoulder_"+s)
            sho_p = _pos(sho) if sho else ref_p
            sign = 1 if sho_p[0] > 0 else -1
            cmds.xform(c, ws=1, t=(sho_p[0] + self.sz*5*sign,
                                    sho_p[1] + self.sz*8, sho_p[2]))
        _color(c, _side_color(side))
        o = _offset(c); cmds.parent(o, self.ctrl_grp)

        cmds.addAttr(c, ln="FKIKBlend", at="float", min=0, max=10, dv=10, k=1)

        # norm = blend / 10
        norm = cmds.createNode("multiplyDivide", n="fkikN_{}_{}".format(limb, side))
        cmds.setAttr(norm+".operation", 2)
        cmds.connectAttr(c+".FKIKBlend", norm+".input1X")
        cmds.setAttr(norm+".input2X", 10)

        # reverse = 1 - norm
        rev = cmds.createNode("reverse", n="fkikR_{}_{}".format(limb, side))
        cmds.connectAttr(norm+".outputX", rev+".inputX")

        # Drive IK blend
        ikh = "ikh_{}_{}".format(limb, side)
        if cmds.objExists(ikh):
            cmds.connectAttr(norm+".outputX", ikh+".ikBlend")
        # FK chain slots — single-target FK constraints (hip/knee or shoulder/elbow)
        if limb == "Leg":
            fk_slots = ["hip_"+s, "knee_"+s]
        else:
            fk_slots = ["shoulder_"+s, "elbow_"+s]

        for sl in fk_slots:
            fc = self.fk_con.get(sl)
            if not fc or not cmds.objExists(fc): continue
            w = cmds.orientConstraint(fc, q=1, wal=1)
            if w: cmds.connectAttr(rev+".outputX", "{}.{}".format(fc, w[0]))

        # Blend dual-target foot/toe orient constraints (FK vs IK orient groups)
        if limb == "Leg":
            for sl in ["foot_"+s, "toe_"+s]:
                fc = self.fk_con.get(sl)
                if not fc or not cmds.objExists(fc): continue
                w = cmds.orientConstraint(fc, q=1, wal=1)
                if len(w) >= 2:
                    # w[0]=FK target, w[1]=IK orient target
                    cmds.connectAttr(rev+".outputX", "{}.{}".format(fc, w[0]))
                    cmds.connectAttr(norm+".outputX", "{}.{}".format(fc, w[1]))
                elif w:
                    cmds.connectAttr(rev+".outputX", "{}.{}".format(fc, w[0]))

        # End effector: blend IK-drives-FK-control constraint
        end_slot = ("foot_" if limb=="Leg" else "wrist_") + s
        ik_fk_oc = self.ik_fk_oc.get(end_slot)
        if ik_fk_oc and cmds.objExists(ik_fk_oc):
            w = cmds.orientConstraint(ik_fk_oc, q=1, wal=1)
            if w: cmds.connectAttr(norm+".outputX", "{}.{}".format(ik_fk_oc, w[0]))

        # --- Visibility: hide unused controls at slider extremes ---
        # FK visible when blend < 10 (norm < 1)
        fk_vis = cmds.createNode("condition", n="fkVis_{}_{}".format(limb, side))
        cmds.connectAttr(norm+".outputX", fk_vis+".firstTerm")
        cmds.setAttr(fk_vis+".secondTerm", 1)
        cmds.setAttr(fk_vis+".operation", 4)  # less than
        cmds.setAttr(fk_vis+".colorIfTrueR", 1)
        cmds.setAttr(fk_vis+".colorIfFalseR", 0)

        # IK visible when blend > 0 (norm > 0)
        ik_vis = cmds.createNode("condition", n="ikVis_{}_{}".format(limb, side))
        cmds.connectAttr(norm+".outputX", ik_vis+".firstTerm")
        cmds.setAttr(ik_vis+".secondTerm", 0)
        cmds.setAttr(ik_vis+".operation", 2)  # greater than
        cmds.setAttr(ik_vis+".colorIfTrueR", 1)
        cmds.setAttr(ik_vis+".colorIfFalseR", 0)

        # Hide FK offsets
        if limb == "Leg":
            vis_fk = ["hip_"+s, "knee_"+s, "foot_"+s, "toe_"+s]
        else:
            vis_fk = ["scapula_"+s, "shoulder_"+s, "elbow_"+s, "wrist_"+s]
        for sl in vis_fk:
            off = self.fk_offsets.get(sl)
            if off and cmds.objExists(off):
                cmds.connectAttr(fk_vis+".outColorR", off+".v")

        # Hide IK offsets (ctrl + pole)
        ik_key = "{}_{}".format(limb, side)
        for off in self.ik_offsets.get(ik_key, []):
            if cmds.objExists(off):
                cmds.connectAttr(ik_vis+".outColorR", off+".v")



# ---------------------------------------------------------------------------
# Remove
# ---------------------------------------------------------------------------
def remove_control_rig():
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found."); return

    # Read stored data before deleting anything
    bind_pose = {}
    if cmds.attributeQuery("bind_pose", node=RIG_GRP, exists=True):
        try:
            bind_pose = json.loads(cmds.getAttr(RIG_GRP+".bind_pose"))
        except Exception:
            pass

    # Delete constraints on skin joints first (stored on the rig group)
    if cmds.attributeQuery("skin_constraints", node=RIG_GRP, exists=True):
        try:
            names = json.loads(cmds.getAttr(RIG_GRP+".skin_constraints"))
            for n in names:
                if cmds.objExists(n): cmds.delete(n)
        except Exception:
            pass

    # Delete twist utility nodes (DG nodes, not parented under rig group)
    if cmds.attributeQuery("twist_nodes", node=RIG_GRP, exists=True):
        try:
            nodes = json.loads(cmds.getAttr(RIG_GRP+".twist_nodes"))
            for n in nodes:
                if cmds.objExists(n): cmds.delete(n)
        except Exception:
            pass

    cmds.delete(RIG_GRP)

    # Restore original bind pose
    for jnt, xf in bind_pose.items():
        if not cmds.objExists(jnt):
            continue
        try:
            cmds.setAttr(jnt+".t", *xf["t"])
            cmds.setAttr(jnt+".r", *xf["r"])
            cmds.setAttr(jnt+".s", *xf["s"])
        except Exception:
            pass

    print("// AutoControlRig removed — bind pose restored.")


# ---------------------------------------------------------------------------
# Post-Rig utilities
# ---------------------------------------------------------------------------
def reset_to_bind_pose():
    """Zero out all rig controls, returning the character to bind pose."""
    if not cmds.objExists(RIG_GRP):
        cmds.warning("No rig found."); return
    ctrl_grp = "Ctrl_GRP"
    if not cmds.objExists(ctrl_grp):
        cmds.warning("Ctrl_GRP not found."); return
    ctrls = cmds.listRelatives(ctrl_grp, ad=1, type="transform", f=1) or []
    for c in ctrls:
        # Skip offset groups (only reset actual controls with shapes or user attrs)
        shapes = cmds.listRelatives(c, s=1) or []
        if not shapes:
            continue
        for attr in ("tx","ty","tz","rx","ry","rz"):
            try:
                if not cmds.getAttr(c+"."+attr, l=1):
                    cmds.setAttr(c+"."+attr, 0)
            except Exception:
                pass
        for attr in ("sx","sy","sz"):
            try:
                if not cmds.getAttr(c+"."+attr, l=1):
                    cmds.setAttr(c+"."+attr, 1)
            except Exception:
                pass
        # Reset custom attrs (FKIKBlend, Roll) to default
        ud = cmds.listAttr(c, ud=1, k=1) or []
        for attr in ud:
            try:
                dv = cmds.addAttr(c+"."+attr, q=1, dv=1)
                cmds.setAttr(c+"."+attr, dv)
            except Exception:
                pass
    cmds.select(cl=1)
    print("// All controls reset to bind pose.")


def _create_foot_roll_locators(*a):
    """Create heel / toe-tip locators at default positions for reverse foot setup."""
    mapping = _read_map()
    created = 0
    for s, S in [("l","L"), ("r","R")]:
        foot_jnt = mapping.get("foot_"+s, "")
        toe_jnt  = mapping.get("toe_"+s, "")
        if not foot_jnt or not cmds.objExists(foot_jnt):
            continue
        fp = _pos(foot_jnt)
        heel_n = "footRoll_heel_"+S
        if not cmds.objExists(heel_n):
            h = cmds.spaceLocator(n=heel_n)[0]
            cmds.xform(h, ws=1, t=[fp[0], 0, fp[2] - 5])
            _color(h, _side_color(S))
            created += 1
        toetip_n = "footRoll_toetip_"+S
        if not cmds.objExists(toetip_n):
            t = cmds.spaceLocator(n=toetip_n)[0]
            if toe_jnt and cmds.objExists(toe_jnt):
                tp = _pos(toe_jnt)
                cmds.xform(t, ws=1, t=[tp[0], 0, tp[2] + 5])
            else:
                cmds.xform(t, ws=1, t=[fp[0], 0, fp[2] + 15])
            _color(t, _side_color(S))
            created += 1
    if created:
        print("// Created {} foot roll locator(s). Adjust positions as needed.".format(created))
    else:
        print("// Foot roll locators already exist or no foot joints mapped.")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
_ui = {"win":"AutoCtrlRigWin", "joints":[], "fields":{}, "labels":{}, "root":None}

try:
    _PRESET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "joint_mappings")
except NameError:
    _PRESET_DIR = os.path.join(cmds.workspace(q=1, rd=1), "joint_mappings")


def _color_labels():
    for k, lbl in _ui["labels"].items():
        v = cmds.optionMenu(_ui["fields"][k], q=1, v=1)
        bg = (0.8,0.3,0.3) if v == "(none)" else (0.36,0.36,0.36)
        cmds.text(lbl, e=1, bgc=bg)

def _on_root(*a):
    sel = cmds.ls(sl=1, type="joint")
    if not sel: cmds.warning("Select a root joint."); return
    cmds.textField(_ui["root"], e=1, tx=sel[0])
    _ui["joints"] = get_hierarchy_joints(sel[0])
    _fill_menus()

def _on_sel(slot, *a):
    sel = cmds.ls(sl=1, type="joint")
    if not sel: return
    menu = _ui["fields"].get(slot)
    if not menu: return
    items = [cmds.menuItem(i, q=1, l=1) for i in (cmds.optionMenu(menu, q=1, ill=1) or [])]
    if sel[0] not in items:
        cmds.menuItem(l=sel[0], p=menu)
    cmds.optionMenu(menu, e=1, v=sel[0])
    _color_labels()

def _on_auto(*a):
    if not _ui["joints"]: cmds.warning("Load a root joint first."); return
    mp = auto_map_joints(_ui["joints"])
    for k, j in mp.items():
        menu = _ui["fields"].get(k)
        if menu and j:
            try: cmds.optionMenu(menu, e=1, v=j)
            except: pass
    _color_labels()

def _fill_menus():
    jts = ["(none)"] + sorted(_ui["joints"])
    for k, menu in _ui["fields"].items():
        for i in (cmds.optionMenu(menu, q=1, ill=1) or []): cmds.deleteUI(i)
        for j in jts: cmds.menuItem(l=j, p=menu)
    _color_labels()

def _read_map():
    return {k: ("" if cmds.optionMenu(m, q=1, v=1)=="(none)" else cmds.optionMenu(m, q=1, v=1))
            for k, m in _ui["fields"].items()}

def _on_build(*a):
    opts = {
        "control_size": cmds.floatField(_ui["sz"], q=1, v=1),
        "create_ik_legs": cmds.checkBox(_ui["ik_l"], q=1, v=1),
        "create_ik_arms": cmds.checkBox(_ui["ik_a"], q=1, v=1),
        "create_fk_arms": cmds.checkBox(_ui["fk_a"], q=1, v=1),
        "create_fk_legs": cmds.checkBox(_ui["fk_l"], q=1, v=1),
        "create_fkik_blend": cmds.checkBox(_ui["fkik"], q=1, v=1),
        "scale_taper": cmds.floatField(_ui["taper"], q=1, v=1),
        "show_debug": cmds.checkBox(_ui["dbg"], q=1, v=1),
        "create_twist_drivers": cmds.checkBox(_ui["twist"], q=1, v=1),
        "roll_start_angle": cmds.floatField(_ui["roll_start"], q=1, v=1),
        "roll_end_angle": cmds.floatField(_ui["roll_end"], q=1, v=1),
    }
    AutoControlRigBuilder(_read_map(), opts).build()

def _on_save(*a):
    if not os.path.exists(_PRESET_DIR): os.makedirs(_PRESET_DIR)
    r = cmds.fileDialog2(cap="Save Mapping", ff="JSON (*.json)", ds=2, fm=0, dir=_PRESET_DIR)
    if not r: return
    data = {"root": cmds.textField(_ui["root"], q=1, tx=1), "mapping": _read_map()}
    with open(r[0], "w") as f: json.dump(data, f, indent=2)
    print("// Saved:", r[0])

def _on_load(*a):
    sd = _PRESET_DIR if os.path.exists(_PRESET_DIR) else ""
    r = cmds.fileDialog2(cap="Load Mapping", ff="JSON (*.json)", ds=2, fm=1, dir=sd)
    if not r: return
    with open(r[0]) as f: data = json.load(f)
    rj = data.get("root","")
    if rj and cmds.objExists(rj):
        cmds.textField(_ui["root"], e=1, tx=rj)
        _ui["joints"] = get_hierarchy_joints(rj)
        _fill_menus()
    for k, j in data.get("mapping",{}).items():
        menu = _ui["fields"].get(k)
        if menu and j:
            items = [cmds.menuItem(i, q=1, l=1) for i in (cmds.optionMenu(menu, q=1, ill=1) or [])]
            if j not in items: cmds.menuItem(l=j, p=menu)
            try: cmds.optionMenu(menu, e=1, v=j)
            except: pass
    _color_labels()
    print("// Loaded:", r[0])


def show():
    w = _ui["win"]
    if cmds.window(w, ex=1): cmds.deleteUI(w)
    cmds.window(w, t="Auto Control Rig", wh=(520,700), s=1)
    cmds.scrollLayout(cr=1)
    cmds.columnLayout(adj=1, rs=6)

    cmds.frameLayout(l="Joint Hierarchy", cll=0, mw=10, mh=5)
    cmds.rowLayout(nc=3, cw3=(60,300,100), adj=2)
    cmds.text(l="Root:")
    _ui["root"] = cmds.textField(pht="Select root joint...")
    cmds.button(l="From Selection", c=_on_root)
    cmds.setParent(".."); cmds.button(l="Auto-Map", c=_on_auto, h=28)
    cmds.rowLayout(nc=2, cw2=(200,200), adj=2)
    cmds.button(l="Save Mapping", c=_on_save)
    cmds.button(l="Load Mapping", c=_on_load)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.frameLayout(l="Joint Mapping", cll=1, mw=10, mh=5)
    _ui["fields"], _ui["labels"] = {}, {}
    for key, name, side, _ in SLOT_DEFS:
        cmds.rowLayout(nc=3, cw3=(160,240,80), adj=2)
        tag = {"L":" [L]","R":" [R]","M":""}[side]
        _ui["labels"][key] = cmds.text(l=name+tag, al="right", bgc=(0.8,0.3,0.3))
        _ui["fields"][key] = cmds.optionMenu(cc=lambda *a: _color_labels())
        cmds.menuItem(l="(none)")
        cmds.button(l="< Sel", c=lambda x, k=key: _on_sel(k))
        cmds.setParent("..")
    cmds.separator(h=6, st="in")
    cmds.button(l="Create Foot Roll Locators", h=28, bgc=(0.6,0.6,0.8),
                c=lambda *a: _create_foot_roll_locators())
    cmds.setParent("..")

    cmds.frameLayout(l="Options", cll=1, mw=10, mh=5)
    cmds.rowColumnLayout(nc=2, cw=[(1,200),(2,200)])
    _ui["ik_l"] = cmds.checkBox(l="IK Legs", v=1)
    _ui["ik_a"] = cmds.checkBox(l="IK Arms", v=1)
    _ui["fk_a"] = cmds.checkBox(l="FK Arms", v=1)
    _ui["fk_l"] = cmds.checkBox(l="FK Legs", v=1)
    _ui["fkik"] = cmds.checkBox(l="FK/IK Blend", v=1)
    _ui["twist"] = cmds.checkBox(l="Twist Joints", v=1)
    _ui["dbg"]  = cmds.checkBox(l="Show Debug", v=0)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130,100))
    cmds.text(l="Control Size:")
    _ui["sz"] = cmds.floatField(v=1, min=0.1, max=100)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130,100))
    cmds.text(l="Scale Taper:")
    _ui["taper"] = cmds.floatField(v=1.3, min=1.0, max=3.0)
    cmds.setParent("..")
    cmds.separator(h=6, st="in")
    cmds.text(l="IK Foot Roll:", fn="boldLabelFont")
    cmds.rowLayout(nc=2, cw2=(130,100))
    cmds.text(l="Roll Start Angle:")
    _ui["roll_start"] = cmds.floatField(v=30, min=0, max=90)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130,100))
    cmds.text(l="Roll End Angle:")
    _ui["roll_end"] = cmds.floatField(v=60, min=0, max=120)
    cmds.setParent(".."); cmds.setParent("..")

    cmds.separator(h=10, st="in")
    cmds.button(l="Build Control Rig", h=40, bgc=(0.4,0.8,0.4), c=_on_build)
    cmds.button(l="Remove Control Rig", h=32, bgc=(0.9,0.4,0.4), c=lambda *a: remove_control_rig())
    cmds.separator(h=10, st="in")

    cmds.frameLayout(l="Post Rig", cll=1, mw=10, mh=5)
    cmds.button(l="Return to Bind Pose", h=32, bgc=(0.5,0.7,1.0),
                c=lambda *a: reset_to_bind_pose())
    cmds.setParent("..")

    cmds.showWindow(w)

if __name__ == "__main__":
    show()
