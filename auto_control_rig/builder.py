import maya.cmds as cmds
import json

from .constants import RIG_GRP, COL_IK, COL_M, COL_POLE
from .utils import color
from . import skeleton
from . import controls
from . import twist
from . import helpers


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
        self.m = mapping
        self.opts = opts
        self.sz = opts.get("control_size", 1.0)
        self.taper = opts.get("scale_taper", 1.3)
        self.dj = {}
        self.fk_con = {}
        self.ik_con = {}
        self.fk_offsets = {}
        self.ik_offsets = {}
        self.ik_fk_oc = {}
        self.skin_constraints = []
        self.twist_nodes = []
        self.bind_pose = {}

    def build(self):
        if cmds.objExists(RIG_GRP):
            cmds.warning("Rig exists — remove it first.")
            return

        # Top groups
        self.top = cmds.group(em=1, n=RIG_GRP)
        self.ctrl_grp = cmds.group(em=1, n="Ctrl_GRP", p=self.top)
        self.drv_grp = cmds.group(em=1, n="Driver_GRP", p=self.top)
        self.ik_grp = cmds.group(em=1, n="IK_GRP", p=self.top)
        self.misc_grp = cmds.group(em=1, n="Misc_GRP", p=self.top)
        cmds.setAttr(self.ik_grp + ".v", 0)
        cmds.setAttr(self.misc_grp + ".v", 0)

        # 1) Driver skeleton
        skeleton.build_driver_skeleton(self)

        # 2) Controls
        controls.build_root(self)
        controls.build_fk_spine(self)
        for s in "LR":
            if self.opts.get("create_fk_arms", True):
                controls.build_fk_arm(self, s)
            if self.opts.get("create_fk_legs", True):
                controls.build_fk_leg(self, s)
            if self.opts.get("create_ik_legs", True):
                controls.build_ik_leg(self, s)
            if self.opts.get("create_ik_arms", True):
                controls.build_ik_arm(self, s)
        for s in "LR":
            if self.opts.get("create_fkik_blend", True):
                if self.opts.get("create_ik_legs") and self.opts.get("create_fk_legs"):
                    controls.build_fkik(self, "Leg", s)
                if self.opts.get("create_ik_arms") and self.opts.get("create_fk_arms"):
                    controls.build_fkik(self, "Arm", s)

        # 3) Bind skin joints to driver
        self._bind_skin()

        # 3.25) Twist joint drivers
        if self.opts.get("create_twist_drivers", True):
            twist.setup_twist_joints(self)

        # 3.35) Helper joint correctives (elbow/knee)
        helpers.setup_helper_joints(self)

        # 3.5) Debug visualization
        if self.opts.get("show_debug", False):
            self._create_debug_vis()

        # 4) Store data for clean removal
        cmds.addAttr(self.top, ln="skin_constraints", dt="string")
        cmds.setAttr(self.top + ".skin_constraints",
                     json.dumps(self.skin_constraints), type="string")
        cmds.addAttr(self.top, ln="twist_nodes", dt="string")
        cmds.setAttr(self.top + ".twist_nodes",
                     json.dumps(self.twist_nodes), type="string")
        cmds.addAttr(self.top, ln="bind_pose", dt="string")
        cmds.setAttr(self.top + ".bind_pose",
                     json.dumps(self.bind_pose), type="string")

        cmds.select(cl=1)
        print("// AutoControlRig built.")

    def _bind_skin(self):
        for slot, dj in self.dj.items():
            skin = self.m.get(slot, "")
            if skin and cmds.objExists(skin):
                self.bind_pose[skin] = {
                    "t": list(cmds.getAttr(skin + ".t")[0]),
                    "r": list(cmds.getAttr(skin + ".r")[0]),
                    "s": list(cmds.getAttr(skin + ".s")[0]),
                }
                c = cmds.parentConstraint(dj, skin, mo=1)[0]
                self.skin_constraints.append(c)

    def _create_debug_vis(self):
        dbg = cmds.group(em=1, n="Debug_GRP", p=self.top)
        lsz = self.sz * 3
        for slot, dj in self.dj.items():
            loc = cmds.spaceLocator(n="dbg_" + slot)[0]
            for ax in ("X", "Y", "Z"):
                cmds.setAttr(loc + ".localScale" + ax, lsz)
            cmds.parentConstraint(dj, loc, mo=0)
            cmds.parent(loc, dbg)
        for side in ("L", "R"):
            roll_pivots = [
                ("heelPiv_" + side, "dbg_heelPiv_" + side, COL_IK),
                ("ballPiv_" + side, "dbg_ballPiv_" + side, COL_M),
                ("toetipPiv_" + side, "dbg_toetipPiv_" + side, COL_POLE),
            ]
            for grp_name, loc_name, col in roll_pivots:
                if not cmds.objExists(grp_name):
                    continue
                loc = cmds.spaceLocator(n=loc_name)[0]
                for ax in ("X", "Y", "Z"):
                    cmds.setAttr(loc + ".localScale" + ax, lsz)
                color(loc, col)
                cmds.parentConstraint(grp_name, loc, mo=0)
                cmds.parent(loc, dbg)
