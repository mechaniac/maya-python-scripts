import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class WalkCycleTool(AnimGeneratorBase):
    WINDOW_NAME = "WalkCycleWindow"
    WINDOW_TITLE = "Walk Cycle Tool"
    WINDOW_SIZE = (800, 600)

    def __init__(self):
        super().__init__()
        self.stride = 10.0; self.stride_width = 2.0; self.stride_height = 4.0
        self.swing_extend = 10.0; self.hip_sway_lr = 5.0
        self.root_bounce = 1.5; self.root_sway = 2.0; self.root_rock = 1.0
        self.foot_raise = 10.0; self.root_bounce_offset = 0.0
        self.root_twist = 0.0; self.root_rock_offset = 0.0
        self.root_backforth = 0.0; self.root_leftright = 0.0
        self.leg_stretch_L = 0.0; self.leg_stretch_R = 0.0

        self.arm_params = {
            'shoulder_down_y': -30.0, 'scapula_down': -15.0,
            'scapula_z': 8.0, 'shoulder_z': 20.0, 'shoulder_x': 0.0,
            'elbow_z': 12.0, 'wrist_z': 6.0,
        }
        self.upper_body_params = {
            'spine1': {'name': 'FKSpine1_M', 'rx': 5.0, 'ry': 2.0, 'rz': 1.5, 'rz_offset': 0.0},
            'chest':  {'name': 'FKChest_M',  'rx': 7.0, 'ry': 3.0, 'rz': 2.0, 'rz_offset': 0.0},
            'neck':   {'name': 'FKNeck_M',   'rx': 4.0, 'ry': 2.0, 'rz': 1.0, 'rz_offset': 0.0},
            'head':   {'name': 'FKHead_M',   'rx': 3.0, 'ry': 1.5, 'rz': 1.5, 'rz_offset': 0.0},
        }
        self.frames_stride_halved = []
        self.quarter = 0; self.three_quarter = 0
        self.limbs = {
            'right_leg': "IKLeg_R", 'left_leg': "IKLeg_L",
            'hip': "HipSwinger_M", 'root': "RootX_M",
        }
        self.arm_ctrls = {
            'scapula': "FKScapula_R", 'shoulder': "FKShoulder_R",
            'elbow': "FKElbow_R", 'wrist': "FKWrist_R",
        }

    # ---------- frame data ----------
    def compute_frame_data(self):
        start, end = self.timeline_range()
        mid = (start + end) / 2.0
        self.quarter = (start + mid) / 2.0
        self.three_quarter = (mid + end) / 2.0
        self.frames_stride_halved = [
            (start,  self.stride / 2.0, -self.stride / 2.0),
            (mid,   -self.stride / 2.0,  self.stride / 2.0),
            (end,    self.stride / 2.0, -self.stride / 2.0),
        ]

    def apply_keyframe_pattern(self, obj_attr, values_per_frame):
        obj, attr = obj_attr
        for (t, *_), v in zip(self.frames_stride_halved, values_per_frame):
            self.set_key(obj, attr, t, v)

    # ---------- clear ----------
    def clear_keys(self):
        start, end = self.timeline_range()
        attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        all_controls = list(self.limbs.values()) + [d['name'] for d in self.upper_body_params.values()]
        all_controls += list(self.arm_ctrls.values())
        all_controls += [c.replace('_R', '_L') for c in self.arm_ctrls.values()]
        for ctrl in all_controls:
            for attr in attrs:
                if cmds.objExists(ctrl) and cmds.attributeQuery(attr, node=ctrl, exists=True):
                    cmds.cutKey(ctrl, at=attr, time=(start, end))

    # ---------- keying ----------
    def set_leg_stretch_keys(self):
        start, end = self.timeline_range()
        for node, val in [(self.limbs['left_leg'], self.leg_stretch_L),
                          (self.limbs['right_leg'], self.leg_stretch_R)]:
            if not cmds.objExists(node):
                continue
            if not cmds.attributeQuery('stretchy', node=node, exists=True):
                continue
            try:
                cmds.cutKey(node, at='stretchy', time=(start, end))
            except Exception:
                pass
            cmds.setAttr(f"{node}.stretchy", val)
            self.set_key(node, 'stretchy', start, val)
            self.set_key(node, 'stretchy', end, val)

    def set_feet_keys(self):
        r = self.limbs['right_leg']; l = self.limbs['left_leg']
        rz = [f[1] for f in self.frames_stride_halved]
        lz = [f[2] for f in self.frames_stride_halved]
        self.apply_keyframe_pattern((r, 'translateZ'), rz)
        self.apply_keyframe_pattern((l, 'translateZ'), lz)
        self.apply_keyframe_pattern((r, 'translateX'), [self.stride_width] * 3)
        self.apply_keyframe_pattern((l, 'translateX'), [-self.stride_width] * 3)
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        self.set_key(l, 'translateY', self.quarter, self.stride_height)
        self.set_key(r, 'translateY', self.three_quarter, self.stride_height)
        for t in [start, mid, end]:
            self.set_key(l, 'translateY', t, 0)
            self.set_key(r, 'translateY', t, 0)

    def set_foot_raise_keys(self):
        leg_l = self.limbs['left_leg']; leg_r = self.limbs['right_leg']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter
        self.set_key(leg_l, 'rotateX', start, 0)
        self.set_key(leg_l, 'rotateX', q, 0)
        self.set_key(leg_l, 'rotateX', (q + mid) / 2.0, self.foot_raise)
        self.set_key(leg_l, 'rotateX', mid, 0)
        self.set_key(leg_l, 'rotateX', tq, 0)
        self.set_key(leg_l, 'rotateX', end, 0)
        self.set_key(leg_r, 'rotateX', start, 0)
        self.set_key(leg_r, 'rotateX', q, 0)
        self.set_key(leg_r, 'rotateX', mid, 0)
        self.set_key(leg_r, 'rotateX', tq, 0)
        self.set_key(leg_r, 'rotateX', (tq + end) / 2.0, self.foot_raise)
        self.set_key(leg_r, 'rotateX', end, 0)

    def set_hip_swinger_keys(self):
        hip = self.limbs['hip']
        self.apply_keyframe_pattern((hip, 'rotateX'), [self.swing_extend, -self.swing_extend, self.swing_extend])
        self.apply_keyframe_pattern((hip, 'rotateY'), [self.hip_sway_lr, -self.hip_sway_lr, self.hip_sway_lr])

    def set_root_keys(self):
        root = self.limbs['root']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter
        bo = self.root_bounce_offset
        bounce = [self.root_bounce + bo, -self.root_bounce + bo,
                  self.root_bounce + bo, -self.root_bounce + bo,
                  self.root_bounce + bo]
        for t, v in zip([start, q, mid, tq, end], bounce):
            self.set_key(root, 'translateY', t, v)

        lr = [self.root_leftright, 0, -self.root_leftright, 0, self.root_leftright]
        for t, v in zip([start, q, mid, tq, end], lr):
            self.set_key(root, 'translateX', t, v)

        bf = [self.root_backforth, -self.root_backforth, self.root_backforth,
              -self.root_backforth, self.root_backforth]
        for t, v in zip([start, q, mid, tq, end], bf):
            self.set_key(root, 'translateZ', t, v)

        ro = self.root_rock_offset
        rx = [self.root_rock + ro, -self.root_rock + ro, self.root_rock + ro,
              -self.root_rock + ro, self.root_rock + ro]
        for t, v in zip([start, q, mid, tq, end], rx):
            self.set_key(root, 'rotateX', t, v)

        self.set_key(root, 'rotateY', start, self.root_sway)
        self.set_key(root, 'rotateY', mid, -self.root_sway)
        self.set_key(root, 'rotateY', end, self.root_sway)
        self.apply_keyframe_pattern((root, 'rotateZ'), [self.root_twist, -self.root_twist, self.root_twist])

    def set_spine_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter
        fifths = [start, q, mid, tq, end]
        for key, data in self.upper_body_params.items():
            ctrl = data['name']
            self.apply_keyframe_pattern((ctrl, 'rotateZ'), [data['rx'], -data['rx'], data['rx']])
            self.apply_keyframe_pattern((ctrl, 'rotateX'), [data['ry'], -data['ry'], data['ry']])
            rz = data['rz']; offset = data.get('rz_offset', 0)
            rz_vals = [rz + offset, -rz + offset, rz + offset, -rz + offset, rz + offset]
            for t, v in zip(fifths, rz_vals):
                self.set_key(ctrl, 'rotateY', t, v)

    def set_right_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        static_ry = self.arm_params['shoulder_down_y']
        cmds.setAttr(f"{self.arm_ctrls['shoulder']}.rotateZ", static_ry)
        self.set_key(self.arm_ctrls['shoulder'], 'rotateZ', start, static_ry)
        self.set_key(self.arm_ctrls['shoulder'], 'rotateZ', end, static_ry)

        sc = self.arm_ctrls['scapula']
        sd = self.arm_params['scapula_down']
        cmds.setAttr(f"{sc}.rotateZ", sd)
        self.set_key(sc, 'rotateZ', start, sd); self.set_key(sc, 'rotateZ', end, sd)

        x_vals = [self.arm_params['shoulder_x'], -self.arm_params['shoulder_x'], self.arm_params['shoulder_x']]
        self.apply_keyframe_pattern((self.arm_ctrls['shoulder'], 'rotateX'), x_vals)

        for key, ctrl in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                             ['scapula', 'shoulder', 'elbow', 'wrist']):
            val = self.arm_params[key]
            values = [0, val, 0] if key == 'elbow_z' else [val, -val, val]
            self.apply_keyframe_pattern((self.arm_ctrls[ctrl], 'rotateY'), values)

    def set_left_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        static_ry = self.arm_params['shoulder_down_y']
        l_sh = self.arm_ctrls['shoulder'].replace('_R', '_L')
        cmds.setAttr(f"{l_sh}.rotateZ", static_ry)
        self.set_key(l_sh, 'rotateZ', start, static_ry); self.set_key(l_sh, 'rotateZ', end, static_ry)

        l_sc = self.arm_ctrls['scapula'].replace('_R', '_L')
        sd = self.arm_params['scapula_down']
        cmds.setAttr(f"{l_sc}.rotateZ", sd)
        self.set_key(l_sc, 'rotateZ', start, sd); self.set_key(l_sc, 'rotateZ', end, sd)

        x_vals = [-self.arm_params['shoulder_x'], self.arm_params['shoulder_x'], -self.arm_params['shoulder_x']]
        self.apply_keyframe_pattern((l_sh, 'rotateX'), x_vals)

        for key, ctrl in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                             ['scapula', 'shoulder', 'elbow', 'wrist']):
            val = self.arm_params[key]
            l_ctrl = self.arm_ctrls[ctrl].replace('_R', '_L')
            values = [val, 0, val] if key == 'elbow_z' else [-val, val, -val]
            self.apply_keyframe_pattern((l_ctrl, 'rotateY'), values)

    # ---------- generate ----------
    def create_walk_cycle(self, *args):
        self._read_ui()
        original_time = cmds.currentTime(query=True)
        self.clear_keys(); self.compute_frame_data()
        self.set_leg_stretch_keys(); self.set_feet_keys()
        self.set_foot_raise_keys(); self.set_hip_swinger_keys()
        self.set_spine_keys(); self.set_root_keys()
        self.set_right_arm_keys(); self.set_left_arm_keys()
        cmds.currentTime(original_time, edit=True)

    def _read_ui(self):
        self.stride = cmds.floatField(self.stride_field, q=True, v=True)
        self.stride_width = cmds.floatField(self.stride_width_field, q=True, v=True)
        self.stride_height = cmds.floatField(self.stride_height_field, q=True, v=True)
        self.swing_extend = cmds.floatField(self.swing_field, q=True, v=True)
        self.hip_sway_lr = cmds.floatField(self.hip_sway_field, q=True, v=True)
        self.root_bounce = cmds.floatField(self.root_bounce_field, q=True, v=True)
        self.root_sway = cmds.floatField(self.root_sway_field, q=True, v=True)
        self.root_rock = cmds.floatField(self.root_rock_field, q=True, v=True)
        self.root_rock_offset = cmds.floatField(self.root_rock_offset_field, q=True, v=True)
        self.foot_raise = cmds.floatField(self.foot_raise_field, q=True, v=True)
        self.root_bounce_offset = cmds.floatField(self.root_bounce_offset_field, q=True, v=True)
        self.root_twist = cmds.floatField(self.root_twist_field, q=True, v=True)
        self.root_backforth = cmds.floatField(self.root_backforth_field, q=True, v=True)
        self.root_leftright = cmds.floatField(self.root_leftright_field, q=True, v=True)
        self.leg_stretch_L = cmds.floatSliderGrp(self.leg_stretch_L_slider, q=True, v=True)
        self.leg_stretch_R = cmds.floatSliderGrp(self.leg_stretch_R_slider, q=True, v=True)
        for key in self.upper_body_params:
            for a in ('rx', 'ry', 'rz', 'rz_offset'):
                self.upper_body_params[key][a] = cmds.floatField(self.upper_body_params[key][a + '_field'], q=True, v=True)
        for k in ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']:
            self.arm_params[k] = cmds.floatField(self.arm_params[k + '_field'], q=True, v=True)

    # ---------- settings ----------
    def print_settings(self, *args):
        settings = {
            'stride': self.stride, 'stride_width': self.stride_width,
            'stride_height': self.stride_height, 'swing_extend': self.swing_extend,
            'hip_sway_lr': self.hip_sway_lr, 'root_bounce': self.root_bounce,
            'root_sway': self.root_sway, 'root_rock': self.root_rock,
            'foot_raise': self.foot_raise, 'root_bounce_offset': self.root_bounce_offset,
            'root_twist': self.root_twist, 'root_backforth': self.root_backforth,
            'root_leftright': self.root_leftright,
            'leg_stretch_L': self.leg_stretch_L, 'leg_stretch_R': self.leg_stretch_R,
            'upper_body': {k: {a: v[a] for a in ('rx', 'ry', 'rz', 'rz_offset')}
                           for k, v in self.upper_body_params.items()},
            'arms': {k: self.arm_params[k] for k in self.arm_params if not k.endswith('_field')},
        }
        self.print_settings_json("WalkCycleTool", settings)

    def apply_settings(self, settings):
        for k in ('stride', 'stride_width', 'stride_height', 'swing_extend', 'hip_sway_lr',
                   'root_bounce', 'root_sway', 'root_rock', 'root_rock_offset', 'foot_raise',
                   'root_bounce_offset', 'root_twist', 'root_backforth', 'root_leftright',
                   'leg_stretch_L', 'leg_stretch_R'):
            if k in settings:
                setattr(self, k, settings.get(k, 0.0))
        for key, vals in settings.get('upper_body', {}).items():
            if key in self.upper_body_params:
                for a in ('rx', 'ry', 'rz', 'rz_offset'):
                    self.upper_body_params[key][a] = vals.get(a, 0.0)
        arm_defaults = ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']
        for k in arm_defaults:
            if 'arms' in settings:
                self.arm_params[k] = settings['arms'].get(k, 0.0)

    def update_ui_fields_from_settings(self):
        for ff, val in [
            ('stride_field', self.stride), ('stride_width_field', self.stride_width),
            ('stride_height_field', self.stride_height), ('swing_field', self.swing_extend),
            ('hip_sway_field', self.hip_sway_lr), ('root_bounce_field', self.root_bounce),
            ('root_sway_field', self.root_sway), ('root_rock_field', self.root_rock),
            ('root_rock_offset_field', self.root_rock_offset), ('foot_raise_field', self.foot_raise),
            ('root_bounce_offset_field', self.root_bounce_offset), ('root_twist_field', self.root_twist),
            ('root_backforth_field', self.root_backforth), ('root_leftright_field', self.root_leftright),
        ]:
            cmds.floatField(getattr(self, ff), e=True, value=val)
        cmds.floatSliderGrp(self.leg_stretch_L_slider, e=True, value=self.leg_stretch_L)
        cmds.floatSliderGrp(self.leg_stretch_R_slider, e=True, value=self.leg_stretch_R)
        for key in self.upper_body_params:
            for a in ('rx', 'ry', 'rz', 'rz_offset'):
                cmds.floatField(self.upper_body_params[key][a + '_field'], e=True, value=self.upper_body_params[key][a])
        for k in ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']:
            cmds.floatField(self.arm_params[k + '_field'], e=True, value=self.arm_params[k])

    def prompt_and_apply_settings(self, *args):
        self.prompt_and_apply(lambda s: (self.apply_settings(s), self.update_ui_fields_from_settings()))

    # ---------- UI ----------
    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE, widthHeight=self.WINDOW_SIZE)
        cmds.scrollLayout(horizontalScrollBarThickness=0)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        # Global Settings
        cmds.frameLayout(label="Global Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
        cmds.text(label="Stride Length"); self.stride_field = cmds.floatField(value=self.stride, bgc=self.COLOR_Z)
        cmds.text(label="Stride Width (X)"); self.stride_width_field = cmds.floatField(value=self.stride_width, bgc=self.COLOR_X)
        cmds.text(label="Stride Height (Y)"); self.stride_height_field = cmds.floatField(value=self.stride_height, bgc=self.COLOR_Y)
        cmds.text(label="Hip Swing (rotateX)"); self.swing_field = cmds.floatField(value=self.swing_extend, bgc=self.COLOR_X)
        cmds.text(label="Hip Sway (rotateY)"); self.hip_sway_field = cmds.floatField(value=self.hip_sway_lr, bgc=self.COLOR_Y)
        cmds.text(label="Foot Raise (rotateX)"); self.foot_raise_field = cmds.floatField(value=self.foot_raise, bgc=self.COLOR_X)
        cmds.rowLayout(numberOfColumns=2)
        cmds.text(label="Bounce Offset (Y):"); self.root_bounce_offset_field = cmds.floatField(value=self.root_bounce_offset, bgc=self.COLOR_Y)
        cmds.setParent('..')
        cmds.setParent('..'); cmds.setParent('..')

        # Root
        cmds.frameLayout(label="Root Controls (RootX_M)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
        cmds.text(label="Bounce (translateY)"); self.root_bounce_field = cmds.floatField(value=self.root_bounce, bgc=self.COLOR_Y)
        cmds.text(label="Side Sway (rotateY)"); self.root_sway_field = cmds.floatField(value=self.root_sway, bgc=self.COLOR_Y)
        cmds.text(label="Rock (rotateX)"); self.root_rock_field = cmds.floatField(value=self.root_rock, bgc=self.COLOR_X)
        cmds.text(label="Rock Offset (rotateX)"); self.root_rock_offset_field = cmds.floatField(value=self.root_rock_offset, bgc=self.COLOR_X)
        cmds.text(label="Twist (rotateZ)"); self.root_twist_field = cmds.floatField(value=self.root_twist, bgc=self.COLOR_Z)
        cmds.text(label="LeftRight (translateX)"); self.root_leftright_field = cmds.floatField(value=self.root_leftright, bgc=self.COLOR_X)
        cmds.text(label="BackForth (translateZ)"); self.root_backforth_field = cmds.floatField(value=self.root_backforth, bgc=self.COLOR_Z)
        cmds.setParent('..'); cmds.setParent('..')

        # Leg Stretch
        cmds.frameLayout(label="Leg Stretch (IKLeg_*.Stretchy)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 220), (2, 400)])
        cmds.text(label="IKLeg_L.Stretchy (0-10)")
        self.leg_stretch_L_slider = cmds.floatSliderGrp(label="", field=True, min=0.0, max=10.0, value=self.leg_stretch_L)
        cmds.text(label="IKLeg_R.Stretchy (0-10)")
        self.leg_stretch_R_slider = cmds.floatSliderGrp(label="", field=True, min=0.0, max=10.0, value=self.leg_stretch_R)
        cmds.setParent('..'); cmds.setParent('..')

        # Spine / Neck / Head
        cmds.frameLayout(label="Spine / Neck / Head", collapsable=True, marginWidth=10, marginHeight=5)
        for key in self.upper_body_params:
            cmds.text(label=key.capitalize(), align='left')
            cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 60), (2, 90), (3, 60), (4, 90), (5, 60), (6, 90)])
            cmds.text(label="Rotate Z:")
            self.upper_body_params[key]['rx_field'] = cmds.floatField(value=self.upper_body_params[key]['rx'], bgc=self.COLOR_Z)
            cmds.text(label="Rotate X:")
            self.upper_body_params[key]['ry_field'] = cmds.floatField(value=self.upper_body_params[key]['ry'], bgc=self.COLOR_X)
            cmds.text(label="Rotate Y:")
            self.upper_body_params[key]['rz_field'] = cmds.floatField(value=self.upper_body_params[key]['rz'], bgc=self.COLOR_Y)
            cmds.text(label="Offset Y:")
            self.upper_body_params[key]['rz_offset_field'] = cmds.floatField(value=self.upper_body_params[key]['rz_offset'], bgc=self.COLOR_Y)
            cmds.setParent('..')
        cmds.setParent('..')

        # Right Arm Swing
        cmds.frameLayout(label="Right Arm Swing", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
        cmds.text(label="Shoulder Down (rotateZ):")
        self.arm_params['shoulder_down_y_field'] = cmds.floatField(value=self.arm_params['shoulder_down_y'], bgc=self.COLOR_Z)
        cmds.text(label="Scapula Down (rotateZ):")
        self.arm_params['scapula_down_field'] = cmds.floatField(value=self.arm_params['scapula_down'], bgc=self.COLOR_Z)
        cmds.text(label="Shoulder X (rotateX):")
        self.arm_params['shoulder_x_field'] = cmds.floatField(value=self.arm_params['shoulder_x'], bgc=self.COLOR_X)
        for label, key in [('Scapula Y', 'scapula_z'), ('Shoulder Y', 'shoulder_z'),
                           ('Elbow Y', 'elbow_z'), ('Wrist Y', 'wrist_z')]:
            cmds.text(label=label)
            self.arm_params[key + '_field'] = cmds.floatField(value=self.arm_params[key], bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        # Action Buttons
        cmds.separator(height=10, style='in')
        cmds.button(label="Create Walk Cycle", height=40, command=self.create_walk_cycle)
        cmds.separator(height=10, style='in')

        cmds.frameLayout(label="Presets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(300, 300))
        cmds.button(label="Print Current Settings to Console", command=self.print_settings)
        cmds.button(label="Apply Settings From String", command=self.prompt_and_apply_settings)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.showWindow(self.window)
