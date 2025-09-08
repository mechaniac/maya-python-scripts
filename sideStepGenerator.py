import maya.cmds as cmds
import json

class SideStepGenerator:
    def __init__(self):
        self.window = "SideStepGeneratorWindow"

        # Direction (only affects step/base swings)
        self.mirror = False  # ON => step right, OFF => step left

        # Controls
        self.root = "RootX_M"
        self.leg_r = "IKLeg_R"
        self.leg_l = "IKLeg_L"
        self.hip = "HipSwinger_M"
        self.spine = "FKSpine1_M"
        self.chest = "FKChest_M"
        self.neck = "FKNeck_M"
        self.head = "FKHead_M"
        self.scapula_l = "FKScapula_L"
        self.scapula_r = "FKScapula_R"
        self.shoulder_l = "FKShoulder_L"
        self.shoulder_r = "FKShoulder_R"
        self.elbow_l = "FKElbow_L"
        self.elbow_r = "FKElbow_R"
        self.wrist_l = "FKWrist_L"
        self.wrist_r = "FKWrist_R"

        # Step settings
        self.step_width = 5.0
        self.step_height = 2.0

        # Root motion
        self.root_tilt = 5.0       # rotateZ
        self.root_bounce = 1.0     # translateY
        self.root_offset_y = 0.0   # 🔹 NEW absolute offset added to root bounce

        # Base arm motion
        self.scapula_swing  = 10.0  # rotateY (L/R oppose)
        self.shoulder_swing = 5.0   # rotateZ (L/R oppose)
        self.elbow_swing    = 5.0   # rotateZ (L/R oppose)

        # Torso whip
        self.hip_sway = 3.0
        self.spine_sway = 2.0
        self.chest_sway = 1.5
        self.neck_sway = 1.0
        self.head_sway = 0.5

        # ABSOLUTE (non-mirrored) additions — apply to BOTH arms
        # Down (rotateY)
        self.down_scapula_y  = 0.0
        self.down_shoulder_y = 0.0
        self.down_elbow_y    = 0.0
        self.down_wrist_y    = 0.0
        # Bent (rotateZ)
        self.bent_scapula_z  = 0.0
        self.bent_shoulder_z = 0.0
        self.bent_elbow_z    = 0.0
        self.bent_wrist_z    = 0.0
        # Twist (rotateX)
        self.twist_scapula_x  = 0.0
        self.twist_shoulder_x = 0.0
        self.twist_elbow_x    = 0.0
        self.twist_wrist_x    = 0.0

        self.frames = []

    # ---------- helpers ----------
    def _dir(self):
        return -1 if self.mirror else 1

    def _abs(self, v):  # convenience
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
        """Wipe keys on all relevant nodes/attrs and reset to 0 so reruns are idempotent."""
        attrs = ['translateX', 'translateY', 'rotateX', 'rotateY', 'rotateZ']
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        controls = [
            self.root, self.leg_r, self.leg_l, self.hip,
            self.spine, self.chest, self.neck, self.head,
            self.scapula_l, self.scapula_r,
            self.shoulder_l, self.shoulder_r, self.elbow_l, self.elbow_r,
            self.wrist_l, self.wrist_r
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
        end = cmds.playbackOptions(q=True, max=True)
        quarter = start + (end - start) / 4.0
        mid = (start + end) / 2.0
        three_quarter = start + 3 * (end - start) / 4.0
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
    def set_leg_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        step_x = d * self.step_width
        lift_y = self.step_height

        first_leg  = self.leg_r if self.mirror else self.leg_l
        second_leg = self.leg_l if self.mirror else self.leg_r

        # first leg (moving)
        self.set_key(first_leg, 'translateX', start, 0)
        self.set_key(first_leg, 'translateY', start, 0)
        self.set_key(first_leg, 'translateY', quarter, lift_y)
        self.set_key(first_leg, 'translateX', mid, step_x)
        self.set_key(first_leg, 'translateY', mid, 0)
        self.set_key(first_leg, 'translateX', end, 0)
        self.set_key(first_leg, 'translateY', end, 0)

        # second leg (support -> catch-up)
        self.set_key(second_leg, 'translateX', start, 0)
        self.set_key(second_leg, 'translateY', start, 0)
        self.set_key(second_leg, 'translateX', mid, 0)
        self.set_key(second_leg, 'translateY', mid, 0)
        self.set_key(second_leg, 'translateY', three_quarter, lift_y)
        self.set_key(second_leg, 'translateX', three_quarter, step_x * 0.5)
        self.set_key(second_leg, 'translateX', end, 0)
        self.set_key(second_leg, 'translateY', end, 0)

    def set_root_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        off = self.root_offset_y  # signed
    
        # translateX: use HALF step width at mid  ⬅️ fix
        self.set_key(self.root, 'translateX', start, 0)
        self.set_key(self.root, 'translateX', mid,   d * (self.step_width * 0.5))
        self.set_key(self.root, 'translateX', end,   0)
    
        # rotateZ (fifths)
        self.set_key(self.root, 'rotateZ', start,         0)
        self.set_key(self.root, 'rotateZ', quarter,       d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', mid,           0)
        self.set_key(self.root, 'rotateZ', three_quarter, -d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', end,           0)
    
        # translateY (fifths with signed offset)
        self.set_key(self.root, 'translateY', start,         off)
        self.set_key(self.root, 'translateY', quarter,   off + self.root_bounce)
        self.set_key(self.root, 'translateY', mid,           off)
        self.set_key(self.root, 'translateY', three_quarter, off + self.root_bounce)
        self.set_key(self.root, 'translateY', end,           off)



    def set_scapula_keys(self):
        """Base scapula swing on rotateY + absolute add-ons on Y/Z/X for BOTH arms."""
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d = self._dir()
        s = self.scapula_swing * d
        addY = self._abs(self.down_scapula_y)
        addZ = self._abs(self.bent_scapula_z)
        addX = self._abs(self.twist_scapula_x)

        for node, sign in [(self.scapula_l, +1), (self.scapula_r, -1)]:
            # rotateY (base swing ±s) + absolute down
            self.set_key(node, 'rotateY', start,  sign*s + addY)
            self.set_key(node, 'rotateY', mid,   -sign*s + addY)
            self.set_key(node, 'rotateY', end,    sign*s + addY)
            # rotateZ (no base swing) + absolute bent
            self.set_key(node, 'rotateZ', start,  addZ)
            self.set_key(node, 'rotateZ', mid,    addZ)
            self.set_key(node, 'rotateZ', end,    addZ)
            # rotateX (no base swing) + absolute twist
            self.set_key(node, 'rotateX', start,  addX)
            self.set_key(node, 'rotateX', mid,    addX)
            self.set_key(node, 'rotateX', end,    addX)

    def set_shoulder_elbow_keys(self):
        """Shoulder/elbow rotateZ base swings + add-ons for Y/Z/X. Also keys wrists with add-ons."""
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d   = self._dir()
        shZ = self.shoulder_swing * d
        elZ = self.elbow_swing * d

        # absolute adds
        addY_sh = self._abs(self.down_shoulder_y)
        addZ_sh = self._abs(self.bent_shoulder_z)
        addX_sh = self._abs(self.twist_shoulder_x)

        addY_el = self._abs(self.down_elbow_y)
        addZ_el = self._abs(self.bent_elbow_z)
        addX_el = self._abs(self.twist_elbow_x)

        addY_wr = self._abs(self.down_wrist_y)
        addZ_wr = self._abs(self.bent_wrist_z)
        addX_wr = self._abs(self.twist_wrist_x)

        for (shoulder, elbow, wrist, sign) in [
            (self.shoulder_l, self.elbow_l, self.wrist_l, +1),
            (self.shoulder_r, self.elbow_r, self.wrist_r, -1),
        ]:
            # SHOULDER
            # Z: base swing ±shZ + absolute bent
            self.set_key(shoulder, 'rotateZ', start,  sign*shZ + addZ_sh)
            self.set_key(shoulder, 'rotateZ', mid,   -sign*shZ + addZ_sh)
            self.set_key(shoulder, 'rotateZ', end,    sign*shZ + addZ_sh)
            # Y: absolute down
            self.set_key(shoulder, 'rotateY', start,  addY_sh)
            self.set_key(shoulder, 'rotateY', mid,    addY_sh)
            self.set_key(shoulder, 'rotateY', end,    addY_sh)
            # X: absolute twist
            self.set_key(shoulder, 'rotateX', start,  addX_sh)
            self.set_key(shoulder, 'rotateX', mid,    addX_sh)
            self.set_key(shoulder, 'rotateX', end,    addX_sh)

            # ELBOW
            # Z: base swing ±elZ + absolute bent
            self.set_key(elbow, 'rotateZ', start,  sign*elZ + addZ_el)
            self.set_key(elbow, 'rotateZ', mid,   -sign*elZ + addZ_el)
            self.set_key(elbow, 'rotateZ', end,    sign*elZ + addZ_el)
            # Y: absolute down
            self.set_key(elbow, 'rotateY', start,  addY_el)
            self.set_key(elbow, 'rotateY', mid,    addY_el)
            self.set_key(elbow, 'rotateY', end,    addY_el)
            # X: absolute twist
            self.set_key(elbow, 'rotateX', start,  addX_el)
            self.set_key(elbow, 'rotateX', mid,    addX_el)
            self.set_key(elbow, 'rotateX', end,    addX_el)

            # WRIST (no base swing; just absolute adds so hands can relax)
            self.set_key(wrist, 'rotateY', start,  addY_wr)
            self.set_key(wrist, 'rotateY', mid,    addY_wr)
            self.set_key(wrist, 'rotateY', end,    addY_wr)

            self.set_key(wrist, 'rotateZ', start,  addZ_wr)
            self.set_key(wrist, 'rotateZ', mid,    addZ_wr)
            self.set_key(wrist, 'rotateZ', end,    addZ_wr)

            self.set_key(wrist, 'rotateX', start,  addX_wr)
            self.set_key(wrist, 'rotateX', mid,    addX_wr)
            self.set_key(wrist, 'rotateX', end,    addX_wr)

    def set_sidewhip_keys(self):
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
        self.set_leg_keys()
        self.set_root_keys()
        self.set_scapula_keys()         # base + absolute adds
        self.set_shoulder_elbow_keys()  # base + absolute adds (+ wrists)
        self.set_sidewhip_keys()

    # ---------- settings I/O & UI (unchanged except new fields) ----------
    def print_settings(self, *args):
        settings = {
            'mirror': self.mirror,
            'step_width': self.step_width,
            'step_height': self.step_height,
            'root_tilt': self.root_tilt,
            'root_bounce': self.root_bounce,
            'root_offset_y': self.root_offset_y,
            'scapula_swing': self.scapula_swing,
            'shoulder_swing': self.shoulder_swing,
            'elbow_swing': self.elbow_swing,
            'hip_sway': self.hip_sway,
            'spine_sway': self.spine_sway,
            'chest_sway': self.chest_sway,
            'neck_sway': self.neck_sway,
            'head_sway': self.head_sway,

            'down_scapula_y': self.down_scapula_y,
            'down_shoulder_y': self.down_shoulder_y,
            'down_elbow_y': self.down_elbow_y,
            'down_wrist_y': self.down_wrist_y,

            'bent_scapula_z': self.bent_scapula_z,
            'bent_shoulder_z': self.bent_shoulder_z,
            'bent_elbow_z': self.bent_elbow_z,
            'bent_wrist_z': self.bent_wrist_z,

            'twist_scapula_x': self.twist_scapula_x,
            'twist_shoulder_x': self.twist_shoulder_x,
            'twist_elbow_x': self.twist_elbow_x,
            'twist_wrist_x': self.twist_wrist_x,
        }
        print("// SideStepGenerator Settings:\n" + json.dumps(settings, indent=2))

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

    def on_generate(self, *args):
        self.mirror = cmds.checkBox(self.mirror_field, q=True, v=True)

        self.step_width  = cmds.floatField(self.step_width_field,  q=True, v=True)
        self.step_height = cmds.floatField(self.step_height_field, q=True, v=True)

        self.root_tilt   = cmds.floatField(self.root_tilt_field,   q=True, v=True)
        self.root_bounce = cmds.floatField(self.root_bounce_field, q=True, v=True)
        self.root_offset_y = cmds.floatField(self.root_offset_y_field, q=True, v=True)

        self.scapula_swing  = cmds.floatField(self.scapula_swing_field,  q=True, v=True)
        self.shoulder_swing = cmds.floatField(self.shoulder_swing_field, q=True, v=True)
        self.elbow_swing    = cmds.floatField(self.elbow_swing_field,    q=True, v=True)

        self.hip_sway   = cmds.floatField(self.hip_sway_field,   q=True, v=True)
        self.spine_sway = cmds.floatField(self.spine_sway_field, q=True, v=True)
        self.chest_sway = cmds.floatField(self.chest_sway_field, q=True, v=True)
        self.neck_sway  = cmds.floatField(self.neck_sway_field,  q=True, v=True)
        self.head_sway  = cmds.floatField(self.head_sway_field,  q=True, v=True)

        # Absolute (both arms)
        self.down_scapula_y  = cmds.floatField(self.down_scapula_y_field,  q=True, v=True)
        self.down_shoulder_y = cmds.floatField(self.down_shoulder_y_field, q=True, v=True)
        self.down_elbow_y    = cmds.floatField(self.down_elbow_y_field,    q=True, v=True)
        self.down_wrist_y    = cmds.floatField(self.down_wrist_y_field,    q=True, v=True)

        self.bent_scapula_z  = cmds.floatField(self.bent_scapula_z_field,  q=True, v=True)
        self.bent_shoulder_z = cmds.floatField(self.bent_shoulder_z_field, q=True, v=True)
        self.bent_elbow_z    = cmds.floatField(self.bent_elbow_z_field,    q=True, v=True)
        self.bent_wrist_z    = cmds.floatField(self.bent_wrist_z_field,    q=True, v=True)

        self.twist_scapula_x  = cmds.floatField(self.twist_scapula_x_field,  q=True, v=True)
        self.twist_shoulder_x = cmds.floatField(self.twist_shoulder_x_field, q=True, v=True)
        self.twist_elbow_x    = cmds.floatField(self.twist_elbow_x_field,    q=True, v=True)
        self.twist_wrist_x    = cmds.floatField(self.twist_wrist_x_field,    q=True, v=True)

        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Side Step Generator", widthHeight=(640, 1020))
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(180, 100, 180, 100), adjustableColumn=4)
            cmds.text(label=label1); field_fn1()
            cmds.text(label=label2); field_fn2()
            cmds.setParent('..')

        # Direction
        cmds.frameLayout(label="Direction", collapsable=False, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 300))
        cmds.text(label="Mirror (ON = Step Right, OFF = Step Left):")
        self.mirror_field = cmds.checkBox(value=self.mirror)
        cmds.setParent('..'); cmds.setParent('..')

        # Step
        cmds.frameLayout(label="Step Settings", collapsable=True, marginWidth=10)
        two_col_row(
            "Step Width (X):",  lambda: setattr(self, 'step_width_field',  cmds.floatField(value=self.step_width)),
            "Step Height (Y):", lambda: setattr(self, 'step_height_field', cmds.floatField(value=self.step_height))
        )
        cmds.setParent('..')

        # Root
        cmds.frameLayout(label="Root Settings", collapsable=True, marginWidth=10)
        two_col_row(
            "Root Tilt (rotateZ):",      lambda: setattr(self, 'root_tilt_field',   cmds.floatField(value=self.root_tilt)),
            "Root Bounce (translateY):", lambda: setattr(self, 'root_bounce_field', cmds.floatField(value=self.root_bounce))
        )
        # Root Settings frame (keep your existing two_col_row for Tilt/Bounce)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Root Offset (translateY):")
        self.root_offset_y_field = cmds.floatField(value=self.root_offset_y)
        cmds.setParent('..')
        cmds.setParent('..')     # <-- ADD THIS: closes the frame


        # Arm / Scapula base anim
        cmds.frameLayout(label="Arm / Scapula Animation", collapsable=True, marginWidth=10)
        two_col_row(
            "Scapula Swing (rotateY):",  lambda: setattr(self, 'scapula_swing_field',  cmds.floatField(value=self.scapula_swing)),
            "Shoulder Swing (rotateZ):", lambda: setattr(self, 'shoulder_swing_field', cmds.floatField(value=self.shoulder_swing))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Elbow Bend (rotateZ):")
        self.elbow_swing_field = cmds.floatField(value=self.elbow_swing)
        cmds.setParent('..'); cmds.setParent('..')

        # Torso Whip
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

        # Arms Down (Added)
        cmds.frameLayout(label="Arms Down (Added) — add |value| to rotateY (Both arms)", collapsable=True, marginWidth=10)
        two_col_row(
            "Scapula Down (Y):",  lambda: setattr(self, 'down_scapula_y_field',  cmds.floatField(value=self.down_scapula_y)),
            "Shoulder Down (Y):", lambda: setattr(self, 'down_shoulder_y_field', cmds.floatField(value=self.down_shoulder_y))
        )
        two_col_row(
            "Elbow Down (Y):",    lambda: setattr(self, 'down_elbow_y_field',    cmds.floatField(value=self.down_elbow_y)),
            "Wrist Down (Y):",    lambda: setattr(self, 'down_wrist_y_field',    cmds.floatField(value=self.down_wrist_y))
        )
        cmds.setParent('..')

        # Arms Bent (Added)
        cmds.frameLayout(label="Arms Bent (Added) — add |value| to rotateZ (Both arms)", collapsable=True, marginWidth=10)
        two_col_row(
            "Scapula Bent (Z):",  lambda: setattr(self, 'bent_scapula_z_field',  cmds.floatField(value=self.bent_scapula_z)),
            "Shoulder Bent (Z):", lambda: setattr(self, 'bent_shoulder_z_field', cmds.floatField(value=self.bent_shoulder_z))
        )
        two_col_row(
            "Elbow Bent (Z):",    lambda: setattr(self, 'bent_elbow_z_field',    cmds.floatField(value=self.bent_elbow_z)),
            "Wrist Bent (Z):",    lambda: setattr(self, 'bent_wrist_z_field',    cmds.floatField(value=self.bent_wrist_z))
        )
        cmds.setParent('..')

        # Arms Twist (Added)
        cmds.frameLayout(label="Arms Twist (Added) — add |value| to rotateX (Both arms)", collapsable=True, marginWidth=10)
        two_col_row(
            "Scapula Twist (X):",  lambda: setattr(self, 'twist_scapula_x_field',  cmds.floatField(value=self.twist_scapula_x)),
            "Shoulder Twist (X):", lambda: setattr(self, 'twist_shoulder_x_field', cmds.floatField(value=self.twist_shoulder_x))
        )
        two_col_row(
            "Elbow Twist (X):",    lambda: setattr(self, 'twist_elbow_x_field',    cmds.floatField(value=self.twist_elbow_x)),
            "Wrist Twist (X):",    lambda: setattr(self, 'twist_wrist_x_field',    cmds.floatField(value=self.twist_wrist_x))
        )
        cmds.setParent('..')

        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200), adjustableColumn=3)
        cmds.button(label="Generate Side Step", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)


# To run:
SideStepGenerator().show()
