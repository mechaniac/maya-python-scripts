import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class HandSideStepGenerator(AnimGeneratorBase):
    WINDOW_NAME = "HandSideStepGeneratorWindow"
    WINDOW_TITLE = "Hand Side Step Generator"
    WINDOW_SIZE = (640, 920)

    def __init__(self):
        super().__init__()
        self.mirror = False
        self.stretch_arms = False

        self.root = "RootX_M"
        self.hand_r = "IKArm_R"; self.hand_l = "IKArm_L"
        self.hip = "HipSwinger_M"
        self.spine = "FKSpine1_M"; self.chest = "FKChest_M"
        self.neck = "FKNeck_M"; self.head = "FKHead_M"
        self.scapula_l = "FKScapula_L"; self.scapula_r = "FKScapula_R"

        self.fkik_leg_r = "FKIKLeg_R"; self.fkik_leg_l = "FKIKLeg_L"
        self.fk_hip_r = "FKHip_R"; self.fk_hip_l = "FKHip_L"
        self.fk_knee_r = "FKKnee_R"; self.fk_knee_l = "FKKnee_L"
        self.fk_foot_r = "FKFoot_R"; self.fk_foot_l = "FKFoot_L"
        self.fk_toe_r = "FKToe_R"; self.fk_toe_l = "FKToe_L"

        self.leg_fkik_blend = 10.0
        self.fk_hip_ry = 0.0; self.fk_knee_ry = 0.0
        self.fk_foot_ry = 0.0; self.fk_toe_ry = 0.0

        self.step_width = 5.0; self.step_height = 2.0
        self.ground_height = 0.0; self.step_narrowness = 0.0
        self.root_tilt = 5.0; self.root_bounce = 1.0; self.root_offset_y = 0.0
        self.scapula_swing = 0.0
        self.hip_sway = 3.0; self.spine_sway = 2.0; self.chest_sway = 1.5
        self.neck_sway = 1.0; self.head_sway = 0.5
        self.down_scapula_z = 0.0; self.bent_scapula_y = 0.0; self.twist_scapula_x = 0.0

    def _dir(self):
        return -1 if self.mirror else 1

    def clear_keys(self):
        attrs = ['translateX', 'translateY', 'rotateX', 'rotateY', 'rotateZ',
                 'stretchy', 'FKIKBlend']
        controls = [
            self.root, self.hand_r, self.hand_l,
            self.hip, self.spine, self.chest, self.neck, self.head,
            self.scapula_l, self.scapula_r,
            self.fkik_leg_r, self.fkik_leg_l,
            self.fk_hip_r, self.fk_hip_l, self.fk_knee_r, self.fk_knee_l,
            self.fk_foot_r, self.fk_foot_l, self.fk_toe_r, self.fk_toe_l,
        ]
        self.clear_keys_on(controls, attrs)

    # ---------- keying ----------
    def set_leg_fkik_blend_keys(self):
        start, end = self.frames[0], self.frames[4]
        for ctrl in (self.fkik_leg_l, self.fkik_leg_r):
            self.set_key(ctrl, 'FKIKBlend', start, self.leg_fkik_blend)
            self.set_key(ctrl, 'FKIKBlend', end, self.leg_fkik_blend)

    def set_leg_fk_pose_keys(self):
        start, end = self.frames[0], self.frames[4]
        pairs = [
            (self.fk_hip_l, self.fk_hip_r, self.fk_hip_ry),
            (self.fk_knee_l, self.fk_knee_r, self.fk_knee_ry),
            (self.fk_foot_l, self.fk_foot_r, self.fk_foot_ry),
            (self.fk_toe_l, self.fk_toe_r, self.fk_toe_ry),
        ]
        for L, R, v in pairs:
            self.set_key(L, 'rotateY', start, v); self.set_key(R, 'rotateY', start, v)
            self.set_key(L, 'rotateY', end, v); self.set_key(R, 'rotateY', end, v)

    def set_stretch_keys(self):
        if not self.stretch_arms:
            return
        start, end = self.frames[0], self.frames[4]
        for arm in (self.hand_l, self.hand_r):
            self.set_key(arm, 'stretchy', start, 10)
            self.set_key(arm, 'stretchy', end, 10)

    def set_hand_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        step_x = d * self.step_width
        base_y = self.ground_height; lift_y = self.ground_height + self.step_height
        first = self.hand_r if self.mirror else self.hand_l
        second = self.hand_l if self.mirror else self.hand_r

        hr = (self.resolve_node(self.hand_r) or self.hand_r).lower()
        hl = (self.resolve_node(self.hand_l) or self.hand_l).lower()
        offR = abs(self.step_narrowness); offL = -abs(self.step_narrowness)

        def x_with_narrow(node, base):
            ln = (self.resolve_node(node) or node).lower()
            return base + (offR if ln == hr else offL if ln == hl else 0.0)

        self.set_key(first, 'translateX', start, x_with_narrow(first, 0))
        self.set_key(first, 'translateY', start, base_y)
        self.set_key(first, 'translateY', quarter, lift_y)
        self.set_key(first, 'translateX', mid, x_with_narrow(first, step_x))
        self.set_key(first, 'translateY', mid, base_y)
        self.set_key(first, 'translateX', end, x_with_narrow(first, 0))
        self.set_key(first, 'translateY', end, base_y)

        self.set_key(second, 'translateX', start, x_with_narrow(second, 0))
        self.set_key(second, 'translateY', start, base_y)
        self.set_key(second, 'translateX', mid, x_with_narrow(second, 0))
        self.set_key(second, 'translateY', mid, base_y)
        self.set_key(second, 'translateY', three_quarter, lift_y)
        self.set_key(second, 'translateX', three_quarter, x_with_narrow(second, step_x * 0.5))
        self.set_key(second, 'translateX', end, x_with_narrow(second, 0))
        self.set_key(second, 'translateY', end, base_y)

    def clamp_hands_to_ground(self):
        for hand in (self.hand_l, self.hand_r):
            node = self.resolve_node(hand) or hand
            if not cmds.objExists(node) or not cmds.attributeQuery('translateY', node=node, exists=True):
                continue
            times = cmds.keyframe(node, at='translateY', q=True, tc=True) or []
            for t in set(times):
                v = cmds.keyframe(node, at='translateY', q=True, eval=True, t=(t, t))[0]
                if v < self.ground_height:
                    cmds.keyframe(node, at='translateY', e=True, t=(t, t), vc=self.ground_height)

    def set_root_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir(); off = self.root_offset_y
        self.set_key(self.root, 'translateX', start, 0)
        self.set_key(self.root, 'translateX', mid, d * (self.step_width * 0.5))
        self.set_key(self.root, 'translateX', end, 0)
        self.set_key(self.root, 'rotateZ', start, 0)
        self.set_key(self.root, 'rotateZ', quarter, d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', mid, 0)
        self.set_key(self.root, 'rotateZ', three_quarter, -d * self.root_tilt)
        self.set_key(self.root, 'rotateZ', end, 0)
        for t, v in [(start, off), (quarter, off + self.root_bounce), (mid, off),
                     (three_quarter, off + self.root_bounce), (end, off)]:
            self.set_key(self.root, 'translateY', t, v)

    def set_scapula_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d = self._dir(); s = self.scapula_swing * d
        addZ = abs(float(self.down_scapula_z))
        addY = abs(float(self.bent_scapula_y))
        addX = abs(float(self.twist_scapula_x))
        for node, sign in [(self.scapula_l, +1), (self.scapula_r, -1)]:
            self.set_key(node, 'rotateZ', start, sign * s + addZ)
            self.set_key(node, 'rotateZ', mid, -sign * s + addZ)
            self.set_key(node, 'rotateZ', end, sign * s + addZ)
            for t in (start, mid, end):
                self.set_key(node, 'rotateY', t, addY)
                self.set_key(node, 'rotateX', t, addX)

    def set_sidewhip_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        # HipSwinger stays world-aligned: rotateY unchanged
        a = d * self.hip_sway
        self.set_key(self.hip, 'rotateY', start, 0)
        self.set_key(self.hip, 'rotateY', quarter, a)
        self.set_key(self.hip, 'rotateY', mid, 0)
        self.set_key(self.hip, 'rotateY', three_quarter, -a)
        self.set_key(self.hip, 'rotateY', end, 0)
        # Spine/chest/neck/head FK: rotateY -> rotateX
        for ctrl, amount in [(self.spine, self.spine_sway),
                             (self.chest, self.chest_sway), (self.neck, self.neck_sway),
                             (self.head, self.head_sway)]:
            a = d * amount
            self.set_key(ctrl, 'rotateX', start, 0)
            self.set_key(ctrl, 'rotateX', quarter, a)
            self.set_key(ctrl, 'rotateX', mid, 0)
            self.set_key(ctrl, 'rotateX', three_quarter, -a)
            self.set_key(ctrl, 'rotateX', end, 0)

    def generate(self):
        self.clear_keys(); self.compute_frames()
        self.set_leg_fkik_blend_keys(); self.set_leg_fk_pose_keys()
        self.set_hand_keys(); self.set_root_keys()
        self.set_scapula_keys(); self.set_sidewhip_keys()
        self.clamp_hands_to_ground(); self.set_stretch_keys()

    # ---------- settings ----------
    def _get_settings_dict(self):
        return {k: getattr(self, k) for k in [
            'mirror', 'stretch_arms', 'step_width', 'step_height',
            'step_narrowness', 'ground_height', 'root_tilt', 'root_bounce',
            'root_offset_y', 'scapula_swing', 'hip_sway', 'spine_sway',
            'chest_sway', 'neck_sway', 'head_sway', 'down_scapula_z',
            'bent_scapula_y', 'twist_scapula_x', 'leg_fkik_blend',
            'fk_hip_ry', 'fk_knee_ry', 'fk_foot_ry', 'fk_toe_ry',
        ]}

    def print_settings(self, *args):
        self.print_settings_json("HandSideStepGenerator", self._get_settings_dict())

    def apply_settings(self, settings):
        if not isinstance(settings, dict):
            return
        for k in ('mirror', 'stretch_arms'):
            if k in settings:
                v = settings[k]
                if isinstance(v, bool):
                    setattr(self, k, v)
                elif isinstance(v, (int, float)):
                    setattr(self, k, bool(v))
                elif isinstance(v, str):
                    setattr(self, k, v.strip().lower() in ('1', 'true', 'yes', 'on'))
        float_keys = [
            'step_width', 'step_height', 'step_narrowness', 'ground_height',
            'root_tilt', 'root_bounce', 'root_offset_y', 'scapula_swing',
            'hip_sway', 'spine_sway', 'chest_sway', 'neck_sway', 'head_sway',
            'down_scapula_z', 'bent_scapula_y', 'twist_scapula_x',
            'leg_fkik_blend', 'fk_hip_ry', 'fk_knee_ry', 'fk_foot_ry', 'fk_toe_ry',
        ]
        for k in float_keys:
            if k in settings:
                try:
                    setattr(self, k, float(settings[k]))
                except (ValueError, TypeError):
                    pass

    def prompt_and_apply_settings(self, *args):
        self.prompt_and_apply(lambda s: (self.apply_settings(s), self.show()))

    # ---------- UI ----------
    def on_generate(self, *args):
        self.mirror = cmds.checkBox(self.mirror_field, q=True, v=True)
        self.stretch_arms = cmds.checkBox(self.stretch_arms_field, q=True, v=True)
        for attr in ['step_width', 'step_height', 'step_narrowness', 'ground_height',
                      'root_tilt', 'root_bounce', 'root_offset_y', 'scapula_swing',
                      'hip_sway', 'spine_sway', 'chest_sway', 'neck_sway', 'head_sway',
                      'down_scapula_z', 'bent_scapula_y', 'twist_scapula_x',
                      'fk_hip_ry', 'fk_knee_ry', 'fk_foot_ry', 'fk_toe_ry']:
            setattr(self, attr, cmds.floatField(getattr(self, attr + '_field'), q=True, v=True))
        self.leg_fkik_blend = cmds.floatSlider(self.leg_fkik_blend_slider, q=True, value=True)
        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE, widthHeight=self.WINDOW_SIZE)
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        # Direction
        cmds.frameLayout(label="Direction", collapsable=False, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 300))
        cmds.text(label="Mirror (ON = Step Right, OFF = Step Left):")
        self.mirror_field = cmds.checkBox(value=self.mirror)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(220, 100))
        cmds.text(label="Stretch Arms (keys .stretchy=10):")
        self.stretch_arms_field = cmds.checkBox(value=self.stretch_arms)
        cmds.setParent('..')

        # Step Settings (Hands)
        cmds.frameLayout(label="Step Settings (Hands)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Step Width (X):", lambda: setattr(self, 'step_width_field', cmds.floatField(value=self.step_width, bgc=self.COLOR_X)),
            "Step Height (Y):", lambda: setattr(self, 'step_height_field', cmds.floatField(value=self.step_height, bgc=self.COLOR_Y)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Ground Height (Y):"); self.ground_height_field = cmds.floatField(value=self.ground_height, bgc=self.COLOR_Y)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Step Narrowness (X):"); self.step_narrowness_field = cmds.floatField(value=self.step_narrowness, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # Root
        cmds.frameLayout(label="Root Settings", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Root Tilt (rotateZ):", lambda: setattr(self, 'root_tilt_field', cmds.floatField(value=self.root_tilt, bgc=self.COLOR_Z)),
            "Root Bounce (translateY):", lambda: setattr(self, 'root_bounce_field', cmds.floatField(value=self.root_bounce, bgc=self.COLOR_Y)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 100))
        cmds.text(label="Root Offset (translateY, signed):"); self.root_offset_y_field = cmds.floatField(value=self.root_offset_y, bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        # Scapula
        cmds.frameLayout(label="Scapula Animation", collapsable=True, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Scapula Swing (rotateZ):"); self.scapula_swing_field = cmds.floatField(value=self.scapula_swing, bgc=self.COLOR_Z)
        cmds.setParent('..')
        self.two_col_row(
            "Scapula Down (Z, add |v|):", lambda: setattr(self, 'down_scapula_z_field', cmds.floatField(value=self.down_scapula_z, bgc=self.COLOR_Z)),
            "Scapula Bent (Y, add |v|):", lambda: setattr(self, 'bent_scapula_y_field', cmds.floatField(value=self.bent_scapula_y, bgc=self.COLOR_Y)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Scapula Twist (X, add |v|):"); self.twist_scapula_x_field = cmds.floatField(value=self.twist_scapula_x, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # SideWhip
        cmds.frameLayout(label="SideWhip (Torso)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Hip Sway (rotateY):", lambda: setattr(self, 'hip_sway_field', cmds.floatField(value=self.hip_sway, bgc=self.COLOR_Y)),
            "Spine Sway (rotateX):", lambda: setattr(self, 'spine_sway_field', cmds.floatField(value=self.spine_sway, bgc=self.COLOR_X)))
        self.two_col_row(
            "Chest Sway (rotateX):", lambda: setattr(self, 'chest_sway_field', cmds.floatField(value=self.chest_sway, bgc=self.COLOR_X)),
            "Neck Sway (rotateX):", lambda: setattr(self, 'neck_sway_field', cmds.floatField(value=self.neck_sway, bgc=self.COLOR_X)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Head Sway (rotateX):"); self.head_sway_field = cmds.floatField(value=self.head_sway, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # Legs FK
        cmds.frameLayout(label="Legs FK Pose", collapsable=True, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200))
        cmds.text(label="FK/IK Blend (0..10):")
        self.leg_fkik_blend_slider = cmds.floatSlider(min=0, max=10, value=self.leg_fkik_blend, step=0.1)
        cmds.setParent('..')
        self.two_col_row(
            "Hip rotateY:", lambda: setattr(self, 'fk_hip_ry_field', cmds.floatField(value=self.fk_hip_ry, bgc=self.COLOR_Y)),
            "Knee rotateY:", lambda: setattr(self, 'fk_knee_ry_field', cmds.floatField(value=self.fk_knee_ry, bgc=self.COLOR_Y)))
        self.two_col_row(
            "Foot rotateY:", lambda: setattr(self, 'fk_foot_ry_field', cmds.floatField(value=self.fk_foot_ry, bgc=self.COLOR_Y)),
            "Toe rotateY:", lambda: setattr(self, 'fk_toe_ry_field', cmds.floatField(value=self.fk_toe_ry, bgc=self.COLOR_Y)))
        cmds.setParent('..')

        # Buttons
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200), adjustableColumn=3)
        cmds.button(label="Generate Hand Side Step", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')
        cmds.showWindow(self.window)
