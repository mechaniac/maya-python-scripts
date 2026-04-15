import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class SideStepGenerator(AnimGeneratorBase):
    WINDOW_NAME = "SideStepGeneratorWindow"
    WINDOW_TITLE = "Side Step Generator"
    WINDOW_SIZE = (640, 1020)

    def __init__(self):
        super().__init__()
        self.mirror = False
        self.root = "RootX_M"
        self.leg_r = "IKLeg_R"; self.leg_l = "IKLeg_L"
        self.hip = "HipSwinger_M"
        self.spine = "FKSpine1_M"; self.chest = "FKChest_M"
        self.neck = "FKNeck_M"; self.head = "FKHead_M"
        self.scapula_l = "FKScapula_L"; self.scapula_r = "FKScapula_R"
        self.shoulder_l = "FKShoulder_L"; self.shoulder_r = "FKShoulder_R"
        self.elbow_l = "FKElbow_L"; self.elbow_r = "FKElbow_R"
        self.wrist_l = "FKWrist_L"; self.wrist_r = "FKWrist_R"

        self.step_width = 5.0; self.step_height = 2.0
        self.root_tilt = 5.0; self.root_bounce = 1.0; self.root_offset_y = 0.0
        self.scapula_swing = 10.0; self.shoulder_swing = 5.0; self.elbow_swing = 5.0
        self.hip_sway = 3.0; self.spine_sway = 2.0; self.chest_sway = 1.5
        self.neck_sway = 1.0; self.head_sway = 0.5

        self.down_scapula_y = 0.0; self.down_shoulder_y = 0.0
        self.down_elbow_y = 0.0; self.down_wrist_y = 0.0
        self.bent_scapula_z = 0.0; self.bent_shoulder_z = 0.0
        self.bent_elbow_z = 0.0; self.bent_wrist_z = 0.0
        self.twist_scapula_x = 0.0; self.twist_shoulder_x = 0.0
        self.twist_elbow_x = 0.0; self.twist_wrist_x = 0.0

    def _dir(self):
        return -1 if self.mirror else 1

    def clear_keys(self):
        attrs = ['translateX', 'translateY', 'rotateX', 'rotateY', 'rotateZ']
        controls = [self.root, self.leg_r, self.leg_l, self.hip,
                    self.spine, self.chest, self.neck, self.head,
                    self.scapula_l, self.scapula_r,
                    self.shoulder_l, self.shoulder_r, self.elbow_l, self.elbow_r,
                    self.wrist_l, self.wrist_r]
        self.clear_keys_on(controls, attrs)

    def set_leg_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        step_x = d * self.step_width; lift_y = self.step_height
        first  = self.leg_r if self.mirror else self.leg_l
        second = self.leg_l if self.mirror else self.leg_r
        self.set_key(first, 'translateX', start, 0); self.set_key(first, 'translateY', start, 0)
        self.set_key(first, 'translateY', quarter, lift_y)
        self.set_key(first, 'translateX', mid, step_x); self.set_key(first, 'translateY', mid, 0)
        self.set_key(first, 'translateX', end, 0); self.set_key(first, 'translateY', end, 0)
        self.set_key(second, 'translateX', start, 0); self.set_key(second, 'translateY', start, 0)
        self.set_key(second, 'translateX', mid, 0); self.set_key(second, 'translateY', mid, 0)
        self.set_key(second, 'translateY', three_quarter, lift_y)
        self.set_key(second, 'translateX', three_quarter, step_x * 0.5)
        self.set_key(second, 'translateX', end, 0); self.set_key(second, 'translateY', end, 0)

    def set_root_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir(); off = self.root_offset_y
        self.set_key(self.root, 'translateZ', start, 0)
        self.set_key(self.root, 'translateZ', mid, d * (self.step_width * 0.5))
        self.set_key(self.root, 'translateZ', end, 0)
        self.set_key(self.root, 'rotateY', start, 0)
        self.set_key(self.root, 'rotateY', quarter, d * self.root_tilt)
        self.set_key(self.root, 'rotateY', mid, 0)
        self.set_key(self.root, 'rotateY', three_quarter, -d * self.root_tilt)
        self.set_key(self.root, 'rotateY', end, 0)
        self.set_key(self.root, 'translateX', start, off)
        self.set_key(self.root, 'translateX', quarter, off + self.root_bounce)
        self.set_key(self.root, 'translateX', mid, off)
        self.set_key(self.root, 'translateX', three_quarter, off + self.root_bounce)
        self.set_key(self.root, 'translateX', end, off)

    def set_scapula_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d = self._dir(); s = self.scapula_swing * d
        addY = float(self.down_scapula_y); addZ = float(self.bent_scapula_z); addX = float(self.twist_scapula_x)
        for node, sign in [(self.scapula_l, +1), (self.scapula_r, -1)]:
            self.set_key(node, 'rotateZ', start, sign * s + addY)
            self.set_key(node, 'rotateZ', mid, -sign * s + addY)
            self.set_key(node, 'rotateZ', end, sign * s + addY)
            for t in (start, mid, end):
                self.set_key(node, 'rotateY', t, addZ)
                self.set_key(node, 'rotateX', t, addX)

    def set_shoulder_elbow_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        d = self._dir(); shZ = self.shoulder_swing * d; elZ = self.elbow_swing * d
        addY_sh = float(self.down_shoulder_y); addZ_sh = float(self.bent_shoulder_z); addX_sh = float(self.twist_shoulder_x)
        addY_el = float(self.down_elbow_y); addZ_el = float(self.bent_elbow_z); addX_el = float(self.twist_elbow_x)
        addY_wr = float(self.down_wrist_y); addZ_wr = float(self.bent_wrist_z); addX_wr = float(self.twist_wrist_x)
        for (shoulder, elbow, wrist, sign) in [
            (self.shoulder_l, self.elbow_l, self.wrist_l, +1),
            (self.shoulder_r, self.elbow_r, self.wrist_r, -1),
        ]:
            self.set_key(shoulder, 'rotateZ', start, sign * shZ + addZ_sh)
            self.set_key(shoulder, 'rotateZ', mid, -sign * shZ + addZ_sh)
            self.set_key(shoulder, 'rotateZ', end, sign * shZ + addZ_sh)
            for t in (start, mid, end):
                self.set_key(shoulder, 'rotateY', t, addY_sh)
                self.set_key(shoulder, 'rotateX', t, addX_sh)
            self.set_key(elbow, 'rotateZ', start, sign * elZ + addZ_el)
            self.set_key(elbow, 'rotateZ', mid, -sign * elZ + addZ_el)
            self.set_key(elbow, 'rotateZ', end, sign * elZ + addZ_el)
            for t in (start, mid, end):
                self.set_key(elbow, 'rotateY', t, addY_el)
                self.set_key(elbow, 'rotateX', t, addX_el)
            for t in (start, mid, end):
                self.set_key(wrist, 'rotateY', t, addY_wr)
                self.set_key(wrist, 'rotateZ', t, addZ_wr)
                self.set_key(wrist, 'rotateX', t, addX_wr)

    def set_sidewhip_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        d = self._dir()
        for ctrl, amount in [(self.hip, self.hip_sway), (self.spine, self.spine_sway),
                             (self.chest, self.chest_sway), (self.neck, self.neck_sway),
                             (self.head, self.head_sway)]:
            a = d * amount
            self.set_key(ctrl, 'rotateY', start, 0)
            self.set_key(ctrl, 'rotateY', quarter, a)
            self.set_key(ctrl, 'rotateY', mid, 0)
            self.set_key(ctrl, 'rotateY', three_quarter, -a)
            self.set_key(ctrl, 'rotateY', end, 0)

    def generate(self):
        self.clear_keys(); self.compute_frames()
        self.set_leg_keys(); self.set_root_keys()
        self.set_scapula_keys(); self.set_shoulder_elbow_keys()
        self.set_sidewhip_keys()

    def _get_settings_dict(self):
        return {k: getattr(self, k) for k in [
            'mirror', 'step_width', 'step_height', 'root_tilt', 'root_bounce', 'root_offset_y',
            'scapula_swing', 'shoulder_swing', 'elbow_swing',
            'hip_sway', 'spine_sway', 'chest_sway', 'neck_sway', 'head_sway',
            'down_scapula_y', 'down_shoulder_y', 'down_elbow_y', 'down_wrist_y',
            'bent_scapula_z', 'bent_shoulder_z', 'bent_elbow_z', 'bent_wrist_z',
            'twist_scapula_x', 'twist_shoulder_x', 'twist_elbow_x', 'twist_wrist_x',
        ]}

    def print_settings(self, *args):
        self.print_settings_json("SideStepGenerator", self._get_settings_dict())

    def apply_settings(self, settings):
        for k in settings:
            if hasattr(self, k):
                setattr(self, k, settings[k])

    def prompt_and_apply_settings(self, *args):
        self.prompt_and_apply(lambda s: (self.apply_settings(s), self.show()))

    def on_generate(self, *args):
        self.mirror = cmds.checkBox(self.mirror_field, q=True, v=True)
        for attr in ['step_width', 'step_height', 'root_tilt', 'root_bounce', 'root_offset_y',
                      'scapula_swing', 'shoulder_swing', 'elbow_swing',
                      'hip_sway', 'spine_sway', 'chest_sway', 'neck_sway', 'head_sway',
                      'down_scapula_y', 'down_shoulder_y', 'down_elbow_y', 'down_wrist_y',
                      'bent_scapula_z', 'bent_shoulder_z', 'bent_elbow_z', 'bent_wrist_z',
                      'twist_scapula_x', 'twist_shoulder_x', 'twist_elbow_x', 'twist_wrist_x']:
            setattr(self, attr, cmds.floatField(getattr(self, attr + '_field'), q=True, v=True))
        self.generate()

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE, widthHeight=self.WINDOW_SIZE)
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        cmds.frameLayout(label="Direction", collapsable=False, marginWidth=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 300))
        cmds.text(label="Mirror (ON = Step Right, OFF = Step Left):")
        self.mirror_field = cmds.checkBox(value=self.mirror)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Step Settings", collapsable=True, marginWidth=10)
        self.two_col_row("Step Width (X):", lambda: setattr(self, 'step_width_field', cmds.floatField(value=self.step_width, bgc=self.COLOR_X)),
                         "Step Height (Y):", lambda: setattr(self, 'step_height_field', cmds.floatField(value=self.step_height, bgc=self.COLOR_Y)))
        cmds.setParent('..')

        cmds.frameLayout(label="Root Settings", collapsable=True, marginWidth=10)
        self.two_col_row("Root Tilt (rotateZ):", lambda: setattr(self, 'root_tilt_field', cmds.floatField(value=self.root_tilt, bgc=self.COLOR_Z)),
                         "Root Bounce (translateY):", lambda: setattr(self, 'root_bounce_field', cmds.floatField(value=self.root_bounce, bgc=self.COLOR_Y)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Root Offset (translateY):"); self.root_offset_y_field = cmds.floatField(value=self.root_offset_y, bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Arm / Scapula Animation", collapsable=True, marginWidth=10)
        self.two_col_row("Scapula Swing (rotateZ):", lambda: setattr(self, 'scapula_swing_field', cmds.floatField(value=self.scapula_swing, bgc=self.COLOR_Z)),
                         "Shoulder Swing (rotateY):", lambda: setattr(self, 'shoulder_swing_field', cmds.floatField(value=self.shoulder_swing, bgc=self.COLOR_Y)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Elbow Bend (rotateY):"); self.elbow_swing_field = cmds.floatField(value=self.elbow_swing, bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="SideWhip (Torso)", collapsable=True, marginWidth=10)
        self.two_col_row("Hip Sway (rotateX):", lambda: setattr(self, 'hip_sway_field', cmds.floatField(value=self.hip_sway, bgc=self.COLOR_X)),
                         "Spine Sway (rotateX):", lambda: setattr(self, 'spine_sway_field', cmds.floatField(value=self.spine_sway, bgc=self.COLOR_X)))
        self.two_col_row("Chest Sway (rotateX):", lambda: setattr(self, 'chest_sway_field', cmds.floatField(value=self.chest_sway, bgc=self.COLOR_X)),
                         "Neck Sway (rotateX):", lambda: setattr(self, 'neck_sway_field', cmds.floatField(value=self.neck_sway, bgc=self.COLOR_X)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 100))
        cmds.text(label="Head Sway (rotateX):"); self.head_sway_field = cmds.floatField(value=self.head_sway, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Arms Down (rotateZ, both arms)", collapsable=True, marginWidth=10)
        self.two_col_row("Scapula Down (Z):", lambda: setattr(self, 'down_scapula_y_field', cmds.floatField(value=self.down_scapula_y, bgc=self.COLOR_Z)),
                         "Shoulder Down (Z):", lambda: setattr(self, 'down_shoulder_y_field', cmds.floatField(value=self.down_shoulder_y, bgc=self.COLOR_Z)))
        self.two_col_row("Elbow Down (Z):", lambda: setattr(self, 'down_elbow_y_field', cmds.floatField(value=self.down_elbow_y, bgc=self.COLOR_Z)),
                         "Wrist Down (Z):", lambda: setattr(self, 'down_wrist_y_field', cmds.floatField(value=self.down_wrist_y, bgc=self.COLOR_Z)))
        cmds.setParent('..')

        cmds.frameLayout(label="Arms Bent (rotateY, both arms)", collapsable=True, marginWidth=10)
        self.two_col_row("Scapula Bent (Y):", lambda: setattr(self, 'bent_scapula_z_field', cmds.floatField(value=self.bent_scapula_z, bgc=self.COLOR_Y)),
                         "Shoulder Bent (Y):", lambda: setattr(self, 'bent_shoulder_z_field', cmds.floatField(value=self.bent_shoulder_z, bgc=self.COLOR_Y)))
        self.two_col_row("Elbow Bent (Y):", lambda: setattr(self, 'bent_elbow_z_field', cmds.floatField(value=self.bent_elbow_z, bgc=self.COLOR_Y)),
                         "Wrist Bent (Y):", lambda: setattr(self, 'bent_wrist_z_field', cmds.floatField(value=self.bent_wrist_z, bgc=self.COLOR_Y)))
        cmds.setParent('..')

        cmds.frameLayout(label="Arms Twist (rotateX, both arms)", collapsable=True, marginWidth=10)
        self.two_col_row("Scapula Twist (X):", lambda: setattr(self, 'twist_scapula_x_field', cmds.floatField(value=self.twist_scapula_x, bgc=self.COLOR_X)),
                         "Shoulder Twist (X):", lambda: setattr(self, 'twist_shoulder_x_field', cmds.floatField(value=self.twist_shoulder_x, bgc=self.COLOR_X)))
        self.two_col_row("Elbow Twist (X):", lambda: setattr(self, 'twist_elbow_x_field', cmds.floatField(value=self.twist_elbow_x, bgc=self.COLOR_X)),
                         "Wrist Twist (X):", lambda: setattr(self, 'twist_wrist_x_field', cmds.floatField(value=self.twist_wrist_x, bgc=self.COLOR_X)))
        cmds.setParent('..')

        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200), adjustableColumn=3)
        cmds.button(label="Generate Side Step", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')
        cmds.showWindow(self.window)
