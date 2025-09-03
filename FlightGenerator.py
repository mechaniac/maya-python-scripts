# FlightGenerator.py  (Maya Python 2 / 2018)
import maya.cmds as cmds
import json

class FlightGenerator:
    def __init__(self):
        self.window = "FlightGeneratorWindow"

        # Controls (resolved case-insensitively when keying)
        self.root     = "RootX_M"
        self.ik_arm_l = "IKArm_L"
        self.ik_arm_r = "IKArm_R"
        self.fkik_l   = "FKIKArm_L"
        self.fkik_r   = "FKIKArm_R"
        self.scap_l   = "FKScapula_L"
        self.scap_r   = "FKScapula_R"
        self.pole_l   = "PoleArm_L"
        self.pole_r   = "PoleArm_R"

        # IKArm_*.translateZ pattern (start:0, quarter:down, three_quarter:up, end:0)
        self.ik_arms_down = 5.0
        self.ik_arms_up   = 2.5

        # IKArm_*.rotateX constant (start=end=input)
        self.arm_rotateX_value = 10.0

        # Hand Flap on IKArm_*.rotateY (start:0, quarter:down, three_quarter:up, end:0), L opposes R
        self.hand_flap_down = 8.0
        self.hand_flap_up   = -4.0

        # Hand Positioning (translates) — Base + two deltas
        # X (Apart) uses opposing signs; Y (Flap) same both sides
        # Hand Positioning X (mirrored L=+, R=-)
        self.hands_base_x = 0.0
        self.hands_x_q    = 0.0   # at 1/4
        self.hands_x_mid  = 0.0   # at 1/2
        self.hands_x_3q   = 0.0   # at 3/4
        self.hands_base_y = 0.0
        self.hands_flap   = 0.0   # Y delta applied at 1/4


        # FK/IK blend (0..10) on FKIKArm_*.FKIKBlend (constant, keyed start & end)
        self.fkik_blend_value = 10.0

        # ROOT movement
        # Up/Down (translateZ) — start=Base, quarter=Mid, threeQuarters=-Mid, end=Base
        self.root_updown_base = 0.0
        self.root_updown_mid  = 0.0
        # Back/Forth (rotateX) — same pattern
        self.root_backforth_base = 0.0
        self.root_backforth_mid  = 0.0

        # SCAPULA flap (rotateZ) — NEW pattern: start=0, quarter=Base, threeQuarters=Mid, end=0
        self.scap_flap_base = 0.0
        self.scap_flap_mid  = 0.0

        # ELBOW POLES (PoleArm_* translates)
        # Pattern per axis: start=offset, quarter=offset+base, threeQuarters=offset+mid, end=offset
        # X is mirrored L(+)/R(-); Y and Z same both sides
        self.pole_off_x = 0.0; self.pole_base_x = 0.0; self.pole_mid_x = 0.0
        self.pole_off_y = 0.0; self.pole_base_y = 0.0; self.pole_mid_y = 0.0
        self.pole_off_z = 0.0; self.pole_base_z = 0.0; self.pole_mid_z = 0.0

        self.frames = []  # [start, quarter, mid, three_quarter, end]

    # ---------- helpers ----------
    def resolve_node_case_insensitive(self, name):
        name_lower = name.lower()
        aliases = {
            'fkscapula1_l': 'fkscapula_l', 'fkscapula_l': 'fkscapula1_l',
            'fkscapula1_r': 'fkscapula_r', 'fkscapula_r': 'fkscapula1_r',
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
        for n in all_nodes:
            nl = n.lower()
            if nl.replace('1_', '_') == name_lower.replace('1_', '_'):
                return n
        return None

    def _timeline_start_end(self):
        s = float(cmds.playbackOptions(q=True, min=True))
        e = float(cmds.playbackOptions(q=True, max=True))
        return s, e

    def compute_frames(self):
        s, e = self._timeline_start_end()
        if e <= s:
            raise RuntimeError("Playback range invalid (start >= end).")
        quarter = s + (e - s) / 4.0
        mid = (s + e) / 2.0
        three_quarter = s + 3 * (e - s) / 4.0
        self.frames = [s, quarter, mid, three_quarter, e]

    def set_key(self, obj, attr, time, value):
        if not cmds.objExists(obj):
            r = self.resolve_node_case_insensitive(obj)
            if r:
                obj = r
            else:
                print("?? Skipping key: {}.{} (node not found)".format(obj, attr))
                return
        if not cmds.attributeQuery(attr, node=obj, exists=True):
            print("?? Skipping key: {}.{} (attr not found)".format(obj, attr))
            return
        try:
            cmds.currentTime(time, edit=True)
            cmds.setAttr("{}.{}".format(obj, attr), value)
            cmds.setKeyframe(obj, at=attr, t=time)
        except Exception as e:
            print("!! set_key failed: {}.{} @ {} -> {}".format(obj, attr, time, e))

    def cut_attr_keys_in_range(self, obj, attr, t0, t1, reset_to_zero=True):
        if not cmds.objExists(obj) or not cmds.attributeQuery(attr, node=obj, exists=True):
            return
        try:
            cmds.cutKey(obj, at=attr, time=(t0, t1))
            full_attr = "{}.{}".format(obj, attr)
            if reset_to_zero and not cmds.getAttr(full_attr, lock=True) and not cmds.connectionInfo(full_attr, isDestination=True):
                cmds.setAttr(full_attr, 0)
        except Exception:
            pass

    # ---------- keying ----------
    def clear_keys(self):
        s, e = self._timeline_start_end()
        for node, attrs in [
            # arms
            (self.ik_arm_l, ["translateZ", "rotateX", "rotateY", "translateX", "translateY"]),
            (self.ik_arm_r, ["translateZ", "rotateX", "rotateY", "translateX", "translateY"]),
            # FK/IK
            (self.fkik_l,   ["FKIKBlend"]),
            (self.fkik_r,   ["FKIKBlend"]),
            # root
            (self.root,     ["translateZ", "rotateX"]),
            # scapulas
            (self.scap_l,   ["rotateZ"]),
            (self.scap_r,   ["rotateZ"]),
            # elbow poles
            (self.pole_l,   ["translateX", "translateY", "translateZ"]),
            (self.pole_r,   ["translateX", "translateY", "translateZ"]),
        ]:
            resolved = self.resolve_node_case_insensitive(node) or node
            for a in attrs:
                self.cut_attr_keys_in_range(resolved, a, s, e, reset_to_zero=True)

    def key_arms(self):
        start, quarter, _, three_quarter, end = self.frames

        # IKArm_*.translateZ: 0 -> down -> up -> 0
        for node in [self.ik_arm_l, self.ik_arm_r]:
            self.set_key(node, "translateZ", start,         0.0)
            self.set_key(node, "translateZ", quarter,       float(self.ik_arms_down))
            self.set_key(node, "translateZ", three_quarter, float(self.ik_arms_up))
            self.set_key(node, "translateZ", end,           0.0)

        # IKArm_*.rotateX: constant (start & end)
        for node in [self.ik_arm_l, self.ik_arm_r]:
            val = float(self.arm_rotateX_value)
            self.set_key(node, "rotateX", start, val)
            self.set_key(node, "rotateX", end,   val)

    def key_hand_flap(self):
        # Hand flap (IKArm_*.rotateY):
        # start: 0, quarter: ±down, mid: (no key), three_quarters: ±up, end: 0
        start, quarter, mid, three_quarter, end = self.frames
        pairs = [(self.ik_arm_l, +1.0), (self.ik_arm_r, -1.0)]
        for node, sgn in pairs:
            self.set_key(node, "rotateY", start,        0.0)
            self.set_key(node, "rotateY", quarter,      sgn * float(self.hand_flap_down))
            # (intentionally no key at mid)
            self.set_key(node, "rotateY", three_quarter, sgn * float(self.hand_flap_up))
            self.set_key(node, "rotateY", end,          0.0)


    def key_hand_positioning(self):
        start, quarter, mid, three_quarter, end = self.frames
    
        # --- X (mirrored) ---
        baseX = float(self.hands_base_x)
        qX    = float(self.hands_x_q)
        mX    = float(self.hands_x_mid)
        q3X   = float(self.hands_x_3q)
        for node, sgn in [(self.ik_arm_l, +1.0), (self.ik_arm_r, -1.0)]:
            self.set_key(node, "translateX", start,         sgn * baseX)
            self.set_key(node, "translateX", quarter,       sgn * (baseX + qX))
            self.set_key(node, "translateX", mid,           sgn * (baseX + mX))
            self.set_key(node, "translateX", three_quarter, sgn * (baseX + q3X))
            self.set_key(node, "translateX", end,           sgn * baseX)
    
        # --- Y (unchanged) ---
        baseY = float(self.hands_base_y)
        flapY = float(self.hands_flap)
        for node in [self.ik_arm_l, self.ik_arm_r]:
            self.set_key(node, "translateY", start,         baseY)
            self.set_key(node, "translateY", quarter,       baseY + flapY)
            # (no key at mid)
            self.set_key(node, "translateY", three_quarter, baseY)
            self.set_key(node, "translateY", end,           baseY)



    def key_root_movement(self):
        # Root Up/Down (translateZ) and Back/Forth (rotateX)
        start, quarter, mid, three_quarter, end = self.frames

        # Up/Down (translateZ): start=Base, quarter=Mid, threeQuarters=-Mid, end=Base
        baseZ = float(self.root_updown_base)
        midZ  = float(self.root_updown_mid)
        self.set_key(self.root, "translateZ", start,         baseZ)
        self.set_key(self.root, "translateZ", quarter,       midZ)
        self.set_key(self.root, "translateZ", three_quarter, -midZ)
        self.set_key(self.root, "translateZ", end,           baseZ)

        # Back/Forth (rotateX): same pattern
        baseRX = float(self.root_backforth_base)
        midRX  = float(self.root_backforth_mid)
        self.set_key(self.root, "rotateX", start,         baseRX)
        self.set_key(self.root, "rotateX", quarter,       midRX)
        self.set_key(self.root, "rotateX", three_quarter, -midRX)
        self.set_key(self.root, "rotateX", end,           baseRX)

    def key_scapula_flap(self):
        # NEW pattern for scapula rotateZ:
        # start: 0, quarter: Base, three_quarters: Mid, end: 0
        start, quarter, mid, three_quarter, end = self.frames
        base = float(self.scap_flap_base)
        midv = float(self.scap_flap_mid)
        for node in [self.scap_l, self.scap_r]:
            self.set_key(node, "rotateZ", start,         0.0)
            self.set_key(node, "rotateZ", quarter,       base)
            self.set_key(node, "rotateZ", three_quarter, midv)
            self.set_key(node, "rotateZ", end,           0.0)

    def key_elbow_poles(self):
        # PoleArm_* translates with offset + base/mid; X mirrored
        start, quarter, mid, three_quarter, end = self.frames

        offX = float(self.pole_off_x); baseX = float(self.pole_base_x); midX = float(self.pole_mid_x)
        offY = float(self.pole_off_y); baseY = float(self.pole_base_y); midY = float(self.pole_mid_y)
        offZ = float(self.pole_off_z); baseZ = float(self.pole_base_z); midZ = float(self.pole_mid_z)

        for node, sgn in [(self.pole_l, +1.0), (self.pole_r, -1.0)]:
            # X (mirrored)
            self.set_key(node, "translateX", start,         sgn * (offX))
            self.set_key(node, "translateX", quarter,       sgn * (offX + baseX))
            self.set_key(node, "translateX", three_quarter, sgn * (offX + midX))
            self.set_key(node, "translateX", end,           sgn * (offX))
            # Y (same both sides)
            self.set_key(node, "translateY", start,         offY)
            self.set_key(node, "translateY", quarter,       offY + baseY)
            self.set_key(node, "translateY", three_quarter, offY + midY)
            self.set_key(node, "translateY", end,           offY)
            # Z (same both sides)
            self.set_key(node, "translateZ", start,         offZ)
            self.set_key(node, "translateZ", quarter,       offZ + baseZ)
            self.set_key(node, "translateZ", three_quarter, offZ + midZ)
            self.set_key(node, "translateZ", end,           offZ)

    def key_fkik_blend(self):
        start, _, _, _, end = self.frames
        val = float(self.fkik_blend_value)
        for node in [self.fkik_l, self.fkik_r]:
            self.set_key(node, "FKIKBlend", start, val)
            self.set_key(node, "FKIKBlend", end,   val)

    def generate(self):
        self.clear_keys()
        self.compute_frames()
        self.key_arms()
        self.key_hand_flap()
        self.key_hand_positioning()
        self.key_root_movement()
        self.key_scapula_flap()
        self.key_elbow_poles()
        self.key_fkik_blend()
        self.print_settings()
        try:
            cmds.inViewMessage(
                amg='[FlightGenerator] Keys: arms Z, hand flap Y (1/4 & 3/4), hand pos X (1/4 flap / 3/4 apart), root Z/X, scap Z, poles XYZ, FK/IK.',
                pos='midCenter', fade=True
            )
        except Exception:
            pass

    def _try_set_float(self, ctrl, val):
        if not ctrl or not cmds.control(ctrl, exists=True):
            return
        try:
            cmds.floatField(ctrl, e=True, v=float(val)); return
        except Exception:
            pass
        try:
            cmds.floatSlider(ctrl, e=True, v=float(val)); return
        except Exception:
            pass
    
    def refresh_ui_fields(self):
        # IK Arms
        self._try_set_float(getattr(self, 'ik_arms_down_field', None), self.ik_arms_down)
        self._try_set_float(getattr(self, 'ik_arms_up_field',   None), self.ik_arms_up)
        self._try_set_float(getattr(self, 'arm_rotateX_field',  None), self.arm_rotateX_value)
    
        # Hand flap
        self._try_set_float(getattr(self, 'hand_flap_down_field', None), self.hand_flap_down)
        self._try_set_float(getattr(self, 'hand_flap_up_field',   None), self.hand_flap_up)
    
        # Hand positioning X (new 1/4, 1/2, 3/4) + Y
        self._try_set_float(getattr(self, 'hands_base_x_field', None), self.hands_base_x)
        self._try_set_float(getattr(self, 'hands_x_q_field',    None), self.hands_x_q)
        self._try_set_float(getattr(self, 'hands_x_mid_field',  None), self.hands_x_mid)
        self._try_set_float(getattr(self, 'hands_x_3q_field',   None), self.hands_x_3q)
        self._try_set_float(getattr(self, 'hands_base_y_field', None), self.hands_base_y)
        self._try_set_float(getattr(self, 'hands_flap_field',   None), self.hands_flap)
    
        # Root
        self._try_set_float(getattr(self, 'root_updown_base_field',    None), self.root_updown_base)
        self._try_set_float(getattr(self, 'root_updown_mid_field',     None), self.root_updown_mid)
        self._try_set_float(getattr(self, 'root_backforth_base_field', None), self.root_backforth_base)
        self._try_set_float(getattr(self, 'root_backforth_mid_field',  None), self.root_backforth_mid)
    
        # Scapula
        self._try_set_float(getattr(self, 'scap_flap_base_field', None), self.scap_flap_base)
        self._try_set_float(getattr(self, 'scap_flap_mid_field',  None), self.scap_flap_mid)
    
        # Poles
        self._try_set_float(getattr(self, 'pole_off_x_field', None),  self.pole_off_x)
        self._try_set_float(getattr(self, 'pole_base_x_field', None), self.pole_base_x)
        self._try_set_float(getattr(self, 'pole_mid_x_field', None),  self.pole_mid_x)
        self._try_set_float(getattr(self, 'pole_off_y_field', None),  self.pole_off_y)
        self._try_set_float(getattr(self, 'pole_base_y_field', None), self.pole_base_y)
        self._try_set_float(getattr(self, 'pole_mid_y_field', None),  self.pole_mid_y)
        self._try_set_float(getattr(self, 'pole_off_z_field', None),  self.pole_off_z)
        self._try_set_float(getattr(self, 'pole_base_z_field', None), self.pole_base_z)
        self._try_set_float(getattr(self, 'pole_mid_z_field', None),  self.pole_mid_z)
    
        # FK/IK blend slider
        self._try_set_float(getattr(self, 'fkik_blend_slider', None), self.fkik_blend_value)

    # ---------- settings I/O & UI ----------
    def print_settings(self, *args):
        settings = {
            'ik_arms_down':        self.ik_arms_down,
            'ik_arms_up':          self.ik_arms_up,
            'arm_rotateX_value':   self.arm_rotateX_value,
            'hand_flap_down':      self.hand_flap_down,
            'hand_flap_up':        self.hand_flap_up,
            "hands_base_x": self.hands_base_x,
            "hands_x_q":    self.hands_x_q,
            "hands_x_mid":  self.hands_x_mid,
            "hands_x_3q":   self.hands_x_3q,
            'hands_base_y': self.hands_base_y,
            'hands_flap':   self.hands_flap,
            'root_updown_base':    self.root_updown_base,
            'root_updown_mid':     self.root_updown_mid,
            'root_backforth_base': self.root_backforth_base,
            'root_backforth_mid':  self.root_backforth_mid,
            'scap_flap_base':      self.scap_flap_base,
            'scap_flap_mid':       self.scap_flap_mid,
            'pole_off_x': self.pole_off_x, 'pole_base_x': self.pole_base_x, 'pole_mid_x': self.pole_mid_x,
            'pole_off_y': self.pole_off_y, 'pole_base_y': self.pole_base_y, 'pole_mid_y': self.pole_mid_y,
            'pole_off_z': self.pole_off_z, 'pole_base_z': self.pole_base_z, 'pole_mid_z': self.pole_mid_z,
            'fkik_blend_value':    self.fkik_blend_value,
        }
        print("// FlightGenerator Settings:\n" + json.dumps(settings, indent=2))

    def apply_settings(self, settings):
        for k, v in settings.items():
            if hasattr(self, k):
                setattr(self, k, v)
    
        # back-compat: accept older keys
        if 'hands_x_q' not in settings and 'hands_x_flap' in settings:
            self.hands_x_q = settings['hands_x_flap']
        if 'hands_x_3q' not in settings and 'hands_apart' in settings:
            self.hands_x_3q = settings['hands_apart']


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
    
            # Refresh widgets in-place (don’t rebuild/delete the window here)
            cmds.evalDeferred(lambda *a: self.refresh_ui_fields())
    
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))


    def on_generate(self, *args):
        # Arms
        self.ik_arms_down      = cmds.floatField(self.ik_arms_down_field, q=True, v=True)
        self.ik_arms_up        = cmds.floatField(self.ik_arms_up_field,   q=True, v=True)
        self.arm_rotateX_value = cmds.floatField(self.arm_rotateX_field,  q=True, v=True)
        # Hand flap
        self.hand_flap_down    = cmds.floatField(self.hand_flap_down_field, q=True, v=True)
        self.hand_flap_up      = cmds.floatField(self.hand_flap_up_field,   q=True, v=True)
        # Hand positioning
        self.hands_base_x = cmds.floatField(self.hands_base_x_field, q=True, v=True)
        self.hands_x_q    = cmds.floatField(self.hands_x_q_field,    q=True, v=True)
        self.hands_x_mid  = cmds.floatField(self.hands_x_mid_field,  q=True, v=True)
        self.hands_x_3q   = cmds.floatField(self.hands_x_3q_field,   q=True, v=True)

        
        self.hands_base_y = cmds.floatField(self.hands_base_y_field, q=True, v=True)
        self.hands_flap   = cmds.floatField(self.hands_flap_field,   q=True, v=True)

        # Root
        self.root_updown_base     = cmds.floatField(self.root_updown_base_field,     q=True, v=True)
        self.root_updown_mid      = cmds.floatField(self.root_updown_mid_field,      q=True, v=True)
        self.root_backforth_base  = cmds.floatField(self.root_backforth_base_field,  q=True, v=True)
        self.root_backforth_mid   = cmds.floatField(self.root_backforth_mid_field,   q=True, v=True)
        # Scapula
        self.scap_flap_base    = cmds.floatField(self.scap_flap_base_field, q=True, v=True)
        self.scap_flap_mid     = cmds.floatField(self.scap_flap_mid_field,  q=True, v=True)
        # Poles
        self.pole_off_x = cmds.floatField(self.pole_off_x_field, q=True, v=True)
        self.pole_base_x = cmds.floatField(self.pole_base_x_field, q=True, v=True)
        self.pole_mid_x  = cmds.floatField(self.pole_mid_x_field,  q=True, v=True)

        self.pole_off_y = cmds.floatField(self.pole_off_y_field, q=True, v=True)
        self.pole_base_y = cmds.floatField(self.pole_base_y_field, q=True, v=True)
        self.pole_mid_y  = cmds.floatField(self.pole_mid_y_field,  q=True, v=True)

        self.pole_off_z = cmds.floatField(self.pole_off_z_field, q=True, v=True)
        self.pole_base_z = cmds.floatField(self.pole_base_z_field, q=True, v=True)
        self.pole_mid_z  = cmds.floatField(self.pole_mid_z_field,  q=True, v=True)

        # FK/IK
        self.fkik_blend_value  = cmds.floatSlider(self.fkik_blend_slider, q=True, v=True)

        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Flight Generator", widthHeight=(760, 820), sizeable=True)
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(320, 100, 320, 100), adjustableColumn=4)
            cmds.text(label=label1); field_fn1()
            cmds.text(label=label2); field_fn2()
            cmds.setParent('..')

        # IK Arms (translateZ) + rotateX constant
        cmds.frameLayout(label="IK Arms", collapsable=True, marginWidth=10)
        two_col_row(
            "IK Arms down (Z @ 1/4):", lambda: setattr(self, 'ik_arms_down_field', cmds.floatField(value=self.ik_arms_down)),
            "IK Arms up (Z @ 3/4):",  lambda: setattr(self, 'ik_arms_up_field',   cmds.floatField(value=self.ik_arms_up))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 100))
        cmds.text(label="IK Arms rotateX (start=end):")
        self.arm_rotateX_field = cmds.floatField(value=self.arm_rotateX_value)
        cmds.setParent('..')
        cmds.setParent('..')

        # Hand Flap (rotateY, L/R oppose)
        cmds.frameLayout(label="Hand Flap (IK rotateY, L/R oppose)", collapsable=True, marginWidth=10)
        two_col_row(
            "Hand Flap down (1/4):", lambda: setattr(self, 'hand_flap_down_field', cmds.floatField(value=self.hand_flap_down)),
            "Hand Flap up (3/4):",   lambda: setattr(self, 'hand_flap_up_field',   cmds.floatField(value=self.hand_flap_up))
        )
        cmds.setParent('..')

        # Hand Positioning (IK translates)
        cmds.frameLayout(label="Hand Positioning (IK translates)", collapsable=True, marginWidth=10)
        
        # X row: Base, 1/4, 1/2, 3/4  (works in 2026)
        row = cmds.rowLayout(numberOfColumns=8, adjustableColumn=8)
        # set per-column widths
        for i, w in [(1,120),(2,80),(3,120),(4,80),(5,120),(6,80),(7,120),(8,80)]:
            cmds.rowLayout(row, e=True, columnWidth=(i, w))
        
        cmds.text(label="Base X (L=+, R=-):"); self.hands_base_x_field = cmds.floatField(value=self.hands_base_x)
        cmds.text(label="X @ 1/4:");           self.hands_x_q_field    = cmds.floatField(value=self.hands_x_q)
        cmds.text(label="X @ 1/2:");           self.hands_x_mid_field  = cmds.floatField(value=self.hands_x_mid)
        cmds.text(label="X @ 3/4:");           self.hands_x_3q_field   = cmds.floatField(value=self.hands_x_3q)
        cmds.setParent('..')


        
        # inside the Hand Positioning frame, replace the inner def:
        def two_col_row_small(label1, fn1, label2, fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(160, 100, 140, 100), adjustableColumn=4)
            cmds.text(label=label1); fn1()
            cmds.text(label=label2); fn2()
            cmds.setParent('..')
        
        # and call it like this:
        two_col_row_small(
            "Base Y:", lambda: setattr(self, 'hands_base_y_field', cmds.floatField(value=self.hands_base_y)),
            "Flap (Y @ 1/4):", lambda: setattr(self, 'hands_flap_field', cmds.floatField(value=self.hands_flap))
        )

        
        cmds.setParent('..')  # end frameLayout



        # Root Movement
        cmds.frameLayout(label="Root Movement (RootX_M)", collapsable=True, marginWidth=10)
        two_col_row(
            "Up/Down Base (translateZ):", lambda: setattr(self, 'root_updown_base_field', cmds.floatField(value=self.root_updown_base)),
            "Up/Down Mid (translateZ):",  lambda: setattr(self, 'root_updown_mid_field',  cmds.floatField(value=self.root_updown_mid))
        )
        two_col_row(
            "Back/Forth Base (rotateX):", lambda: setattr(self, 'root_backforth_base_field', cmds.floatField(value=self.root_backforth_base)),
            "Back/Forth Mid (rotateX):",  lambda: setattr(self, 'root_backforth_mid_field',  cmds.floatField(value=self.root_backforth_mid))
        )
        cmds.setParent('..')

        # Scapula Flap (updated pattern)
        cmds.frameLayout(label="Scapula Flap (FKScapula_* rotateZ: 0 -> Base@1/4 -> Mid@3/4 -> 0)", collapsable=True, marginWidth=10)
        two_col_row(
            "Flap Base (rotateZ @ 1/4):", lambda: setattr(self, 'scap_flap_base_field', cmds.floatField(value=self.scap_flap_base)),
            "Flap Mid (rotateZ @ 3/4):",  lambda: setattr(self, 'scap_flap_mid_field',  cmds.floatField(value=self.scap_flap_mid))
        )
        cmds.setParent('..')

        # Elbow Poles (PoleArm_* translates)
        cmds.frameLayout(label="Elbow Poles (PoleArm_* translates)", collapsable=True, marginWidth=10)
        
        def three_col_row(label1, fn1, label2, fn2, label3, fn3):
            cmds.rowLayout(numberOfColumns=6,
                           columnWidth6=(220, 90, 140, 90, 100, 90),
                           adjustableColumn=6)
            cmds.text(label=label1); fn1()
            cmds.text(label=label2); fn2()
            cmds.text(label=label3); fn3()
            cmds.setParent('..')
        
        three_col_row(
            "X Offset (L=+, R=- mirrored):",
            lambda: setattr(self, 'pole_off_x_field',  cmds.floatField(value=self.pole_off_x)),
            "X Base:",
            lambda: setattr(self, 'pole_base_x_field', cmds.floatField(value=self.pole_base_x)),
            "X Mid:",
            lambda: setattr(self, 'pole_mid_x_field',  cmds.floatField(value=self.pole_mid_x)),
        )
        
        three_col_row(
            "Y Offset:",
            lambda: setattr(self, 'pole_off_y_field',  cmds.floatField(value=self.pole_off_y)),
            "Y Base:",
            lambda: setattr(self, 'pole_base_y_field', cmds.floatField(value=self.pole_base_y)),
            "Y Mid:",
            lambda: setattr(self, 'pole_mid_y_field',  cmds.floatField(value=self.pole_mid_y)),
        )
        
        three_col_row(
            "Z Offset:",
            lambda: setattr(self, 'pole_off_z_field',  cmds.floatField(value=self.pole_off_z)),
            "Z Base:",
            lambda: setattr(self, 'pole_base_z_field', cmds.floatField(value=self.pole_base_z)),
            "Z Mid:",
            lambda: setattr(self, 'pole_mid_z_field',  cmds.floatField(value=self.pole_mid_z)),
        )
        
        cmds.setParent('..')  # end frameLayout


        # FK IK Blend
        cmds.frameLayout(label="FK IK Blend", collapsable=True, marginWidth=10)
        self.fkik_blend_slider = cmds.floatSlider(min=0.0, max=10.0, value=self.fkik_blend_value, step=0.1)
        cmds.setParent('..')

        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(320, 320, 320), adjustableColumn=3)
        cmds.button(label="Generate Flight", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)


# To run:
FlightGenerator().show()
