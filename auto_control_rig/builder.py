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
    Dual-chain FK/IK architecture:
        FK Controls  -->  FK Driver joints  ──┐
                                               ├─ parentConstraint (blended) --> Skin joints
        IK Handle    -->  IK Driver joints  ──┘
    """

    def __init__(self, mapping, opts):
        self.m = mapping
        self.opts = opts
        self.sz = opts.get("control_size", 1.0)
        self.taper = opts.get("scale_taper", 1.3)
        self.dj = {}
        self.ik_dj = {}
        self.fk_con = {}
        self.ik_con = {}
        self.fk_offsets = {}
        self.ik_offsets = {}
        self.ik_fk_oc = {}
        self.skin_con = {}
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

        # 0) Main controller (parents all groups under itself)
        controls.build_main(self)

        # 1) Driver skeleton (FK)
        skeleton.build_driver_skeleton(self)

        # 1.5) IK driver skeletons (separate chains for IK solving)
        if self.opts.get("create_ik_spine", True):
            skeleton.build_ik_driver_spine(self)
        for s in "lr":
            if self.opts.get("create_ik_arms", True):
                skeleton.build_ik_driver_arm(self, s)
            if self.opts.get("create_ik_legs", True):
                skeleton.build_ik_driver_leg(self, s)

        # 1.6) Finger driver chains (auto-discovered under wrist)
        if self.opts.get("create_fingers", True):
            for s in "LR":
                skeleton.build_finger_drivers(self, s)

        # 2) Controls
        controls.build_root(self)
        controls.build_fk_spine(self)
        if self.opts.get("create_ik_spine", True):
            controls.build_ik_spine(self)
        for s in "LR":
            if self.opts.get("create_fk_arms", True):
                controls.build_fk_arm(self, s)
            if self.opts.get("create_fk_legs", True):
                controls.build_fk_leg(self, s)
            if self.opts.get("create_ik_legs", True):
                controls.build_ik_leg(self, s)
            if self.opts.get("create_ik_arms", True):
                controls.build_ik_arm(self, s)

        # 2.5) Fingers, eyes, eyelids, ears
        if self.opts.get("create_fingers", True):
            for s in "LR":
                controls.build_fk_fingers(self, s)
        if self.opts.get("create_eye_aim", True):
            controls.build_eye_aim(self)
        for s in "LR":
            if self.opts.get("create_eyelids", True):
                controls.build_fk_eyelids(self, s)
            if self.opts.get("create_ears", True):
                controls.build_fk_ears(self, s)

        # 3) Bind skin joints to driver
        self._bind_skin()

        # 3.05) Global scale — propagate Main_M scale to the skin skeleton
        root_skin = self.m.get("root", "")
        main = getattr(self, "main", "Main_M")
        if root_skin and cmds.objExists(root_skin) and cmds.objExists(main):
            sc = cmds.scaleConstraint(main, root_skin, mo=1)[0]
            self.skin_constraints.append(sc)

        # 3.1) FK/IK blend switches (after bind, uses skin constraints)
        if self.opts.get("create_fkik_blend", True):
            if self.opts.get("create_ik_spine", True):
                controls.build_fkik(self, "Spine", "M")
        for s in "LR":
            if self.opts.get("create_fkik_blend", True):
                if self.opts.get("create_ik_legs") and self.opts.get("create_fk_legs"):
                    controls.build_fkik(self, "Leg", s)
                if self.opts.get("create_ik_arms") and self.opts.get("create_fk_arms"):
                    controls.build_fkik(self, "Arm", s)

        # 3.15) Chest follow + IK space switching
        controls.build_spaces(self)

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
        mapped_skins = set(self.m.values())
        for slot, dj in self.dj.items():
            skin = self.m.get(slot, "")
            if not skin or not cmds.objExists(skin):
                continue
            self.bind_pose[skin] = {
                "t": list(cmds.getAttr(skin + ".t")[0]),
                "r": list(cmds.getAttr(skin + ".r")[0]),
                "s": list(cmds.getAttr(skin + ".s")[0]),
            }
            ik_dj = self.ik_dj.get(slot)
            if ik_dj and cmds.objExists(ik_dj):
                # Dual-target: FK driver + IK driver
                c = cmds.parentConstraint(dj, ik_dj, skin, mo=1)[0]
                self.skin_con[slot] = c
                # Default to IK active
                w = cmds.parentConstraint(c, q=1, wal=1)
                if len(w) >= 2:
                    cmds.setAttr("{}.{}".format(c, w[0]), 0)
                    cmds.setAttr("{}.{}".format(c, w[1]), 1)
            else:
                c = cmds.parentConstraint(dj, skin, mo=1)[0]
            self.skin_constraints.append(c)

        # Bind unmapped intermediate joints between consecutive spine slots
        spine_slots = ["spine", "spine_1", "chest", "neck", "head"]
        for i in range(len(spine_slots) - 1):
            lo_slot = spine_slots[i]
            hi_slot = spine_slots[i + 1]
            lo_skin = self.m.get(lo_slot, "")
            hi_skin = self.m.get(hi_slot, "")
            lo_dj = self.dj.get(lo_slot)
            if not lo_skin or not hi_skin or not lo_dj:
                continue
            # Walk down from lo_skin's children toward hi_skin
            cur = lo_skin
            while cur:
                children = cmds.listRelatives(cur, c=1, type="joint") or []
                found = None
                for ch in children:
                    if ch == hi_skin:
                        found = None
                        cur = None
                        break
                    if ch not in mapped_skins:
                        found = ch
                        break
                if cur is None:
                    break
                if found:
                    self.bind_pose[found] = {
                        "t": list(cmds.getAttr(found + ".t")[0]),
                        "r": list(cmds.getAttr(found + ".r")[0]),
                        "s": list(cmds.getAttr(found + ".s")[0]),
                    }
                    c = cmds.parentConstraint(lo_dj, found, mo=1)[0]
                    self.skin_constraints.append(c)
                    cur = found
                else:
                    break

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
