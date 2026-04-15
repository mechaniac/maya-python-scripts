import math
import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class HandWalkCycleTool(AnimGeneratorBase):
    WINDOW_NAME = "HandWalkCycleWindow"
    WINDOW_TITLE = "Hand Walk Cycle Tool"
    WINDOW_SIZE = (1000, 650)

    def __init__(self):
        super().__init__()
        self.stride = 8.0; self.stride_width = 2.0; self.stride_height = 3.0
        self.hand_offsets = {'offset_x': 2.0, 'offset_y': -5.0, 'offset_z': 0.0, 'rotation_y': 0.0}
        self.elbow_ctrls = {'right': 'PoleArm_R', 'left': 'PoleArm_L'}
        self.elbow_params = {
            'out': 0.0, 'up': 0.0, 'forward': 0.0,
            'offset': {'x': 0.0, 'y': 0.0, 'z': 0.0},
        }
        self.groundHeight = -57.04; self.clamp_hands_to_ground = True
        self.stretch_arms = 0.0
        self.stride_limbs = {'right': "IKArm_R", 'left': "IKArm_L"}
        self.root_ctrl = "RootX_M"; self.hip_ctrl = "HipSwinger_M"
        self.root_params = {
            'offset_y': 0.0, 'offset_z': 0.0, 'offset_rx': 0.0,
            'bounce': 1.5, 'sway': 2.0, 'rock': 1.0,
            'shift_x': 0.0, 'swing_z': 0.0, 'bounce_z': 0.0,
        }
        self.hip_params = {'swing': 10.0, 'sway': 5.0}
        self.feet = {'right': "IKLeg_R", 'left': "IKLeg_L"}
        self.feet_follow = {
            'moveFeetWithRoot': 1.0, 'offset_x': 3.0, 'offset_y': 5.0, 'offset_z': 0.0,
            'rotate_x': 20.0, 'bounce_y': 0.0, 'swing_x': 0.0, 'back_forth_z': 0.0,
        }
        self.scapula_ctrls = {'left': "FKScapula_L", 'right': "FKScapula_R"}
        self.scapula_params = {
            'rotateY': 5.0, 'rotateX': -10.0, 'rotateZ': 0.0,
            'offsetY': 0.0, 'offsetX': 0.0, 'offsetZ': 0.0,
        }
        self.head_ctrls = {'neck': "FKNeck_M", 'head': "FKHead_M"}
        self.neck_params = {
            'counter_rotateZ': -3.0, 'counter_rotateX': -3.0, 'counter_rotateY': 2.0,
            'bounce_tx': 0.0, 'bob_ty': 0.5, 'sway_tz': 0.5, 'offsetY': 0.0,
        }
        self.head_params = {
            'counter_rotateZ': -5.0, 'counter_rotateX': -5.0, 'counter_rotateY': 3.0,
            'bounce_tx': 0.0, 'bob_ty': 0.8, 'sway_tz': 0.8, 'offsetY': 0.0,
        }
        self.spine_ctrl_candidates = ["FKSpine_M", "FKSpine1_M"]
        self.chest_ctrl = "FKChest_M"
        self.spine_params = {'swing_rz': 5.0, 'rock_ry': 3.0, 'sway_rx': 3.0, 'offsetY': 0.0}
        self.chest_params = {'swing_rz': 6.0, 'rock_ry': 4.0, 'sway_rx': 4.0, 'offsetY': 0.0}
        self.legs_fk_params = {'fkik_blend': 0.0, 'hip_ry': 0.0, 'knee_ry': 0.0, 'foot_ry': 0.0, 'toe_ry': 0.0}
        self.fkik_nodes = {'right': 'FKIKLeg_R', 'left': 'FKIKLeg_L'}
        self.frames_stride_halved = []
        self.quarter = 0; self.three_quarter = 0

    # ---------- helpers ----------
    @staticmethod
    def resolve_first_existing(names):
        for n in names:
            if n and cmds.objExists(n):
                return n
        return None

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
        trs_attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ', 'stretchy']
        controls = []
        controls += [n for n in self.stride_limbs.values() if cmds.objExists(n)]
        controls += [n for n in self.feet.values() if cmds.objExists(n)]
        controls += [n for n in [self.root_ctrl, self.hip_ctrl] if cmds.objExists(n)]
        controls += [n for n in self.scapula_ctrls.values() if cmds.objExists(n)]
        controls += [n for n in self.head_ctrls.values() if cmds.objExists(n)]
        controls += [n for n in self.elbow_ctrls.values() if cmds.objExists(n)]
        spine = self.resolve_first_existing(self.spine_ctrl_candidates)
        if spine:
            controls.append(spine)
        if cmds.objExists(self.chest_ctrl):
            controls.append(self.chest_ctrl)
        fk_leg_nodes = ['FKHip_R', 'FKHip_L', 'FKKnee_R', 'FKKnee_L',
                        'FKFoot_R', 'FKFoot_L', 'FKToe_R', 'FKToe_L']
        controls += [n for n in fk_leg_nodes if cmds.objExists(n)]
        for ctrl in controls:
            for attr in trs_attrs:
                if cmds.attributeQuery(attr, node=ctrl, exists=True):
                    try:
                        if not cmds.getAttr(f"{ctrl}.{attr}", lock=True):
                            cmds.setAttr(f"{ctrl}.{attr}", 0)
                        cmds.cutKey(ctrl, at=attr, time=(start, end))
                    except Exception:
                        pass
        for node in self.fkik_nodes.values():
            if node and cmds.objExists(node) and cmds.attributeQuery('FKIKBlend', node=node, exists=True):
                try:
                    cmds.cutKey(node, at='FKIKBlend', time=(start, end))
                except Exception:
                    pass

    # ---------- keying ----------
    def set_stride_keys(self):
        r = self.stride_limbs['right']; l = self.stride_limbs['left']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter
        rz = [f[1] for f in self.frames_stride_halved]
        lz = [f[2] for f in self.frames_stride_halved]
        for (t, vr, vl) in zip([start, mid, end], rz, lz):
            self.set_key(r, 'translateZ', t, vr + self.hand_offsets['offset_z'])
            self.set_key(l, 'translateZ', t, vl + self.hand_offsets['offset_z'])
        base = float(self.stride_width); ox = float(self.hand_offsets['offset_x'])
        self.set_key(r, 'translateX', start, base); self.set_key(r, 'translateX', q, base + ox)
        self.set_key(r, 'translateX', mid, base); self.set_key(r, 'translateX', end, base)
        self.set_key(l, 'translateX', start, -base); self.set_key(l, 'translateX', mid, -base)
        self.set_key(l, 'translateX', tq, -base - ox); self.set_key(l, 'translateX', end, -base)
        gh = float(self.groundHeight); oy = float(self.hand_offsets['offset_y'])
        self.set_key(r, 'translateY', start, gh); self.set_key(r, 'translateY', q, oy)
        self.set_key(r, 'translateY', mid, gh); self.set_key(r, 'translateY', tq, gh)
        self.set_key(r, 'translateY', end, gh)
        self.set_key(l, 'translateY', start, gh); self.set_key(l, 'translateY', q, gh)
        self.set_key(l, 'translateY', mid, gh); self.set_key(l, 'translateY', tq, oy)
        self.set_key(l, 'translateY', end, gh)
        for t in [start, mid, end]:
            self.set_key(r, 'rotateY', t, self.hand_offsets['rotation_y'])
            self.set_key(l, 'rotateY', t, -self.hand_offsets['rotation_y'])

    def set_arm_stretch_keys(self):
        start, end = self.timeline_range()
        val = float(self.stretch_arms)
        for node in self.stride_limbs.values():
            if node and cmds.objExists(node) and cmds.attributeQuery('stretchy', node=node, exists=True):
                self.set_key(node, 'stretchy', start, val)
                self.set_key(node, 'stretchy', end, val)

    def set_root_keys(self):
        root = self.root_ctrl
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter
        p = self.root_params
        for attr, amp, off in [('translateX', p['bounce'], p['offset_y']),
                               ('rotateZ', p['rock'], p['offset_rx'])]:
            for t, sign in zip([start, q, mid, tq, end], [1, -1, 1, -1, 1]):
                self.set_key(root, attr, t, sign * amp + off)
        self.set_key(root, 'rotateY', start, p['sway'])
        self.set_key(root, 'rotateY', mid, -p['sway'])
        self.set_key(root, 'rotateY', end, p['sway'])
        for attr, amp in [('translateZ', p['shift_x']), ('rotateX', p['swing_z'])]:
            self.set_key(root, attr, start, amp)
            self.set_key(root, attr, mid, -amp)
            self.set_key(root, attr, end, amp)
        bz = p.get('bounce_z', 0.0); oz = p['offset_z']
        self.set_key(root, 'translateY', start, oz)
        self.set_key(root, 'translateY', q, oz + bz)
        self.set_key(root, 'translateY', mid, oz)
        self.set_key(root, 'translateY', tq, oz + bz)
        self.set_key(root, 'translateY', end, oz)

    def set_spine_chest_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        t3 = [start, mid, end]
        t5 = [start, self.quarter, mid, self.three_quarter, end]
        def apply_joint(ctrl, p):
            if not ctrl:
                return
            rz = self.pattern_thirds(p['swing_rz'])
            rx = self.pattern_thirds(p['sway_rx'])
            ry = self.pattern_fifths(p['rock_ry'])
            offY = float(p.get('offsetY', 0.0))
            for t, v in zip(t3, rz):
                self.set_key(ctrl, 'rotateZ', t, v)
            for t, v in zip(t5, ry):
                self.set_key(ctrl, 'rotateY', t, v + offY)
            for t, v in zip(t3, rx):
                self.set_key(ctrl, 'rotateX', t, v)
        spine = self.resolve_first_existing(self.spine_ctrl_candidates)
        chest = self.chest_ctrl if cmds.objExists(self.chest_ctrl) else None
        apply_joint(spine, self.spine_params)
        apply_joint(chest, self.chest_params)

    def set_hip_keys(self):
        self.apply_keyframe_pattern((self.hip_ctrl, 'rotateZ'),
                                    [self.hip_params['swing'], -self.hip_params['swing'], self.hip_params['swing']])
        self.apply_keyframe_pattern((self.hip_ctrl, 'rotateY'),
                                    [self.hip_params['sway'], -self.hip_params['sway'], self.hip_params['sway']])

    def set_feet_follow_keys(self):
        right = self.feet['right']; left = self.feet['left']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter; times = [start, q, mid, tq, end]
        ff = self.feet_follow
        blend = float(ff['moveFeetWithRoot']); off_x = float(ff['offset_x'])
        off_y = float(ff['offset_y']); off_z = float(ff['offset_z'])
        rot_x = float(ff['rotate_x']); bounce = float(ff.get('bounce_y', 0.0))
        swing = float(ff.get('swing_x', 0.0)); back_f = float(ff.get('back_forth_z', 0.0))

        def root_val(attr, t):
            try:
                return cmds.getAttr(f"{self.root_ctrl}.{attr}", time=t) if cmds.objExists(self.root_ctrl) else 0.0
            except Exception:
                return 0.0

        def add_tx(t):
            return swing if (t == start or t == end) else (-swing if t == mid else 0.0)
        def add_ty(t):
            return bounce if (t == q or t == tq) else 0.0
        def add_tz(t):
            return back_f if (t == q or t == tq) else 0.0

        for t in times:
            baseY = root_val('translateX', t) * blend + off_y
            baseZ = root_val('translateY', t) * blend + off_z
            baseRX = root_val('rotateZ', t) * blend + rot_x
            ax = add_tx(t); ay = add_ty(t); az = add_tz(t)
            self.set_key(right, 'translateX', t, off_x + ax)
            self.set_key(right, 'translateY', t, baseY + ay)
            self.set_key(right, 'translateZ', t, baseZ + az)
            self.set_key(right, 'rotateX', t, baseRX)
            self.set_key(left, 'translateX', t, -off_x + ax)
            self.set_key(left, 'translateY', t, baseY + ay)
            self.set_key(left, 'translateZ', t, baseZ + az)
            self.set_key(left, 'rotateX', t, baseRX)

    def set_scapula_keys(self):
        times = [f[0] for f in self.frames_stride_halved]
        sp = self.scapula_params
        offY = float(sp.get('offsetY', 0.0)); offX = float(sp.get('offsetX', 0.0))
        offZ = float(sp.get('offsetZ', 0.0))
        for side in ['left', 'right']:
            ctrl = self.scapula_ctrls[side]; sign = 1 if side == 'left' else -1
            y_vals = [sign * sp['rotateY'], -sign * sp['rotateY'], sign * sp['rotateY']]
            x_vals = [sp['rotateX'], -sp['rotateX'], sp['rotateX']]
            z_vals = [sign * sp['rotateZ'], -sign * sp['rotateZ'], sign * sp['rotateZ']]
            for t, y, x, z in zip(times, y_vals, x_vals, z_vals):
                self.set_key(ctrl, 'rotateY', t, y + offY)
                self.set_key(ctrl, 'rotateX', t, x + offX)
                self.set_key(ctrl, 'rotateZ', t, z + offZ)

    def set_head_and_neck_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        t3 = [start, mid, end]; t5 = [start, self.quarter, mid, self.three_quarter, end]
        def apply_joint(ctrl, p):
            rz = self.pattern_thirds(p['counter_rotateZ'])
            rx = self.pattern_thirds(p['counter_rotateX'])
            ry = self.pattern_fifths(p['counter_rotateY'])
            offY = float(p.get('offsetY', 0.0))
            for t, v in zip(t3, rz):
                self.set_key(ctrl, 'rotateZ', t, v)
            for t, v in zip(t3, rx):
                self.set_key(ctrl, 'rotateX', t, v)
            for t, v in zip(t5, ry):
                self.set_key(ctrl, 'rotateY', t, v + offY)
            tx = self.pattern_fifths(p['bounce_tx']); ty = self.pattern_fifths(p['bob_ty'])
            tz = self.pattern_thirds(p['sway_tz'])
            for t, v in zip(t5, tx):
                self.set_key(ctrl, 'translateX', t, v)
            for t, v in zip(t5, ty):
                self.set_key(ctrl, 'translateY', t, v)
            for t, v in zip(t3, tz):
                self.set_key(ctrl, 'translateZ', t, v)
        if cmds.objExists(self.head_ctrls['neck']):
            apply_joint(self.head_ctrls['neck'], self.neck_params)
        if cmds.objExists(self.head_ctrls['head']):
            apply_joint(self.head_ctrls['head'], self.head_params)

    def set_legs_fk_keys_and_blend(self):
        start, end = self.timeline_range()
        blend = max(0.0, min(10.0, float(self.legs_fk_params['fkik_blend'])))
        for side in ['right', 'left']:
            node = self.fkik_nodes.get(side)
            if node and cmds.objExists(node) and cmds.attributeQuery('FKIKBlend', node=node, exists=True):
                for t in (start, end):
                    try:
                        self.set_key(node, 'FKIKBlend', t, blend)
                    except Exception:
                        pass
        pairs = [('FKHip_R', 'FKHip_L', self.legs_fk_params['hip_ry']),
                 ('FKKnee_R', 'FKKnee_L', self.legs_fk_params['knee_ry']),
                 ('FKFoot_R', 'FKFoot_L', self.legs_fk_params['foot_ry']),
                 ('FKToe_R', 'FKToe_L', self.legs_fk_params['toe_ry'])]
        for r_n, l_n, val in pairs:
            for node in (r_n, l_n):
                if cmds.objExists(node) and cmds.attributeQuery('rotateY', node=node, exists=True):
                    for t in (start, end):
                        try:
                            self.set_key(node, 'rotateY', t, float(val))
                        except Exception:
                            pass

    def set_elbow_pole_keys(self):
        if not self.frames_stride_halved:
            return
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        q = self.quarter; tq = self.three_quarter; times = [start, q, mid, tq, end]
        r_ctrl = self.elbow_ctrls.get('right'); l_ctrl = self.elbow_ctrls.get('left')
        out = float(self.elbow_params.get('out', 0.0))
        up = float(self.elbow_params.get('up', 0.0))
        fwd = float(self.elbow_params.get('forward', 0.0))
        off = self.elbow_params.get('offset', {'x': 0, 'y': 0, 'z': 0})
        r_off = {'x': off['x'], 'y': off['y'], 'z': off['z']}
        l_off = {'x': -off['x'], 'y': off['y'], 'z': off['z']}
        rx = [r_off['x'], r_off['x'] + out, r_off['x'], r_off['x'], r_off['x']]
        ry = [r_off['y'], r_off['y'] + up, r_off['y'], r_off['y'], r_off['y']]
        rz = [r_off['z'], r_off['z'] + fwd, r_off['z'], r_off['z'], r_off['z']]
        lx = [l_off['x'], l_off['x'], l_off['x'], l_off['x'] - out, l_off['x']]
        ly = [l_off['y'], l_off['y'], l_off['y'], l_off['y'] + up, l_off['y']]
        lz = [l_off['z'], l_off['z'], l_off['z'], l_off['z'] + fwd, l_off['z']]
        if r_ctrl and cmds.objExists(r_ctrl):
            for t, vx, vy, vz in zip(times, rx, ry, rz):
                self.set_key(r_ctrl, 'translateX', t, vx)
                self.set_key(r_ctrl, 'translateY', t, vy)
                self.set_key(r_ctrl, 'translateZ', t, vz)
        if l_ctrl and cmds.objExists(l_ctrl):
            for t, vx, vy, vz in zip(times, lx, ly, lz):
                self.set_key(l_ctrl, 'translateX', t, vx)
                self.set_key(l_ctrl, 'translateY', t, vy)
                self.set_key(l_ctrl, 'translateZ', t, vz)

    def clamp_hands_ty_two_stage_ground(self):
        start, end = self.timeline_range()
        s = int(math.floor(start)); e = int(math.ceil(end))
        gh = float(self.groundHeight); attr = 'translateY'
        controls = [c for c in self.stride_limbs.values() if c and cmds.objExists(c)]
        for ctrl in controls:
            if not cmds.attributeQuery(attr, node=ctrl, exists=True):
                continue
            for t in range(s, e + 1):
                try:
                    val = cmds.getAttr(f"{ctrl}.{attr}", time=t)
                except Exception:
                    continue
                if val is not None and val < gh:
                    try:
                        cmds.setKeyframe(ctrl, attribute=attr, t=t, v=val)
                    except Exception:
                        pass
            key_times = cmds.keyframe(ctrl, at=attr, q=True, timeChange=True) or []
            seen = set()
            for kt in key_times:
                if kt in seen:
                    continue
                seen.add(kt)
                try:
                    v = cmds.getAttr(f"{ctrl}.{attr}", time=kt)
                except Exception:
                    continue
                if v is not None and v < gh:
                    try:
                        cmds.setKeyframe(ctrl, attribute=attr, t=kt, v=gh)
                    except Exception:
                        pass

    # ---------- generate ----------
    def create_walk_cycle(self, *args):
        self._read_ui()
        original_time = cmds.currentTime(query=True)
        self.clear_keys(); self.compute_frame_data()
        self.set_stride_keys(); self.set_root_keys()
        self.set_spine_chest_keys(); self.set_hip_keys()
        self.set_feet_follow_keys(); self.set_scapula_keys()
        self.set_head_and_neck_keys(); self.set_legs_fk_keys_and_blend()
        self.set_elbow_pole_keys(); self.set_arm_stretch_keys()
        if self.clamp_hands_to_ground:
            self.clamp_hands_ty_two_stage_ground()
        self.stretch_arms = cmds.floatSlider(self.stretch_slider, q=True, value=True)
        cmds.currentTime(original_time, edit=True)

    def _read_ui(self):
        self.stride = cmds.floatField(self.stride_field, q=True, v=True)
        self.stride_width = cmds.floatField(self.stride_width_field, q=True, v=True)
        self.stride_height = cmds.floatField(self.stride_height_field, q=True, v=True)
        self.hand_offsets['offset_x'] = cmds.floatField(self.offset_x_field, q=True, v=True)
        self.hand_offsets['offset_y'] = cmds.floatField(self.offset_y_field, q=True, v=True)
        self.hand_offsets['offset_z'] = cmds.floatField(self.offset_z_field, q=True, v=True)
        self.hand_offsets['rotation_y'] = cmds.floatField(self.rotate_y_field, q=True, v=True)
        for k in ('offset_y', 'offset_z', 'offset_rx', 'bounce', 'sway', 'rock', 'shift_x', 'swing_z', 'bounce_z'):
            fld = getattr(self, f'root_{k.replace("offset_", "offset_").replace("rx","offset_rx")}_field' if 'offset' in k or k == 'rx'
                          else f'root_{k}_field', None)
        self.root_params['offset_y'] = cmds.floatField(self.root_offset_y_field, q=True, v=True)
        self.root_params['offset_z'] = cmds.floatField(self.root_offset_z_field, q=True, v=True)
        self.root_params['offset_rx'] = cmds.floatField(self.root_offset_rx_field, q=True, v=True)
        self.root_params['bounce'] = cmds.floatField(self.root_bounce_field, q=True, v=True)
        self.root_params['sway'] = cmds.floatField(self.root_sway_field, q=True, v=True)
        self.root_params['rock'] = cmds.floatField(self.root_rock_field, q=True, v=True)
        self.root_params['shift_x'] = cmds.floatField(self.root_shift_x_field, q=True, v=True)
        self.root_params['swing_z'] = cmds.floatField(self.root_swing_z_field, q=True, v=True)
        self.root_params['bounce_z'] = cmds.floatField(self.root_bounce_z_field, q=True, v=True)
        self.spine_params['swing_rz'] = cmds.floatField(self.spine_rz_field, q=True, v=True)
        self.spine_params['rock_ry'] = cmds.floatField(self.spine_ry_field, q=True, v=True)
        self.spine_params['sway_rx'] = cmds.floatField(self.spine_rx_field, q=True, v=True)
        self.spine_params['offsetY'] = cmds.floatField(self.spine_ry_offset_field, q=True, v=True)
        self.chest_params['swing_rz'] = cmds.floatField(self.chest_rz_field, q=True, v=True)
        self.chest_params['rock_ry'] = cmds.floatField(self.chest_ry_field, q=True, v=True)
        self.chest_params['sway_rx'] = cmds.floatField(self.chest_rx_field, q=True, v=True)
        self.chest_params['offsetY'] = cmds.floatField(self.chest_ry_offset_field, q=True, v=True)
        self.hip_params['swing'] = cmds.floatField(self.hip_swing_field, q=True, v=True)
        self.hip_params['sway'] = cmds.floatField(self.hip_sway_field, q=True, v=True)
        self.feet_follow['moveFeetWithRoot'] = cmds.floatSlider(self.move_feet_slider, q=True, v=True)
        for k in ('offset_x', 'offset_y', 'offset_z', 'rotate_x'):
            self.feet_follow[k] = cmds.floatField(getattr(self, f'feet_{k}_field'), q=True, v=True)
        self.feet_follow['bounce_y'] = cmds.floatField(self.feet_bounce_y_field, q=True, v=True)
        self.feet_follow['swing_x'] = cmds.floatField(self.feet_swing_x_field, q=True, v=True)
        self.feet_follow['back_forth_z'] = cmds.floatField(self.feet_backforth_z_field, q=True, v=True)
        self.scapula_params['rotateZ'] = cmds.floatField(self.scapula_z_field, q=True, v=True)
        self.scapula_params['rotateX'] = cmds.floatField(self.scapula_x_field, q=True, v=True)
        self.scapula_params['rotateY'] = cmds.floatField(self.scapula_y_field, q=True, v=True)
        self.scapula_params['offsetZ'] = cmds.floatField(self.scapula_offset_z_field, q=True, v=True)
        self.scapula_params['offsetX'] = cmds.floatField(self.scapula_offset_x_field, q=True, v=True)
        self.scapula_params['offsetY'] = cmds.floatField(self.scapula_offset_y_field, q=True, v=True)
        self.legs_fk_params['fkik_blend'] = cmds.floatSlider(self.fkik_slider, q=True, v=True)
        self.legs_fk_params['hip_ry'] = cmds.floatField(self.fk_hip_ry_field, q=True, v=True)
        self.legs_fk_params['knee_ry'] = cmds.floatField(self.fk_knee_ry_field, q=True, v=True)
        self.legs_fk_params['foot_ry'] = cmds.floatField(self.fk_foot_ry_field, q=True, v=True)
        self.legs_fk_params['toe_ry'] = cmds.floatField(self.fk_toe_ry_field, q=True, v=True)
        for p, prefix in [(self.neck_params, 'neck'), (self.head_params, 'head')]:
            p['counter_rotateX'] = cmds.floatField(getattr(self, f'{prefix}_rx_field'), q=True, v=True)
            p['counter_rotateY'] = cmds.floatField(getattr(self, f'{prefix}_ry_field'), q=True, v=True)
            p['counter_rotateZ'] = cmds.floatField(getattr(self, f'{prefix}_rz_field'), q=True, v=True)
            p['bounce_tx'] = cmds.floatField(getattr(self, f'{prefix}_tx_field'), q=True, v=True)
            p['bob_ty'] = cmds.floatField(getattr(self, f'{prefix}_ty_field'), q=True, v=True)
            p['sway_tz'] = cmds.floatField(getattr(self, f'{prefix}_tz_field'), q=True, v=True)
            p['offsetY'] = cmds.floatField(getattr(self, f'{prefix}_ry_off_field'), q=True, v=True)
        self.groundHeight = cmds.floatField(self.ground_height_field, q=True, v=True)
        self.clamp_hands_to_ground = cmds.checkBox(self.clamp_checkbox, q=True, v=True)
        self.elbow_params['offset']['x'] = cmds.floatField(self.elbow_off_x, q=True, v=True)
        self.elbow_params['offset']['y'] = cmds.floatField(self.elbow_off_y, q=True, v=True)
        self.elbow_params['offset']['z'] = cmds.floatField(self.elbow_off_z, q=True, v=True)
        self.elbow_params['out'] = cmds.floatField(self.elbow_out_field, q=True, v=True)
        self.elbow_params['up'] = cmds.floatField(self.elbow_up_field, q=True, v=True)
        self.elbow_params['forward'] = cmds.floatField(self.elbow_forward_field, q=True, v=True)

    # ---------- settings ----------
    def _coerce(self, sect, keys):
        for k in keys:
            if k in sect:
                try:
                    sect[k] = float(sect[k])
                except Exception:
                    pass

    def print_settings(self, *args):
        settings = {
            'stride': self.stride, 'stride_width': self.stride_width, 'stride_height': self.stride_height,
            'offsets': self.hand_offsets.copy(), 'root': self.root_params.copy(),
            'hip': self.hip_params.copy(), 'feet_follow': self.feet_follow.copy(),
            'scapula': self.scapula_params.copy(),
            'neck': self.neck_params.copy(), 'head': self.head_params.copy(),
            'groundHeight': self.groundHeight, 'clampHandsToGround': self.clamp_hands_to_ground,
            'stretchArms': self.stretch_arms,
            'spine': self.spine_params.copy(), 'chest': self.chest_params.copy(),
            'legs_fk': self.legs_fk_params.copy(),
            'elbow': {
                'out': self.elbow_params['out'], 'up': self.elbow_params['up'],
                'forward': self.elbow_params['forward'], 'offset': self.elbow_params['offset'].copy(),
            },
        }
        self.print_settings_json("HandWalkCycleTool", settings)

    def apply_settings(self, settings):
        self.stride = settings.get('stride', self.stride)
        self.stride_width = settings.get('stride_width', self.stride_width)
        self.stride_height = settings.get('stride_height', self.stride_height)
        self.hand_offsets.update(settings.get('offsets', {}))
        self.feet_follow.update(settings.get('feet_follow', {}))
        self.scapula_params.update(settings.get('scapula', {}))
        self.neck_params.update(settings.get('neck', {}))
        self.head_params.update(settings.get('head', {}))
        self._coerce(self.neck_params, ['counter_rotateX', 'counter_rotateY', 'counter_rotateZ',
                                        'bounce_tx', 'bob_ty', 'sway_tz', 'offsetY'])
        self._coerce(self.head_params, ['counter_rotateX', 'counter_rotateY', 'counter_rotateZ',
                                        'bounce_tx', 'bob_ty', 'sway_tz', 'offsetY'])
        if 'head' in settings and 'neck' not in settings:
            self.neck_params.update({k: settings['head'].get(k, self.neck_params[k]) for k in self.neck_params})
        self.groundHeight = settings.get('groundHeight', self.groundHeight)
        self.clamp_hands_to_ground = settings.get('clampHandsToGround', self.clamp_hands_to_ground)
        if 'stretchArms' in settings:
            try:
                self.stretch_arms = float(settings['stretchArms'])
            except Exception:
                pass
        self.spine_params.update(settings.get('spine', {}))
        self.chest_params.update(settings.get('chest', {}))
        self._coerce(self.spine_params, ['swing_rz', 'rock_ry', 'sway_rx', 'offsetY'])
        self._coerce(self.chest_params, ['swing_rz', 'rock_ry', 'sway_rx', 'offsetY'])
        self.legs_fk_params.update(settings.get('legs_fk', {}))
        self._coerce(self.legs_fk_params, ['fkik_blend', 'hip_ry', 'knee_ry', 'foot_ry', 'toe_ry'])
        ep = settings.get('elbow')
        if ep:
            for k in ('out', 'up', 'forward'):
                if k in ep:
                    try:
                        self.elbow_params[k] = float(ep[k])
                    except Exception:
                        pass
            if 'offset' in ep:
                self.elbow_params['offset'].update(ep['offset'])
        self.root_params.update(settings.get('root', {}))
        self._coerce(self.root_params, ['offset_y', 'offset_z', 'offset_rx', 'bounce', 'sway', 'rock',
                                        'shift_x', 'swing_z', 'bounce_z'])
        self.update_ui_fields()

    def update_ui_fields(self):
        def _sf(fld, val):
            try:
                cmds.floatField(fld, e=True, value=val)
            except Exception:
                pass
        _sf(self.stride_field, self.stride)
        _sf(self.stride_width_field, self.stride_width)
        _sf(self.stride_height_field, self.stride_height)
        _sf(self.offset_x_field, self.hand_offsets['offset_x'])
        _sf(self.offset_y_field, self.hand_offsets['offset_y'])
        _sf(self.offset_z_field, self.hand_offsets['offset_z'])
        _sf(self.rotate_y_field, self.hand_offsets['rotation_y'])
        _sf(self.root_offset_y_field, self.root_params['offset_y'])
        _sf(self.root_offset_z_field, self.root_params['offset_z'])
        _sf(self.root_offset_rx_field, self.root_params['offset_rx'])
        _sf(self.root_bounce_field, self.root_params['bounce'])
        _sf(self.root_sway_field, self.root_params['sway'])
        _sf(self.root_rock_field, self.root_params['rock'])
        for a in ('shift_x', 'swing_z', 'bounce_z'):
            if hasattr(self, f'root_{a}_field'):
                _sf(getattr(self, f'root_{a}_field'), self.root_params.get(a, 0.0))
        try:
            cmds.floatSlider(self.move_feet_slider, e=True, value=self.feet_follow['moveFeetWithRoot'])
        except Exception:
            pass
        for k in ('offset_x', 'offset_y', 'offset_z', 'rotate_x'):
            if hasattr(self, f'feet_{k}_field'):
                _sf(getattr(self, f'feet_{k}_field'), self.feet_follow[k])
        for k, attr in [('bounce_y', 'feet_bounce_y_field'), ('swing_x', 'feet_swing_x_field'),
                        ('back_forth_z', 'feet_backforth_z_field')]:
            if hasattr(self, attr):
                _sf(getattr(self, attr), self.feet_follow.get(k, 0.0))
        _sf(self.scapula_z_field, self.scapula_params['rotateZ'])
        _sf(self.scapula_x_field, self.scapula_params['rotateX'])
        _sf(self.scapula_y_field, self.scapula_params['rotateY'])
        for a in ('offsetZ', 'offsetX', 'offsetY'):
            fld = f'scapula_offset_{a[-1].lower()}_field'
            if hasattr(self, fld):
                _sf(getattr(self, fld), self.scapula_params.get(a, 0.0))
        for prefix, params in [('neck', self.neck_params), ('head', self.head_params)]:
            for k, fld_suffix in [('counter_rotateZ', 'rz'), ('counter_rotateX', 'rx'),
                                  ('counter_rotateY', 'ry'), ('bounce_tx', 'tx'),
                                  ('bob_ty', 'ty'), ('sway_tz', 'tz'), ('offsetY', 'ry_off')]:
                fld = f'{prefix}_{fld_suffix}_field'
                if hasattr(self, fld):
                    _sf(getattr(self, fld), params.get(k, 0.0))
        _sf(self.hip_swing_field, self.hip_params['swing'])
        _sf(self.hip_sway_field, self.hip_params['sway'])
        if hasattr(self, 'ground_height_field'):
            _sf(self.ground_height_field, self.groundHeight)
        if hasattr(self, 'clamp_checkbox'):
            try:
                cmds.checkBox(self.clamp_checkbox, e=True, value=self.clamp_hands_to_ground)
            except Exception:
                pass
        if hasattr(self, 'stretch_slider'):
            try:
                cmds.floatSlider(self.stretch_slider, e=True, value=self.stretch_arms)
            except Exception:
                pass
        if hasattr(self, 'fkik_slider'):
            try:
                cmds.floatSlider(self.fkik_slider, e=True, value=self.legs_fk_params['fkik_blend'])
            except Exception:
                pass
        for fld, key in [(getattr(self, 'fk_hip_ry_field', None), 'hip_ry'),
                         (getattr(self, 'fk_knee_ry_field', None), 'knee_ry'),
                         (getattr(self, 'fk_foot_ry_field', None), 'foot_ry'),
                         (getattr(self, 'fk_toe_ry_field', None), 'toe_ry')]:
            if fld:
                _sf(fld, self.legs_fk_params[key])
        for a in ('swing_rz', 'rock_ry', 'sway_rx', 'offsetY'):
            s_fld = f'spine_{"ry_offset" if a == "offsetY" else a.split("_")[1]}_field'
            c_fld = f'chest_{"ry_offset" if a == "offsetY" else a.split("_")[1]}_field'
            if hasattr(self, s_fld):
                _sf(getattr(self, s_fld), self.spine_params.get(a, 0.0))
            if hasattr(self, c_fld):
                _sf(getattr(self, c_fld), self.chest_params.get(a, 0.0))
        if hasattr(self, 'elbow_out_field'):
            _sf(self.elbow_out_field, self.elbow_params['out'])
            _sf(self.elbow_up_field, self.elbow_params['up'])
            _sf(self.elbow_forward_field, self.elbow_params['forward'])
        for fld_name, k in [('elbow_off_x', 'x'), ('elbow_off_y', 'y'), ('elbow_off_z', 'z')]:
            if hasattr(self, fld_name):
                _sf(getattr(self, fld_name), self.elbow_params['offset'][k])

    def prompt_and_apply_settings(self, *args):
        self.prompt_and_apply(lambda s: self.apply_settings(s))

    # ---------- UI ----------
    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE, widthHeight=self.WINDOW_SIZE, sizeable=True)
        main = cmds.formLayout(numberOfDivisions=100)

        # LEFT COLUMN
        leftScroll = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        cmds.frameLayout(label="Stride Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Stride Length"); self.stride_field = cmds.floatField(value=self.stride, bgc=self.COLOR_Z)
        cmds.text(label="Stride Width (X)"); self.stride_width_field = cmds.floatField(value=self.stride_width, bgc=self.COLOR_X)
        cmds.text(label="Stride Height (Y)"); self.stride_height_field = cmds.floatField(value=self.stride_height, bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Root Controls (RootX_M)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Offset Y"); self.root_offset_y_field = cmds.floatField(value=self.root_params['offset_y'], bgc=self.COLOR_Y)
        cmds.text(label="Offset Z"); self.root_offset_z_field = cmds.floatField(value=self.root_params['offset_z'], bgc=self.COLOR_Z)
        cmds.text(label="Offset Rock (rotateX)"); self.root_offset_rx_field = cmds.floatField(value=self.root_params['offset_rx'], bgc=self.COLOR_X)
        cmds.text(label="Bounce (translateY)"); self.root_bounce_field = cmds.floatField(value=self.root_params['bounce'], bgc=self.COLOR_Y)
        cmds.text(label="Side Sway (rotateY)"); self.root_sway_field = cmds.floatField(value=self.root_params['sway'], bgc=self.COLOR_Y)
        cmds.text(label="Rock (rotateX)"); self.root_rock_field = cmds.floatField(value=self.root_params['rock'], bgc=self.COLOR_X)
        cmds.text(label="Shift (translateX)"); self.root_shift_x_field = cmds.floatField(value=self.root_params['shift_x'], bgc=self.COLOR_X)
        cmds.text(label="Swing (rotateZ)"); self.root_swing_z_field = cmds.floatField(value=self.root_params['swing_z'], bgc=self.COLOR_Z)
        cmds.text(label="Bounce Fwd (translateZ)"); self.root_bounce_z_field = cmds.floatField(value=self.root_params.get('bounce_z', 0.0), bgc=self.COLOR_Z)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Spine & Chest", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.text(label="SPINE", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Swing rotateZ"); self.spine_rz_field = cmds.floatField(value=self.spine_params['swing_rz'], bgc=self.COLOR_Z)
        cmds.text(label="Offset Y (add)"); self.spine_ry_offset_field = cmds.floatField(value=self.spine_params['offsetY'], bgc=self.COLOR_Y)
        cmds.text(label="Rock rotateY"); self.spine_ry_field = cmds.floatField(value=self.spine_params['rock_ry'], bgc=self.COLOR_Y)
        cmds.text(label="Sway rotateX"); self.spine_rx_field = cmds.floatField(value=self.spine_params['sway_rx'], bgc=self.COLOR_X)
        cmds.setParent('..')
        cmds.separator(height=8, style='in')
        cmds.text(label="CHEST", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Swing rotateZ"); self.chest_rz_field = cmds.floatField(value=self.chest_params['swing_rz'], bgc=self.COLOR_Z)
        cmds.text(label="Offset Y (add)"); self.chest_ry_offset_field = cmds.floatField(value=self.chest_params['offsetY'], bgc=self.COLOR_Y)
        cmds.text(label="Rock rotateY"); self.chest_ry_field = cmds.floatField(value=self.chest_params['rock_ry'], bgc=self.COLOR_Y)
        cmds.text(label="Sway rotateX"); self.chest_rx_field = cmds.floatField(value=self.chest_params['sway_rx'], bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Scapula Movement", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Rotate Y"); self.scapula_y_field = cmds.floatField(value=self.scapula_params['rotateY'], bgc=self.COLOR_Y)
        cmds.text(label="Offset Y (add)"); self.scapula_offset_y_field = cmds.floatField(value=self.scapula_params.get('offsetY', 0.0), bgc=self.COLOR_Y)
        cmds.text(label="Rotate X"); self.scapula_x_field = cmds.floatField(value=self.scapula_params['rotateX'], bgc=self.COLOR_X)
        cmds.text(label="Offset X (add)"); self.scapula_offset_x_field = cmds.floatField(value=self.scapula_params.get('offsetX', 0.0), bgc=self.COLOR_X)
        cmds.text(label="Rotate Z"); self.scapula_z_field = cmds.floatField(value=self.scapula_params['rotateZ'], bgc=self.COLOR_Z)
        cmds.text(label="Offset Z (add)"); self.scapula_offset_z_field = cmds.floatField(value=self.scapula_params.get('offsetZ', 0.0), bgc=self.COLOR_Z)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Neck & Head Motion", collapsable=True, marginWidth=10, marginHeight=5)
        for prefix, params, label in [('neck', self.neck_params, 'NECK'), ('head', self.head_params, 'HEAD')]:
            cmds.text(label=label, align='left')
            cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
            cmds.text(label="Counter Rotate Z"); setattr(self, f'{prefix}_rz_field', cmds.floatField(value=params['counter_rotateZ'], bgc=self.COLOR_Z))
            cmds.text(label="Counter Rotate X"); setattr(self, f'{prefix}_rx_field', cmds.floatField(value=params['counter_rotateX'], bgc=self.COLOR_X))
            cmds.text(label="Counter Rotate Y"); setattr(self, f'{prefix}_ry_field', cmds.floatField(value=params['counter_rotateY'], bgc=self.COLOR_Y))
            cmds.text(label="Offset Y (add)"); setattr(self, f'{prefix}_ry_off_field', cmds.floatField(value=params.get('offsetY', 0.0), bgc=self.COLOR_Y))
            cmds.text(label="Bounce X tx"); setattr(self, f'{prefix}_tx_field', cmds.floatField(value=params['bounce_tx'], bgc=self.COLOR_X))
            cmds.text(label="Bob Y ty"); setattr(self, f'{prefix}_ty_field', cmds.floatField(value=params['bob_ty'], bgc=self.COLOR_Y))
            cmds.text(label="Sway Z tz"); setattr(self, f'{prefix}_tz_field', cmds.floatField(value=params['sway_tz'], bgc=self.COLOR_Z))
            cmds.setParent('..')
            if prefix == 'neck':
                cmds.separator(height=8, style='in')
        cmds.setParent('..')

        cmds.setParent('..'); cmds.setParent('..')  # left column

        # RIGHT COLUMN
        rightScroll = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        cmds.frameLayout(label="Elbow Poles", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.text(label="Offsets (X mirrored on LEFT)", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Offset X"); self.elbow_off_x = cmds.floatField(value=self.elbow_params['offset']['x'], bgc=self.COLOR_X)
        cmds.text(label="Offset Y"); self.elbow_off_y = cmds.floatField(value=self.elbow_params['offset']['y'], bgc=self.COLOR_Y)
        cmds.text(label="Offset Z"); self.elbow_off_z = cmds.floatField(value=self.elbow_params['offset']['z'], bgc=self.COLOR_Z)
        cmds.setParent('..')
        cmds.separator(height=6, style='in')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Out (translate X)"); self.elbow_out_field = cmds.floatField(value=self.elbow_params['out'], bgc=self.COLOR_X)
        cmds.text(label="Up (translate Y)"); self.elbow_up_field = cmds.floatField(value=self.elbow_params['up'], bgc=self.COLOR_Y)
        cmds.text(label="Forward (translate Z)"); self.elbow_forward_field = cmds.floatField(value=self.elbow_params['forward'], bgc=self.COLOR_Z)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Hip Controls", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Hip Swing (rotateX)"); self.hip_swing_field = cmds.floatField(value=self.hip_params['swing'], bgc=self.COLOR_X)
        cmds.text(label="Hip Sway (rotateY)"); self.hip_sway_field = cmds.floatField(value=self.hip_params['sway'], bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Feet Follow Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Move Feet With Root"); self.move_feet_slider = cmds.floatSlider(min=0, max=1, value=self.feet_follow['moveFeetWithRoot'], step=0.01)
        cmds.text(label="Offset X (mirrored)"); self.feet_offset_x_field = cmds.floatField(value=self.feet_follow['offset_x'], bgc=self.COLOR_X)
        cmds.text(label="Swing X (no mirror)"); self.feet_swing_x_field = cmds.floatField(value=self.feet_follow.get('swing_x', 0.0), bgc=self.COLOR_X)
        cmds.text(label="Offset Y"); self.feet_offset_y_field = cmds.floatField(value=self.feet_follow['offset_y'], bgc=self.COLOR_Y)
        cmds.text(label="Bounce Y"); self.feet_bounce_y_field = cmds.floatField(value=self.feet_follow.get('bounce_y', 0.0), bgc=self.COLOR_Y)
        cmds.text(label="Offset Z"); self.feet_offset_z_field = cmds.floatField(value=self.feet_follow['offset_z'], bgc=self.COLOR_Z)
        cmds.text(label="Back/Forth Z"); self.feet_backforth_z_field = cmds.floatField(value=self.feet_follow.get('back_forth_z', 0.0), bgc=self.COLOR_Z)
        cmds.text(label="Rotate X"); self.feet_rotate_x_field = cmds.floatField(value=self.feet_follow['rotate_x'], bgc=self.COLOR_X)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Legs Forward Kinematics", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 170), (2, 180)])
        cmds.text(label="FK/IK Blend (0..10)")
        self.fkik_slider = cmds.floatSlider(min=0, max=10, value=self.legs_fk_params['fkik_blend'], step=0.1)
        cmds.setParent('..')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 170), (2, 180)])
        cmds.text(label="Hip rotate Y"); self.fk_hip_ry_field = cmds.floatField(value=self.legs_fk_params['hip_ry'], bgc=self.COLOR_Y)
        cmds.text(label="Knee rotate Y"); self.fk_knee_ry_field = cmds.floatField(value=self.legs_fk_params['knee_ry'], bgc=self.COLOR_Y)
        cmds.text(label="Foot rotate Y"); self.fk_foot_ry_field = cmds.floatField(value=self.legs_fk_params['foot_ry'], bgc=self.COLOR_Y)
        cmds.text(label="Toe rotate Y"); self.fk_toe_ry_field = cmds.floatField(value=self.legs_fk_params['toe_ry'], bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Hand Position Offsets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Offset X"); self.offset_x_field = cmds.floatField(value=self.hand_offsets['offset_x'], bgc=self.COLOR_X)
        cmds.text(label="Offset Y"); self.offset_y_field = cmds.floatField(value=self.hand_offsets['offset_y'], bgc=self.COLOR_Y)
        cmds.text(label="Offset Z"); self.offset_z_field = cmds.floatField(value=self.hand_offsets['offset_z'], bgc=self.COLOR_Z)
        cmds.text(label="Rotate Y"); self.rotate_y_field = cmds.floatField(value=self.hand_offsets['rotation_y'], bgc=self.COLOR_Y)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Ground Clamp", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Ground Height (Y)"); self.ground_height_field = cmds.floatField(value=self.groundHeight, bgc=self.COLOR_Y)
        cmds.text(label="Clamp Hands"); self.clamp_checkbox = cmds.checkBox(value=self.clamp_hands_to_ground)
        cmds.text(label="Stretch Arms (0-10)"); self.stretch_slider = cmds.floatSlider(min=0, max=10, value=self.stretch_arms, step=0.1)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.frameLayout(label="Actions & Presets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
        cmds.button(label="Create Hand Walk Cycle", height=36, command=self.create_walk_cycle)
        cmds.separator(height=8, style='in')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(250, 250))
        cmds.button(label="Print Current Settings", command=self.print_settings)
        cmds.button(label="Apply Settings From String", command=self.prompt_and_apply_settings)
        cmds.setParent('..'); cmds.setParent('..')

        cmds.setParent('..'); cmds.setParent('..')  # right column

        cmds.formLayout(main, e=True,
                        attachForm=[(leftScroll, 'top', 8), (leftScroll, 'left', 8), (leftScroll, 'bottom', 8),
                                    (rightScroll, 'top', 8), (rightScroll, 'right', 8), (rightScroll, 'bottom', 8)],
                        attachPosition=[(leftScroll, 'right', 6, 50), (rightScroll, 'left', 6, 50)])
        cmds.showWindow(self.window)
