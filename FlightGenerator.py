# FlightGenerator.py  (Maya Python 2 / 2018)
import maya.cmds as cmds
import json

class FlightGenerator:
    def __init__(self):
        self.window = "FlightGeneratorWindow"

        # Controls (resolved case-insensitively when keying)
        self.ik_arm_l = "IKArm_L"
        self.ik_arm_r = "IKArm_R"
        self.fkik_l   = "FKIKArm_L"
        self.fkik_r   = "FKIKArm_R"

        # Params
        # IKArm_*.translateZ pattern:
        # start: 0, quarter: down, three_quarters: up, end: 0
        self.ik_arms_down = 5.0
        self.ik_arms_up   = 2.5

        # IKArm_*.rotateX constant (start=end=input)
        self.arm_rotateX_value = 10.0

        # Hand Flap on IKArm_*.rotateY:
        # start: 0, half: down, three_quarters: up, end: 0
        self.hand_flap_down = 8.0
        self.hand_flap_up   = -4.0

        # FK/IK blend (0..10) on FKIKArm_*.FKIKBlend (constant, keyed start & end)
        self.fkik_blend_value = 10.0

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
            raise RuntimeError("Playback range invalid (start >= end). Set a valid timeline range.")
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
            (self.ik_arm_l, ["translateZ", "rotateX", "rotateY"]),
            (self.ik_arm_r, ["translateZ", "rotateX", "rotateY"]),
            (self.fkik_l,   ["FKIKBlend"]),
            (self.fkik_r,   ["FKIKBlend"]),
        ]:
            resolved = self.resolve_node_case_insensitive(node) or node
            for a in attrs:
                self.cut_attr_keys_in_range(resolved, a, s, e, reset_to_zero=True)

    def key_arms(self):
        start, quarter, mid, three_quarter, end = self.frames

        # IKArm_*.translateZ: 0 -> down -> up -> 0   (at start, 1/4, 3/4, end)
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
        start, quarter, mid, three_quarter, end = self.frames
    
        # Hand flap (IKArm_*.rotateY):
        # start: 0, half: ±down, three_quarters: ±up, end: 0
        # Left = +, Right = -
        pairs = [(self.ik_arm_l, +1.0), (self.ik_arm_r, -1.0)]
        for node, sgn in pairs:
            self.set_key(node, "rotateY", start, 0.0)
            self.set_key(node, "rotateY", mid,   sgn * float(self.hand_flap_down))
            self.set_key(node, "rotateY", three_quarter, sgn * float(self.hand_flap_up))
            self.set_key(node, "rotateY", end,   0.0)



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
        self.key_fkik_blend()
        self.print_settings()
        try:
            cmds.inViewMessage(amg='[FlightGenerator] Keys generated (arms Z, hand flap Y, FK/IK).', pos='midCenter', fade=True)
        except Exception:
            pass

    # ---------- settings I/O & UI ----------
    def print_settings(self, *args):
        settings = {
            'ik_arms_down':      self.ik_arms_down,
            'ik_arms_up':        self.ik_arms_up,
            'arm_rotateX_value': self.arm_rotateX_value,
            'hand_flap_down':    self.hand_flap_down,
            'hand_flap_up':      self.hand_flap_up,
            'fkik_blend_value':  self.fkik_blend_value,
        }
        print("// FlightGenerator Settings:\n" + json.dumps(settings, indent=2))

    def apply_settings(self, settings):
        for k, v in settings.items():
            if hasattr(self, k):
                setattr(self, k, v)

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
        self.ik_arms_down      = cmds.floatField(self.ik_arms_down_field, q=True, v=True)
        self.ik_arms_up        = cmds.floatField(self.ik_arms_up_field,   q=True, v=True)
        self.arm_rotateX_value = cmds.floatField(self.arm_rotateX_field,  q=True, v=True)

        self.hand_flap_down    = cmds.floatField(self.hand_flap_down_field, q=True, v=True)
        self.hand_flap_up      = cmds.floatField(self.hand_flap_up_field,   q=True, v=True)

        self.fkik_blend_value  = cmds.floatSlider(self.fkik_blend_slider, q=True, v=True)
        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Flight Generator", widthHeight=(480, 360), sizeable=True)
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(200, 100, 200, 100), adjustableColumn=4)
            cmds.text(label=label1); field_fn1()
            cmds.text(label=label2); field_fn2()
            cmds.setParent('..')

        # IK Arms (translateZ) + rotateX constant
        cmds.frameLayout(label="IK Arms", collapsable=True, marginWidth=10)
        two_col_row(
            "IK Arms down (translateZ @ 1/4):", lambda: setattr(self, 'ik_arms_down_field', cmds.floatField(value=self.ik_arms_down)),
            "IK Arms up (translateZ @ 3/4):",   lambda: setattr(self, 'ik_arms_up_field',   cmds.floatField(value=self.ik_arms_up))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 100))
        cmds.text(label="IK Arms rotateX (start=end):")
        self.arm_rotateX_field = cmds.floatField(value=self.arm_rotateX_value)
        cmds.setParent('..')
        cmds.setParent('..')

        # Hand Flap (rotateY)
        cmds.frameLayout(label="Hand Flap (IK rotateY)", collapsable=True, marginWidth=10)
        two_col_row(
            "Hand Flap down (mid):",   lambda: setattr(self, 'hand_flap_down_field', cmds.floatField(value=self.hand_flap_down)),
            "Hand Flap up (3/4):",     lambda: setattr(self, 'hand_flap_up_field',   cmds.floatField(value=self.hand_flap_up))
        )
        cmds.setParent('..')

        # FK IK Blend
        cmds.frameLayout(label="FK IK Blend", collapsable=True, marginWidth=10)
        self.fkik_blend_slider = cmds.floatSlider(min=0.0, max=10.0, value=self.fkik_blend_value, step=0.1)
        cmds.setParent('..')

        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200), adjustableColumn=3)
        cmds.button(label="Generate Flight", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)


# To run:
FlightGenerator().show()
