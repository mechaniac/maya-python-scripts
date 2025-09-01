import maya.cmds as cmds
import json

class HandSideStepGenerator:
    def __init__(self):
        self.window = "HandSideStepGeneratorWindow"

        # Direction (mirror only flips directional motion)
        self.mirror = False  # ON => step right, OFF => step left

        # Controls
        self.stretch_arms = False  # if True, key IKArm_*.stretchy=10 at start/end

        self.root = "RootX_M"
        self.hand_r = "IKArm_R"   # stepping limbs
        self.hand_l = "IKArm_L"

        self.hip   = "HipSwinger_M"
        self.spine = "FKSpine1_M"
        self.chest = "FKChest_M"
        self.neck  = "FKNeck_M"
        self.head  = "FKHead_M"

        # FK scapulas (kept)
        self.scapula_l = "FKScapula_L"
        self.scapula_r = "FKScapula_R"
        
        # FK/IK blend controllers for legs
        self.fkik_leg_r = "FKIKLeg_R"
        self.fkik_leg_l = "FKIKLeg_L"
        
        # FK leg joints (pose)
        self.fk_hip_r  = "FKHip_R";  self.fk_hip_l  = "FKHip_L"
        self.fk_knee_r = "FKKnee_R"; self.fk_knee_l = "FKKnee_L"
        self.fk_foot_r = "FKFoot_R"; self.fk_foot_l = "FKFoot_L"
        self.fk_toe_r  = "FKToe_R";  self.fk_toe_l  = "FKToe_L"
        
        # FK/IK blend value (0..10)
        self.leg_fkik_blend = 10.0
                
        # FK pose (rotateZ) for both legs (static at start/end)
        self.fk_hip_rz  = 0.0
        self.fk_knee_rz = 0.0
        self.fk_foot_rz = 0.0
        self.fk_toe_rz  = 0.0

        # Step settings (for hands)
        self.step_width  = 5.0
        self.step_height = 2.0
        self.ground_height = 0.0
        self.step_narrowness = 0.0  # +|n| on R, -|n| on L (all hand X keys)

        # Root motion (fifths + signed offset)
        self.root_tilt     = 5.0       # rotateZ
        self.root_bounce   = 1.0       # translateY (amplitude)
        self.root_offset_y = 0.0       # translateY baseline (signed)

        # Base scapula motion only (shoulder/elbow/wrist are IK-handled)
        self.scapula_swing = 0.0       # rotateY (L/R oppose)

        # SideWhip (torso) — keyed on fifths
        self.hip_sway   = 3.0
        self.spine_sway = 2.0
        self.chest_sway = 1.5
        self.neck_sway  = 1.0
        self.head_sway  = 0.5

        # ABSOLUTE (kept only for scapulas)
        self.down_scapula_y  = 0.0     # add |v| to rotateY
        self.bent_scapula_z  = 0.0     # add |v| to rotateZ
        self.twist_scapula_x = 0.0     # add |v| to rotateX

        self.frames = []

    # ---------- helpers ----------
    def _dir(self):
        return -1 if self.mirror else 1

    def _abs(self, v):
        return abs(float(v))

    def resolve_node_case_insensitive(self, name):
        name_lower = name.lower()
        aliases = {
            'fkscapula1_l': 'fkscapula_l',
            'fkscapula_l':  'fkscapula1_l',
            'fkscapula1_r': 'fkscapula_r',
            'fkscapula_r':  'fkscapula1_r',
        }
        candidates = [name_lower, aliases.get(name_lower, name_lower)]
        if name_lower.endswith(('_l', '_r', '_m')):
            base_no_one = name_lower.replace('1_', '_')
            if base_no_one not in candidates:
                candidates.append(base_no_one)
        all_nodes = (cmds.ls(type="transform") or []) + (cmds.ls(type="joint") or []) + (cmds.ls(type="locator") or [])
        lower_map = {n.lower(): n for n in all_nodes}
        for c in candidates:
            if c in lower_map:
                return lower_map[c]
        if 'fkscapula' in name_lower:
            for n in all_nodes:
                nl = n.lower()
                if nl.replace('1_', '_') == name_lower.replace('1_', '_'):
                    return n
        return None

    def clear_keys(self):
        """Idempotence: wipe keys we touch and zero the attrs."""
        attrs = ['translateX', 'translateY', 'rotateX', 'rotateY', 'rotateZ', 'stretchy', 'FKIKBlend']
        start = cmds.playbackOptions(q=True, min=True)
        end   = cmds.playbackOptions(q=True, max=True)

        # DO NOT include shoulder/elbow/wrist; IK handles them.
        controls = [
            self.root, self.hand_r, self.hand_l,
            self.hip, self.spine, self.chest, self.neck, self.head,
            self.scapula_l, self.scapula_r,
            self.fkik_leg_r, self.fkik_leg_l,
            self.fk_hip_r, self.fk_hip_l,
            self.fk_knee_r, self.fk_knee_l,
            self.fk_foot_r, self.fk_foot_l,
            self.fk_toe_r, self.fk_toe_l,
        ]

        for ctrl in controls:
            resolved = self.resolve_node_case_insensitive(ctrl)
            if not resolved:
                print(f"?? Could not resolve: {ctrl}")
                continue
            for attr in attrs:
                full_attr = f"{resolved}.{attr}"
                if cmds.attributeQuery(attr, node=resolved, exists=True):
                    cmds.cutKey(resolved, at=attr, time=(start, end))
                    if not cmds.getAttr(full_attr, lock=True) and not cmds.connectionInfo(full_attr, isDestination=True):
                        try:
                            cmds.setAttr(full_attr, 0)
                        except Exception:
                            pass

    def compute_frames(self):
        start = cmds.playbackOptions(q=True, min=True)
        end   = cmds.playbackOptions(q=True, max=True)
        quarter        = start + (end - start) / 4.0
        mid            = (start + end) / 2.0
        three_quarter  = start + 3 * (end - start) / 4.0
        self.frames = [start, quarter, mid, three_quarter, end]

    def set_key(self, obj, attr, time, value):
        if not cmds.objExists(obj):
            resolved = self.resolve_node_case_insensitive(obj)
            if resolved:
                obj = resolved
            else:
                print(f"?? Skipping key: {obj}.{attr} (not found)")
                return
        if not cmds.attributeQuery(attr, node=obj, exists=True):
            print(f"?? Skipping key: {obj}.{attr} (attr not found)")
            return
        cmds.currentTime(time, edit=True)
        cmds.setAttr(f"{obj}.{attr}", value)
        cmds.setKeyframe(obj, at=attr, t=time)

    # ---------- keying ----------

    def set_leg_fkik_blend_keys(self):
        """Key FKIKBlend (0..10) on FKIKLeg_{L,R} at start & end."""
        start, end = self.frames[0], self.frames[4]
        for ctrl in (self.fkik_leg_l, self.fkik_leg_r):
            self.set_key(ctrl, 'FKIKBlend', start, self.leg_fkik_blend)
            self.set_key(ctrl, 'FKIKBlend', end,   self.leg_fkik_blend)
    
    def set_leg_fk_pose_keys(self):
        """Static FK pose on rotateZ for both legs — keys only at start and end."""
        start, end = self.frames[0], self.frames[4]
        pairs = [
            (self.fk_hip_l,  self.fk_hip_r,  self.fk_hip_rz),
            (self.fk_knee_l, self.fk_knee_r, self.fk_knee_rz),
            (self.fk_foot_l, self.fk_foot_r, self.fk_foot_rz),
            (self.fk_toe_l,  self.fk_toe_r,  self.fk_toe_rz),
        ]
        for L, R, v in pairs:
            self.set_key(L, 'rotateZ', start, v); self.set_key(R, 'rotateZ', start, v)
            self.set_key(L, 'rotateZ', end,   v); self.set_key(R, 'rotateZ', end,   v)



    def set_stretch_keys(self):
        """When enabled, set IKArm_{L,R}.stretchy to 10 at start and end (two keys only)."""
        if not self.stretch_arms:
            return
        start, end = self.frames[0], self.frames[4]
        for arm in (self.hand_l, self.hand_r):
            self.set_key(arm, 'stretchy', start, 10)
            self.set_key(arm, 'stretchy', end,   10)

    def set_hand_keys(self):
        """Step using IKArm_*; apply step_narrowness absolute offsets on all hand X keys."""
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        step_x = d * self.step_width
        base_y = self.ground_height
        lift_y = self.ground_height + self.step_height

        first  = self.hand_r if self.mirror else self.hand_l
        second = self.hand_l if self.mirror else self.hand_r

        # resolve actual case once; compute offsets (+|n| for R, -|n| for L)
        hr = (self.resolve_node_case_insensitive(self.hand_r) or self.hand_r).lower()
        hl = (self.resolve_node_case_insensitive(self.hand_l) or self.hand_l).lower()
        offR = abs(self.step_narrowness)
        offL = -abs(self.step_narrowness)

        def x_with_narrow(node, base):
            ln = (self.resolve_node_case_insensitive(node) or node).lower()
            return base + (offR if ln == hr else offL if ln == hl else 0.0)

        # first hand moves early
        self.set_key(first,  'translateX', start, x_with_narrow(first, 0))
        self.set_key(first,  'translateY', start, base_y)
        self.set_key(first,  'translateY', quarter, lift_y)
        self.set_key(first,  'translateX', mid,   x_with_narrow(first, step_x))
        self.set_key(first,  'translateY', mid,   base_y)
        self.set_key(first,  'translateX', end,   x_with_narrow(first, 0))
        self.set_key(first,  'translateY', end,   base_y)

        # second hand catches up
        self.set_key(second, 'translateX', start, x_with_narrow(second, 0))
        self.set_key(second, 'translateY', start, base_y)
        self.set_key(second, 'translateX', mid,   x_with_narrow(second, 0))
        self.set_key(second, 'translateY', mid,   base_y)
        self.set_key(second, 'translateY', three_quarter, lift_y)
        self.set_key(second, 'translateX', three_quarter, x_with_narrow(second, step_x * 0.5))
        self.set_key(second, 'translateX', end,   x_with_narrow(second, 0))
        self.set_key(second, 'translateY', end,   base_y)

    def clamp_hands_to_ground(self):
        for hand in (self.hand_l, self.hand_r):
            node = self.resolve_node_case_insensitive(hand) or hand
            if not cmds.objExists(node) or not cmds.attributeQuery('translateY', node=node, exists=True):
                continue
            times = cmds.keyframe(node, at='translateY', q=True, tc=True) or []
            for t in set(times):
                v = cmds.keyframe(node, at='translateY', q=True, eval=True, t=(t, t))[0]
                if v < self.ground_height:
                    cmds.keyframe(node, at='translateY', e=True, t=(t, t), vc=self.ground_height)

    def set_root_keys(self):
        """Root: translateX half-width at mid; Tilt & Bounce on fifths; bounce has signed offset."""
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        off = self.root_offset_y  # signed
    
        # translateX: HALF step width at mid
        self.set_key(self.root, 'translateX', start, 0)
        self.set_key(self.root, 'translateX', mid,   d * (self.step_width * 0.5))
        self.set_key(self.root, 'translateX', end,   0)
    
        # rotateZ (fifths, mirrored)
        self.set_key(self.root, 'rotateZ', start,         0)
        self.set_key(self.root, 'rotateZ', quarter,       d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', mid,           0)
        self.set_key(self.root, 'rotateZ', three_quarter, -d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', end,           0)
    
        # translateY bounce (fifths, with signed offset baseline)
        self.set_key(self.root, 'translateY', start,         off)
        self.set_key(self.root, 'translateY', quarter,   off + self.root_bounce)
        self.set_key(self.root, 'translateY', mid,           off)
        self.set_key(self.root, 'translateY', three_quarter, off + self.root_bounce)
        self.set_key(self.root, 'translateY', end,           off)


    def set_scapula_keys(self):
        """Base scapula rotateY swing + absolute relaxers (Y/Z/X) for BOTH scapulas."""
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d = self._dir()
        s = self.scapula_swing * d
        addY = self._abs(self.down_scapula_y)
        addZ = self._abs(self.bent_scapula_z)
        addX = self._abs(self.twist_scapula_x)

        for node, sign in [(self.scapula_l, +1), (self.scapula_r, -1)]:
            # rotateY swing ±s + absolute down
            self.set_key(node, 'rotateY', start,  sign*s + addY)
            self.set_key(node, 'rotateY', mid,   -sign*s + addY)
            self.set_key(node, 'rotateY', end,    sign*s + addY)
            # absolute adds on Z/X
            self.set_key(node, 'rotateZ', start,  addZ)
            self.set_key(node, 'rotateZ', mid,    addZ)
            self.set_key(node, 'rotateZ', end,    addZ)
            self.set_key(node, 'rotateX', start,  addX)
            self.set_key(node, 'rotateX', mid,    addX)
            self.set_key(node, 'rotateX', end,    addX)

    def set_sidewhip_keys(self):
        """All torso rotateY on fifths."""
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        for ctrl, amount in [
            (self.hip,   self.hip_sway),
            (self.spine, self.spine_sway),
            (self.chest, self.chest_sway),
            (self.neck,  self.neck_sway),
            (self.head,  self.head_sway),
        ]:
            a = d * amount
            self.set_key(ctrl, 'rotateY', start,         0)
            self.set_key(ctrl, 'rotateY', quarter,       a)
            self.set_key(ctrl, 'rotateY', mid,           0)
            self.set_key(ctrl, 'rotateY', three_quarter, -a)
            self.set_key(ctrl, 'rotateY', end,           0)

    def generate(self):
        self.clear_keys()
        self.compute_frames()
        self.set_leg_fkik_blend_keys()
        self.set_leg_fk_pose_keys()
        self.set_hand_keys()
        self.set_root_keys()
        self.set_scapula_keys()
        self.set_sidewhip_keys()
        self.clamp_hands_to_ground()
        self.set_stretch_keys()

    # ---------- settings I/O ----------
    def print_settings(self, *args):
        settings = {
            'mirror': self.mirror,
            'stretch_arms': self.stretch_arms,
            'step_width': self.step_width,
            'step_height': self.step_height,
            'step_narrowness': self.step_narrowness,
            'ground_height': self.ground_height,
            'root_tilt': self.root_tilt,
            'root_bounce': self.root_bounce,
            'root_offset_y': self.root_offset_y,
            'scapula_swing': self.scapula_swing,
            'hip_sway': self.hip_sway,
            'spine_sway': self.spine_sway,
            'chest_sway': self.chest_sway,
            'neck_sway': self.neck_sway,
            'head_sway': self.head_sway,
            'down_scapula_y': self.down_scapula_y,
            'bent_scapula_z': self.bent_scapula_z,
            'twist_scapula_x': self.twist_scapula_x,
            'leg_fkik_blend': self.leg_fkik_blend,
            'fk_hip_rz':  self.fk_hip_rz,
            'fk_knee_rz': self.fk_knee_rz,
            'fk_foot_rz': self.fk_foot_rz,
            'fk_toe_rz':  self.fk_toe_rz,
        }
        print("// HandSideStepGenerator Settings:\n" + json.dumps(settings, indent=2))

    def apply_settings(self, settings):
        for k in settings:
            if hasattr(self, k):
                setattr(self, k, settings[k])

    def prompt_and_apply_settings(self, *args):
        result = cmds.promptDialog(
            title="Apply Settings",
            message="Paste JSON settings string here:",
            button=['Apply', 'Cancel'],
            defaultButton='Apply',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        if result != 'Apply':
            return
        try:
            text = cmds.promptDialog(query=True, text=True)
            settings = json.loads(text)
            self.apply_settings(settings)
            self.show()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    # ---------- UI ----------
    def on_generate(self, *args):
        self.mirror = cmds.checkBox(self.mirror_field, q=True, v=True)
        self.stretch_arms = cmds.checkBox(self.stretch_arms_field, q=True, v=True)

        self.step_width  = cmds.floatField(self.step_width_field,  q=True, v=True)
        self.step_height = cmds.floatField(self.step_height_field, q=True, v=True)
        self.step_narrowness = cmds.floatField(self.step_narrowness_field, q=True, v=True)
        self.ground_height = cmds.floatField(self.ground_height_field, q=True, v=True)

        self.root_tilt     = cmds.floatField(self.root_tilt_field,     q=True, v=True)
        self.root_bounce   = cmds.floatField(self.root_bounce_field,   q=True, v=True)
        self.root_offset_y = cmds.floatField(self.root_offset_y_field, q=True, v=True)

        self.scapula_swing = cmds.floatField(self.scapula_swing_field, q=True, v=True)

        self.hip_sway   = cmds.floatField(self.hip_sway_field,   q=True, v=True)
        self.spine_sway = cmds.floatField(self.spine_sway_field, q=True, v=True)
        self.chest_sway = cmds.floatField(self.chest_sway_field, q=True, v=True)
        self.neck_sway  = cmds.floatField(self.neck_sway_field,  q=True, v=True)
        self.head_sway  = cmds.floatField(self.head_sway_field,  q=True, v=True)

        self.down_scapula_y  = cmds.floatField(self.down_scapula_y_field,  q=True, v=True)
        self.bent_scapula_z  = cmds.floatField(self.bent_scapula_z_field,  q=True, v=True)
        self.twist_scapula_x = cmds.floatField(self.twist_scapula_x_field, q=True, v=True)
        
        self.leg_fkik_blend = cmds.floatSlider(self.leg_fkik_blend_slider, q=True, value=True)
        self.fk_hip_rz  = cmds.floatField(self.fk_hip_rz_field,  q=True, v=True)
        self.fk_knee_rz = cmds.floatField(self.fk_knee_rz_field, q=True, v=True)
        self.fk_foot_rz = cmds.floatField(self.fk_foot_rz_field, q=True, v=True)
        self.fk_toe_rz  = cmds.floatField(self.fk_toe_rz_field,  q=True, v=True)


        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Hand Side Step Generator", widthHeight=(640, 920))
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(180, 100, 180, 100), adjustableColumn=4)
            cmds.text(label=label1); field_fn1()
            cmds.text(label=label2); field_fn2()
            cmds.setParent('..')

        # Direction (topmost)
        cmds.frameLayout(label="Direction", collapsable=False, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 300))
        cmds.text(label="Mirror (ON = Step Right, OFF = Step Left):")
        self.mirror_field = cmds.checkBox(value=self.mirror)
        cmds.setParent('..'); cmds.setParent('..')

        # Quick toggle
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(220, 100))
        cmds.text(label="Stretch Arms (keys .stretchy=10):")
        self.stretch_arms_field = cmds.checkBox(value=self.stretch_arms)
        cmds.setParent('..')

        # Step Settings (Hands)
        cmds.frameLayout(label="Step Settings (Hands)", collapsable=True, marginWidth=10)
        two_col_row(
            "Step Width (X):",  lambda: setattr(self, 'step_width_field',  cmds.floatField(value=self.step_width)),
            "Step Height (Y):", lambda: setattr(self, 'step_height_field', cmds.floatField(value=self.step_height))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Ground Height (Y):")
        self.ground_height_field = cmds.floatField(value=self.ground_height)
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Step Narrowness (X):")
        self.step_narrowness_field = cmds.floatField(value=self.step_narrowness)
        cmds.setParent('..')
        cmds.setParent('..')

        # Root Settings
        cmds.frameLayout(label="Root Settings", collapsable=True, marginWidth=10)
        two_col_row(
            "Root Tilt (rotateZ):",      lambda: setattr(self, 'root_tilt_field',   cmds.floatField(value=self.root_tilt)),
            "Root Bounce (translateY):", lambda: setattr(self, 'root_bounce_field', cmds.floatField(value=self.root_bounce))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 100))
        cmds.text(label="Root Offset (translateY, signed):")
        self.root_offset_y_field = cmds.floatField(value=self.root_offset_y)
        cmds.setParent('..')
        cmds.setParent('..')

        # Scapula Animation (base + added)
        cmds.frameLayout(label="Scapula Animation", collapsable=True, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Scapula Swing (rotateY):")
        self.scapula_swing_field = cmds.floatField(value=self.scapula_swing)
        cmds.setParent('..')

        two_col_row(
            "Scapula Down (Y, add |v|):", lambda: setattr(self, 'down_scapula_y_field',  cmds.floatField(value=self.down_scapula_y)),
            "Scapula Bent (Z, add |v|):", lambda: setattr(self, 'bent_scapula_z_field',  cmds.floatField(value=self.bent_scapula_z))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Scapula Twist (X, add |v|):")
        self.twist_scapula_x_field = cmds.floatField(value=self.twist_scapula_x)
        cmds.setParent('..')

        # SideWhip (Torso)
        cmds.frameLayout(label="SideWhip (Torso)", collapsable=True, marginWidth=10)
        two_col_row(
            "Hip Sway (rotateY):",   lambda: setattr(self, 'hip_sway_field',   cmds.floatField(value=self.hip_sway)),
            "Spine Sway (rotateY):", lambda: setattr(self, 'spine_sway_field', cmds.floatField(value=self.spine_sway))
        )
        two_col_row(
            "Chest Sway (rotateY):", lambda: setattr(self, 'chest_sway_field', cmds.floatField(value=self.chest_sway)),
            "Neck Sway (rotateY):",  lambda: setattr(self, 'neck_sway_field',  cmds.floatField(value=self.neck_sway))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Head Sway (rotateY):")
        self.head_sway_field = cmds.floatField(value=self.head_sway)
        cmds.setParent('..'); cmds.setParent('..')

        # Legs Forward Kinematics
        cmds.frameLayout(label="Legs Forward Kinematics", collapsable=True, marginWidth=10)
        
        # FK/IK Blend slider 0..10
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(230, 320))
        cmds.text(label="Leg Forward Inverse Kinematics (FK↔IK Blend):")
        self.leg_fkik_blend_slider = cmds.floatSlider(min=0, max=10, step=0.1, value=self.leg_fkik_blend)
        cmds.setParent('..')
        
        # FK pose fields (rotateX), applied to BOTH legs
        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(180, 100, 180, 100), adjustableColumn=4)
            cmds.text(label=label1); field_fn1()
            cmds.text(label=label2); field_fn2()
            cmds.setParent('..')
        
        two_col_row(
            "Hip FK (rotateZ):",  lambda: setattr(self, 'fk_hip_rz_field',  cmds.floatField(value=self.fk_hip_rz)),
            "Knee FK (rotateZ):", lambda: setattr(self, 'fk_knee_rz_field', cmds.floatField(value=self.fk_knee_rz)),
        )
        two_col_row(
            "Foot FK (rotateZ):", lambda: setattr(self, 'fk_foot_rz_field', cmds.floatField(value=self.fk_foot_rz)),
            "Toe FK (rotateZ):",  lambda: setattr(self, 'fk_toe_rz_field',  cmds.floatField(value=self.fk_toe_rz)),
        )
        cmds.setParent('..')  # end frame


        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200), adjustableColumn=3)
        cmds.button(label="Generate Hand Side Step", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)


# To run:
HandSideStepGenerator().show()
