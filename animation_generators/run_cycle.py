import re
import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class RunCycleGenerator(AnimGeneratorBase):
    WINDOW_NAME = "RunCycleGeneratorWindow"
    WINDOW_TITLE = "Run Cycle Generator"
    WINDOW_SIZE = (600, 600)

    def __init__(self):
        super().__init__()
        self.root_ctrl = "RootX_M"
        self.leg_r = "IKLeg_R"; self.leg_l = "IKLeg_L"
        self.chest_ctrl = "FKChest_M"; self.hip_ctrl = "HipSwinger_M"
        self.head_ctrl = "FKHead_M"; self.neck_ctrl = "FKNeck_M"
        self.spine_ctrl = "FKSpine_M"
        self.foot_raise = 10.0

        self.arm_ctrls = {
            'scapula_l': "FKScapula1_L", 'shoulder_l': "FKShoulder_L", 'elbow_l': "FKElbow_L",
            'scapula_r': "FKScapula1_R", 'shoulder_r': "FKShoulder_R", 'elbow_r': "FKElbow_R",
        }
        self.head_bounce = 1.5; self.head_rock = 2.0; self.head_lean = -10.0
        self.head_sway = 1.0; self.head_swing = 2.0
        self.neck_bounce = 1.5; self.neck_rock = 2.0; self.neck_lean = -10.0
        self.neck_sway = 1.0; self.neck_swing = 2.0
        self.spine_bounce = 0.0; self.spine_swing = 0.0; self.spine_tilt = 0.0
        self.chest_z_offset = 0.0; self.spine_z_offset = 0.0
        self.neck_z_offset = 0.0; self.head_z_offset = 0.0
        self.root_bounce_up = 3.0; self.root_bounce_down = -3.0
        self.root_lean = -20.0; self.root_sway = 5.0; self.root_swing = 4.0
        self.corkscrew = False; self.root_back_forth = 0.0
        self.stride_length = 10.0; self.stride_width = 2.0; self.stride_height = 5.0
        self.chest_bounce = 2.0; self.chest_swing = 5.0; self.chest_tilt = 3.0
        self.hip_swing = 6.0; self.hip_side = 4.0
        self.shoulder_down_y = -30.0; self.scapula_down_y = -12.0
        self.scapula_z = 10.0; self.elbow_z = 15.0
        self.shoulder_rotate_x = 0.0; self.shoulder_swing_z = 0.0; self.shoulder_sway_out_y = 0.0
        self.frames_stride_halved = []
        self.quarter = 0; self.three_quarter = 0

        self.alias_map = {
            'fkchest_m': 'FKChest1_M', 'fkhead_m': 'FKHead1_M',
            'fkspine_m': 'FKSpine1_M', 'rootswinger_m': 'RootX_M',
            'hipswinger_m': 'HipSwinger1_M',
            'ikleg_r': 'IKLeg_R', 'ikleg_l': 'IKLeg_L',
        }

    # ---------- resolver ----------
    def resolve(self, name):
        all_nodes = cmds.ls(type='transform')
        name_lower = name.lower()
        for node in all_nodes:
            if node.lower() == name_lower:
                return node
        alias = self.alias_map.get(name_lower)
        if alias and cmds.objExists(alias):
            return alias
        m = re.match(r"^(.+?)(?:1)?(_[A-Za-z0-9]+)$", name)
        if m:
            base, suffix = m.group(1), m.group(2)
            for variant in (base + suffix, base + "1" + suffix):
                if cmds.objExists(variant):
                    return variant
        stripped = name.replace("1_", "_")
        if cmds.objExists(stripped):
            return stripped
        raise RuntimeError(f"Node not found: {name}")

    # ---------- frames ----------
    def compute_frames(self):
        start, end = self.timeline_range()
        mid = (start + end) / 2.0
        self.quarter = (start + mid) / 2.0
        self.three_quarter = (mid + end) / 2.0
        self.frames_stride_halved = [start, self.quarter, mid, self.three_quarter, end]

    # ---------- clear ----------
    def clear_keys(self):
        attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        start, end = self.timeline_range()
        all_ctrls = [self.root_ctrl, self.leg_r, self.leg_l, self.chest_ctrl,
                     self.hip_ctrl, self.neck_ctrl, self.spine_ctrl,
                     getattr(self, 'head_ctrl', 'FKHead_M')]
        all_ctrls += list(self.arm_ctrls.values())
        for ctrl in all_ctrls:
            if not cmds.objExists(ctrl):
                continue
            for attr in attrs:
                full = f"{ctrl}.{attr}"
                if not cmds.attributeQuery(attr, node=ctrl, exists=True):
                    continue
                cmds.cutKey(ctrl, at=attr, time=(start, end))
                if not cmds.getAttr(full, lock=True) and not cmds.connectionInfo(full, isDestination=True):
                    cmds.setAttr(full, 0)

    # ---------- keying ----------
    def set_root_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        self.set_key(self.root_ctrl, 'rotateZ', start, self.root_lean)
        self.set_key(self.root_ctrl, 'rotateZ', end, self.root_lean)
        for t, v in zip([start, quarter, mid, three_quarter, end],
                        [self.root_bounce_up, self.root_bounce_down,
                         self.root_bounce_up, self.root_bounce_down, self.root_bounce_up]):
            self.set_key(self.root_ctrl, 'translateX', t, v)

        span = end - start
        f1 = start + span * 0.2; f4 = start + span * 0.8
        for t in (start, mid, end):
            self.set_key(self.root_ctrl, 'translateY', t, 0)
        self.set_key(self.root_ctrl, 'translateY', f1, self.root_back_forth)
        self.set_key(self.root_ctrl, 'translateY', f4, self.root_back_forth)

        if self.corkscrew:
            self.set_key(self.root_ctrl, 'rotateY', start, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', quarter, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', three_quarter, -self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', end, self.root_sway)
        else:
            self.set_key(self.root_ctrl, 'rotateY', start, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', mid, -self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', end, self.root_sway)

        self.set_key(self.root_ctrl, 'rotateX', start, self.root_swing)
        self.set_key(self.root_ctrl, 'rotateX', mid, -self.root_swing)
        self.set_key(self.root_ctrl, 'rotateX', end, self.root_swing)

    def set_leg_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        span = end - start; f1 = start + span * 0.2; f4 = start + span * 0.8
        for t in (start, mid, end):
            self.set_key(self.leg_l, 'rotateX', t, 0)
            self.set_key(self.leg_r, 'rotateX', t, 0)
        self.set_key(self.leg_l, 'rotateX', f1, self.foot_raise)
        self.set_key(self.leg_r, 'rotateX', f4, self.foot_raise)

        half_stride = self.stride_length / 2.0
        for leg, x in [(self.leg_r, self.stride_width), (self.leg_l, -self.stride_width)]:
            z_vals = [half_stride, -half_stride, half_stride] if leg == self.leg_r else [-half_stride, half_stride, -half_stride]
            for i, t in enumerate([start, mid, end]):
                self.set_key(leg, 'translateZ', t, z_vals[i])
                self.set_key(leg, 'translateX', t, x)
        self.set_key(self.leg_r, 'translateY', three_quarter, self.stride_height)
        self.set_key(self.leg_l, 'translateY', quarter, self.stride_height)
        for t in [start, mid, end]:
            self.set_key(self.leg_r, 'translateY', t, 0)
            self.set_key(self.leg_l, 'translateY', t, 0)

    def set_chest_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        for t, v in zip([start, quarter, mid, three_quarter, end],
                        [1, -1, 1, -1, 1]):
            self.set_key(self.chest_ctrl, 'rotateY', t, v * self.chest_bounce + self.chest_z_offset)
        for attr, val in [('rotateZ', self.chest_swing), ('rotateX', self.chest_tilt)]:
            self.set_key(self.chest_ctrl, attr, start, val)
            self.set_key(self.chest_ctrl, attr, mid, -val)
            self.set_key(self.chest_ctrl, attr, end, val)

    def set_spine_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        for t, v in zip([start, quarter, mid, three_quarter, end],
                        [1, -1, 1, -1, 1]):
            self.set_key(self.spine_ctrl, 'rotateY', t, v * self.spine_bounce + self.spine_z_offset)
        for attr, base in [('rotateZ', self.spine_swing), ('rotateX', self.spine_tilt)]:
            self.set_key(self.spine_ctrl, attr, start, base)
            self.set_key(self.spine_ctrl, attr, mid, -base)
            self.set_key(self.spine_ctrl, attr, end, base)

    def set_hip_keys(self):
        start, mid, end = self.frames_stride_halved[0], self.frames_stride_halved[2], self.frames_stride_halved[4]
        for attr, val in [('rotateZ', self.hip_swing), ('rotateY', self.hip_side)]:
            self.set_key(self.hip_ctrl, attr, start, val)
            self.set_key(self.hip_ctrl, attr, mid, -val)
            self.set_key(self.hip_ctrl, attr, end, val)

    def _key_head_neck(self, ctrl, bounce, rock, lean, sway, swing, z_offset):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        for t, v in zip([start, quarter, mid, three_quarter, end],
                        [bounce, -bounce, bounce, -bounce, bounce]):
            self.set_key(ctrl, 'translateX', t, v)
        self.set_key(ctrl, 'rotateZ', start, -rock)
        self.set_key(ctrl, 'rotateZ', mid, rock)
        self.set_key(ctrl, 'rotateZ', end, -rock)
        self.set_key(ctrl, 'rotateY', start, lean + z_offset)
        self.set_key(ctrl, 'rotateY', end, lean + z_offset)
        self.set_key(ctrl, 'rotateX', start, swing)
        self.set_key(ctrl, 'rotateX', quarter, 0)
        self.set_key(ctrl, 'rotateX', mid, -swing)
        self.set_key(ctrl, 'rotateX', three_quarter, 0)
        self.set_key(ctrl, 'rotateX', end, swing)

    def set_head_keys(self):
        self._key_head_neck(self.head_ctrl, self.head_bounce, self.head_rock,
                            self.head_lean, self.head_sway, self.head_swing, self.head_z_offset)

    def set_neck_keys(self):
        self._key_head_neck(self.neck_ctrl, self.neck_bounce, self.neck_rock,
                            self.neck_lean, self.neck_sway, self.neck_swing, self.neck_z_offset)

    def set_arm_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        for side in ['l', 'r']:
            scapula = self.arm_ctrls[f'scapula_{side}']
            shoulder = self.arm_ctrls[f'shoulder_{side}']
            elbow = self.arm_ctrls[f'elbow_{side}']
            cmds.setAttr(f"{scapula}.rotateY", self.scapula_down_y)
            self.set_key(scapula, 'rotateY', start, self.scapula_down_y)
            self.set_key(scapula, 'rotateY', end, self.scapula_down_y)
            cmds.setAttr(f"{shoulder}.rotateY", self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', start, self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', end, self.shoulder_down_y)

            sign = 1 if side == 'l' else -1
            rotX = [sign * self.shoulder_rotate_x, -sign * self.shoulder_rotate_x, sign * self.shoulder_rotate_x]
            swingY = [sign * self.shoulder_swing_z, -sign * self.shoulder_swing_z, sign * self.shoulder_swing_z]
            for t, vx, vy in zip([start, mid, end], rotX, swingY):
                self.set_key(shoulder, 'rotateX', t, vx)
                self.set_key(shoulder, 'rotateZ', t, vy)

            for t in (start, mid, end):
                self.set_key(shoulder, 'rotateY', t, self.shoulder_down_y)
            val_q = self.shoulder_down_y + (sign * self.shoulder_sway_out_y)
            val_3q = self.shoulder_down_y - (sign * self.shoulder_sway_out_y)
            self.set_key(shoulder, 'rotateZ', quarter, val_q)
            self.set_key(shoulder, 'rotateZ', three_quarter, val_3q)

            scap_vals = [sign * self.scapula_z, -sign * self.scapula_z, sign * self.scapula_z]
            for t, val in zip([start, mid, end], scap_vals):
                self.set_key(scapula, 'rotateZ', t, val)

            if side == 'l':
                elbow_vals = [self.elbow_z, 0, self.elbow_z]
            else:
                elbow_vals = [0, self.elbow_z, 0]
            for t, val in zip([start, mid, end], elbow_vals):
                self.set_key(elbow, 'rotateZ', t, val)

    # ---------- generate ----------
    def generate(self):
        self.clear_keys(); self.compute_frames()
        self.root_ctrl = self.resolve(self.root_ctrl)
        self.leg_r = self.resolve(self.leg_r); self.leg_l = self.resolve(self.leg_l)
        self.chest_ctrl = self.resolve(self.chest_ctrl)
        self.hip_ctrl = self.resolve(self.hip_ctrl)
        self.head_ctrl = self.resolve(self.head_ctrl)
        self.neck_ctrl = self.resolve(self.neck_ctrl)
        self.spine_ctrl = self.resolve(self.spine_ctrl)
        for k in self.arm_ctrls:
            self.arm_ctrls[k] = self.resolve(self.arm_ctrls[k])
        self.set_root_keys(); self.set_leg_keys()
        self.set_chest_keys(); self.set_spine_keys()
        self.set_hip_keys(); self.set_arm_keys()
        self.set_head_keys(); self.set_neck_keys()

    # ---------- settings ----------
    def _sanitize_json(self, text):
        text = re.sub(r'//.*', '', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        for old, new in [('True', 'true'), ('False', 'false'), ('None', 'null')]:
            text = re.sub(rf'\b{old}\b', new, text)
        return text

    def _parse_settings(self, raw):
        try:
            return json.loads(raw)
        except Exception:
            return json.loads(self._sanitize_json(raw))

    def _num(self, v, default):
        try:
            return float(v)
        except Exception:
            return default

    def _bool(self, v, default):
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ('1', 'true', 'yes', 'on'):
            return True
        if s in ('0', 'false', 'no', 'off'):
            return False
        return default

    def _dig(self, d, *ks):
        cur = d
        for k in ks:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        return cur

    def print_settings(self, *args):
        settings = {
            'root_bounce_up': self.root_bounce_up, 'root_bounce_down': self.root_bounce_down,
            'root_lean': self.root_lean, 'root_sway': self.root_sway,
            'root_swing': self.root_swing, 'root_back_forth': self.root_back_forth,
            'corkscrew': self.corkscrew,
            'stride_length': self.stride_length, 'stride_width': self.stride_width,
            'stride_height': self.stride_height, 'foot_raise': self.foot_raise,
            'chest_bounce': self.chest_bounce, 'chest_swing': self.chest_swing,
            'chest_tilt': self.chest_tilt, 'hip_swing': self.hip_swing, 'hip_side': self.hip_side,
            'arm': {
                'shoulder_down_y': self.shoulder_down_y, 'scapula_down_y': self.scapula_down_y,
                'scapula_z': self.scapula_z, 'elbow_z': self.elbow_z,
                'shoulder_rotate_x': self.shoulder_rotate_x,
                'shoulder_swing_z': self.shoulder_swing_z,
                'shoulder_sway_out_y': self.shoulder_sway_out_y,
            },
            'head': {'bounce': self.head_bounce, 'rock': self.head_rock,
                     'lean': self.head_lean, 'sway': self.head_sway, 'swing': self.head_swing},
            'neck': {'bounce': self.neck_bounce, 'rock': self.neck_rock,
                     'lean': self.neck_lean, 'sway': self.neck_sway, 'swing': self.neck_swing},
        }
        self.print_settings_json("RunCycleGenerator", settings)

    def apply_settings(self, settings):
        for k in ('root_bounce_up', 'root_bounce_down', 'root_lean', 'root_sway',
                   'root_swing', 'root_back_forth', 'stride_length', 'stride_width',
                   'stride_height', 'foot_raise', 'chest_bounce', 'chest_swing',
                   'chest_tilt', 'chest_z_offset', 'spine_bounce', 'spine_swing',
                   'spine_tilt', 'spine_z_offset', 'hip_swing', 'hip_side'):
            if k in settings:
                setattr(self, k, self._num(settings[k], getattr(self, k)))
        if 'corkscrew' in settings:
            self.corkscrew = self._bool(settings['corkscrew'], self.corkscrew)

        arm = settings.get('arm', {}) if isinstance(settings.get('arm'), dict) else {}
        for k in ('shoulder_down_y', 'scapula_down_y', 'scapula_z', 'shoulder_rotate_x',
                   'shoulder_swing_z', 'shoulder_sway_out_y'):
            if k in arm:
                setattr(self, k, self._num(arm[k], getattr(self, k)))
        if 'elbow_z' in arm:
            self.elbow_z = abs(self._num(arm['elbow_z'], self.elbow_z))

        for prefix in ('head', 'neck'):
            for attr in ('bounce', 'rock', 'lean', 'sway', 'swing'):
                flat = f'{prefix}_{attr}'
                nested = self._dig(settings, prefix, attr)
                val = settings.get(flat, nested)
                if val is not None:
                    setattr(self, flat, self._num(val, getattr(self, flat)))
            zoff = f'{prefix}_z_offset'
            if zoff in settings:
                setattr(self, zoff, self._num(settings[zoff], getattr(self, zoff)))

    def refresh_ui(self):
        def _set(ff, val):
            if hasattr(self, ff):
                try:
                    cmds.floatField(getattr(self, ff), e=True, value=val)
                except Exception:
                    pass
        _set('root_bounce_up_field', self.root_bounce_up)
        _set('root_bounce_down_field', self.root_bounce_down)
        _set('root_lean_field', self.root_lean)
        _set('root_sway_field', self.root_sway)
        _set('root_swing_field', self.root_swing)
        _set('root_back_forth_field', self.root_back_forth)
        try:
            cmds.checkBox(self.corkscrew_field, e=True, value=self.corkscrew)
        except Exception:
            pass
        _set('stride_length_field', self.stride_length)
        _set('stride_width_field', self.stride_width)
        _set('stride_height_field', self.stride_height)
        _set('foot_raise_field', self.foot_raise)
        _set('chest_bounce_field', self.chest_bounce)
        _set('chest_swing_field', self.chest_swing)
        _set('chest_tilt_field', self.chest_tilt)
        _set('chest_z_offset_field', self.chest_z_offset)
        _set('spine_bounce_field', self.spine_bounce)
        _set('spine_swing_field', self.spine_swing)
        _set('spine_tilt_field', self.spine_tilt)
        _set('spine_z_offset_field', self.spine_z_offset)
        _set('hip_swing_field', self.hip_swing)
        _set('hip_side_field', self.hip_side)
        _set('shoulder_down_y_field', self.shoulder_down_y)
        _set('scapula_down_y_field', self.scapula_down_y)
        _set('scapula_z_field', self.scapula_z)
        _set('elbow_z_field', self.elbow_z)
        _set('shoulder_rotate_x_field', self.shoulder_rotate_x)
        _set('shoulder_swing_z_field', self.shoulder_swing_z)
        _set('shoulder_sway_out_y_field', self.shoulder_sway_out_y)
        for prefix in ('neck', 'head'):
            for attr in ('bounce', 'rock', 'lean', 'sway', 'swing'):
                _set(f'{prefix}_{attr}_field', getattr(self, f'{prefix}_{attr}'))
            _set(f'{prefix}_z_offset_field', getattr(self, f'{prefix}_z_offset'))

    def prompt_and_apply_settings(self, *args):
        result = cmds.promptDialog(title="Apply Settings", message="Paste JSON settings string here:",
                                   button=['Apply', 'Cancel'], defaultButton='Apply',
                                   cancelButton='Cancel', dismissString='Cancel')
        if result != 'Apply':
            return
        try:
            data = self._parse_settings(cmds.promptDialog(query=True, text=True))
            self.apply_settings(data)
            self.refresh_ui()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    # ---------- UI callbacks ----------
    def on_generate(self, *args):
        for attr, fld in [
            ('root_bounce_up', 'root_bounce_up_field'), ('root_bounce_down', 'root_bounce_down_field'),
            ('root_lean', 'root_lean_field'), ('root_sway', 'root_sway_field'),
            ('root_swing', 'root_swing_field'), ('root_back_forth', 'root_back_forth_field'),
            ('stride_length', 'stride_length_field'), ('stride_width', 'stride_width_field'),
            ('stride_height', 'stride_height_field'), ('foot_raise', 'foot_raise_field'),
            ('chest_bounce', 'chest_bounce_field'), ('chest_swing', 'chest_swing_field'),
            ('chest_tilt', 'chest_tilt_field'), ('chest_z_offset', 'chest_z_offset_field'),
            ('spine_bounce', 'spine_bounce_field'), ('spine_swing', 'spine_swing_field'),
            ('spine_tilt', 'spine_tilt_field'), ('spine_z_offset', 'spine_z_offset_field'),
            ('neck_z_offset', 'neck_z_offset_field'), ('head_z_offset', 'head_z_offset_field'),
            ('head_bounce', 'head_bounce_field'), ('head_rock', 'head_rock_field'),
            ('head_lean', 'head_lean_field'), ('head_sway', 'head_sway_field'),
            ('head_swing', 'head_swing_field'),
            ('neck_bounce', 'neck_bounce_field'), ('neck_rock', 'neck_rock_field'),
            ('neck_lean', 'neck_lean_field'), ('neck_sway', 'neck_sway_field'),
            ('neck_swing', 'neck_swing_field'),
            ('hip_swing', 'hip_swing_field'), ('hip_side', 'hip_side_field'),
            ('shoulder_down_y', 'shoulder_down_y_field'), ('scapula_down_y', 'scapula_down_y_field'),
            ('shoulder_rotate_x', 'shoulder_rotate_x_field'),
            ('shoulder_swing_z', 'shoulder_swing_z_field'),
            ('shoulder_sway_out_y', 'shoulder_sway_out_y_field'),
            ('scapula_z', 'scapula_z_field'),
        ]:
            setattr(self, attr, cmds.floatField(getattr(self, fld), q=True, v=True))
        self.elbow_z = abs(cmds.floatField(self.elbow_z_field, q=True, v=True))
        self.corkscrew = cmds.checkBox(self.corkscrew_field, q=True, v=True)
        self.generate()

    # ---------- UI ----------
    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE, widthHeight=self.WINDOW_SIZE)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        # Root
        cmds.frameLayout(label="Root (RootX_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Bounce Up (Y):", lambda: setattr(self, 'root_bounce_up_field', cmds.floatField(value=self.root_bounce_up, bgc=self.COLOR_Y)),
            "Bounce Down (Y):", lambda: setattr(self, 'root_bounce_down_field', cmds.floatField(value=self.root_bounce_down, bgc=self.COLOR_Y)))
        self.two_col_row(
            "Lean (X):", lambda: setattr(self, 'root_lean_field', cmds.floatField(value=self.root_lean, bgc=self.COLOR_X)),
            "Swing (Z):", lambda: setattr(self, 'root_swing_field', cmds.floatField(value=self.root_swing, bgc=self.COLOR_Z)))
        self.two_col_row(
            "Sway (Y):", lambda: setattr(self, 'root_sway_field', cmds.floatField(value=self.root_sway, bgc=self.COLOR_Y)),
            "Back/Forth (Z):", lambda: setattr(self, 'root_back_forth_field', cmds.floatField(value=self.root_back_forth, bgc=self.COLOR_Z)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 200))
        cmds.text(label="Corkscrew Twist:"); self.corkscrew_field = cmds.checkBox(value=self.corkscrew)
        cmds.setParent('..'); cmds.setParent('..')

        # Legs
        cmds.frameLayout(label="Legs", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Stride Length (Z):", lambda: setattr(self, 'stride_length_field', cmds.floatField(value=self.stride_length, bgc=self.COLOR_Z)),
            "Stride Width (X):", lambda: setattr(self, 'stride_width_field', cmds.floatField(value=self.stride_width, bgc=self.COLOR_X)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Stride Height (Y):"); self.stride_height_field = cmds.floatField(value=self.stride_height, bgc=self.COLOR_Y)
        cmds.setParent('..')
        self.two_col_row(
            "Foot Raise (rotateX):", lambda: setattr(self, 'foot_raise_field', cmds.floatField(value=self.foot_raise, bgc=self.COLOR_X)),
            "", lambda: None)
        cmds.setParent('..')

        # Chest
        cmds.frameLayout(label="Chest (FKChest_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Chest Bounce (Y):", lambda: setattr(self, 'chest_bounce_field', cmds.floatField(value=self.chest_bounce, bgc=self.COLOR_Y)),
            "Chest Swing (Z):", lambda: setattr(self, 'chest_swing_field', cmds.floatField(value=self.chest_swing, bgc=self.COLOR_Z)))
        self.two_col_row(
            "Rotate Y Offset:", lambda: setattr(self, 'chest_z_offset_field', cmds.floatField(value=self.chest_z_offset, bgc=self.COLOR_Y)),
            "", lambda: None)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Chest Tilt (X):"); self.chest_tilt_field = cmds.floatField(value=self.chest_tilt, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # Spine
        cmds.frameLayout(label="Spine (FKSpine_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Spine Bounce (Y):", lambda: setattr(self, 'spine_bounce_field', cmds.floatField(value=self.spine_bounce, bgc=self.COLOR_Y)),
            "Spine Swing (Z):", lambda: setattr(self, 'spine_swing_field', cmds.floatField(value=self.spine_swing, bgc=self.COLOR_Z)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Spine Tilt (X):"); self.spine_tilt_field = cmds.floatField(value=self.spine_tilt, bgc=self.COLOR_X)
        cmds.setParent('..')
        self.two_col_row(
            "Rotate Y Offset:", lambda: setattr(self, 'spine_z_offset_field', cmds.floatField(value=self.spine_z_offset, bgc=self.COLOR_Y)),
            "", lambda: None)
        cmds.setParent('..')

        # Hips
        cmds.frameLayout(label="HipSwinger (HipSwinger_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Hip Swing (X):", lambda: setattr(self, 'hip_swing_field', cmds.floatField(value=self.hip_swing, bgc=self.COLOR_X)),
            "Hip Side (Y):", lambda: setattr(self, 'hip_side_field', cmds.floatField(value=self.hip_side, bgc=self.COLOR_Y)))
        cmds.setParent('..')

        # Arms
        cmds.frameLayout(label="Arms (Left / Right)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Shoulder Down (Z):", lambda: setattr(self, 'shoulder_down_y_field', cmds.floatField(value=self.shoulder_down_y, bgc=self.COLOR_Z)),
            "Scapula Down (Z):", lambda: setattr(self, 'scapula_down_y_field', cmds.floatField(value=self.scapula_down_y, bgc=self.COLOR_Z)))
        self.two_col_row(
            "Scapula Swing (Y):", lambda: setattr(self, 'scapula_z_field', cmds.floatField(value=self.scapula_z, bgc=self.COLOR_Y)),
            "Shoulder Rotate (X):", lambda: setattr(self, 'shoulder_rotate_x_field', cmds.floatField(value=self.shoulder_rotate_x, bgc=self.COLOR_X)))
        self.two_col_row(
            "Shoulder Swing (Y):", lambda: setattr(self, 'shoulder_swing_z_field', cmds.floatField(value=self.shoulder_swing_z, bgc=self.COLOR_Y)),
            "Shoulder SwayOut (Z):", lambda: setattr(self, 'shoulder_sway_out_y_field', cmds.floatField(value=self.shoulder_sway_out_y, bgc=self.COLOR_Z)))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(160, 80))
        cmds.text(label="Elbow Swing (Y, fwd only):"); self.elbow_z_field = cmds.floatField(value=self.elbow_z, bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        # Neck
        cmds.frameLayout(label="Neck (FKNeck_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Bounce (translateY):", lambda: setattr(self, 'neck_bounce_field', cmds.floatField(value=self.neck_bounce, bgc=self.COLOR_Y)),
            "Rock (rotateZ):", lambda: setattr(self, 'neck_rock_field', cmds.floatField(value=self.neck_rock, bgc=self.COLOR_Z)))
        self.two_col_row(
            "Lean (rotateY):", lambda: setattr(self, 'neck_lean_field', cmds.floatField(value=self.neck_lean, bgc=self.COLOR_Y)),
            "Swing (rotateX, 4ths):", lambda: setattr(self, 'neck_swing_field', cmds.floatField(value=self.neck_swing, bgc=self.COLOR_X)))
        self.two_col_row(
            "Rotate Y Offset:", lambda: setattr(self, 'neck_z_offset_field', cmds.floatField(value=self.neck_z_offset, bgc=self.COLOR_Y)),
            "", lambda: None)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Sway (rotateX):"); self.neck_sway_field = cmds.floatField(value=self.neck_sway, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # Head
        cmds.frameLayout(label="Head (FKHead_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Bounce (translateY):", lambda: setattr(self, 'head_bounce_field', cmds.floatField(value=self.head_bounce, bgc=self.COLOR_Y)),
            "Rock (rotateZ):", lambda: setattr(self, 'head_rock_field', cmds.floatField(value=self.head_rock, bgc=self.COLOR_Z)))
        self.two_col_row(
            "Lean (rotateY):", lambda: setattr(self, 'head_lean_field', cmds.floatField(value=self.head_lean, bgc=self.COLOR_Y)),
            "Swing (rotateX, 4ths):", lambda: setattr(self, 'head_swing_field', cmds.floatField(value=self.head_swing, bgc=self.COLOR_X)))
        self.two_col_row(
            "Rotate Y Offset:", lambda: setattr(self, 'head_z_offset_field', cmds.floatField(value=self.head_z_offset, bgc=self.COLOR_Y)),
            "", lambda: None)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Sway (rotateX):"); self.head_sway_field = cmds.floatField(value=self.head_sway, bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(150, 150, 150, 150), adjustableColumn=4)
        cmds.button(label="Generate Run Cycle", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.button(label="Reload UI", command=lambda *_: self.show())
        cmds.setParent('..')

        cmds.setParent('..')
        cmds.showWindow(self.window)
