import json
import maya.cmds as cmds
from .base import AnimGeneratorBase


class FlightGenerator(AnimGeneratorBase):
    WINDOW_NAME = "FlightGeneratorWindow"
    WINDOW_TITLE = "Flight Generator"
    WINDOW_SIZE = (760, 820)

    def __init__(self):
        super().__init__()

        # Controls
        self.root     = "RootX_M"
        self.ik_arm_l = "IKArm_L"
        self.ik_arm_r = "IKArm_R"
        self.fkik_l   = "FKIKArm_L"
        self.fkik_r   = "FKIKArm_R"
        self.scap_l   = "FKScapula_L"
        self.scap_r   = "FKScapula_R"
        self.pole_l   = "PoleArm_L"
        self.pole_r   = "PoleArm_R"

        # IK Arms translateZ
        self.ik_arms_down = 300.0
        self.ik_arms_up   = -200.0
        self.arm_rotateX_value = -90.0

        # Hand flap
        self.hand_flap_down = -90.0
        self.hand_flap_up   = 90.0

        # Hand positioning
        self.hands_base_x = 100.0
        self.hands_x_q    = -300.0
        self.hands_x_mid  = 100.0
        self.hands_x_3q   = 0.0
        self.hands_base_y = 0.0
        self.hands_flap   = 0.0

        # Torso
        self.spine = "FKSpine1_M"
        self.chest = "FKChest_M"
        self.neck  = "FKNeck_M"
        self.head  = "FKHead_M"

        # Stretch & Bend Posture
        self.spine_off = 0.0; self.spine_1_3 = 0.0; self.spine_2_3 = 0.0
        self.chest_off = 0.0; self.chest_1_3 = 0.0; self.chest_2_3 = 0.0
        self.neck_off  = 0.0; self.neck_1_3  = 0.0; self.neck_2_3  = 0.0
        self.head_off  = 0.0; self.head_1_3  = 0.0; self.head_2_3  = 0.0

        # FK/IK blend
        self.fkik_blend_value = 10.0

        # Root movement
        self.root_updown_base = 6.0
        self.root_updown_mid  = -12.0
        self.root_backforth_base = 0.0
        self.root_backforth_mid  = 0.0
        self.root_bf_off = 0.0
        self.root_bf_q   = 0.0
        self.root_bf_mid = 0.0
        self.root_bf_3q  = 0.0

        # IK Legs
        self.leg_l = "IKLeg_L"
        self.leg_r = "IKLeg_R"
        self.leg_tx_base = 0.0; self.leg_tx_q = 0.0; self.leg_tx_mid = 0.0; self.leg_tx_3q = 0.0
        self.leg_ty_base = 0.0; self.leg_ty_q = 0.0; self.leg_ty_mid = 0.0; self.leg_ty_3q = 0.0
        self.leg_tz_base = 0.0; self.leg_tz_q = 0.0; self.leg_tz_mid = 0.0; self.leg_tz_3q = 0.0
        self.leg_rx_off = 45.0; self.leg_rx_q = 0.0; self.leg_rx_mid = 0.0; self.leg_rx_3q = 0.0

        # Scapula
        self.scap_flap_base = 45.0
        self.scap_flap_mid  = -35.0
        self.scap_rz_off  = 0.0
        self.scap_rx_off  = 0.0; self.scap_rx_base = 0.0; self.scap_rx_mid = 0.0
        self.scap_ry_off  = 0.0; self.scap_ry_base = 0.0; self.scap_ry_mid = 0.0

        # Elbow poles
        self.pole_off_x = 0.0; self.pole_base_x = 0.0; self.pole_mid_x = 0.0
        self.pole_off_y = 0.0; self.pole_base_y = 0.0; self.pole_mid_y = 0.0
        self.pole_off_z = 0.0; self.pole_base_z = 0.0; self.pole_mid_z = 0.0

    # ------------------------------------------------------------------ #
    #  Keying
    # ------------------------------------------------------------------ #
    def clear_keys(self):
        s, e = self.timeline_range()
        for node, attrs in [
            (self.ik_arm_l, ["translateZ", "rotateX", "rotateY", "translateX", "translateY"]),
            (self.ik_arm_r, ["translateZ", "rotateX", "rotateY", "translateX", "translateY"]),
            (self.fkik_l,   ["FKIKBlend"]),
            (self.fkik_r,   ["FKIKBlend"]),
            (self.spine, ["rotateZ"]),
            (self.chest, ["rotateZ"]),
            (self.neck,  ["rotateZ"]),
            (self.head,  ["rotateZ"]),
            (self.root,  ["translateY"]),
            (self.leg_l, ["translateX", "translateY", "translateZ", "rotateX"]),
            (self.leg_r, ["translateX", "translateY", "translateZ", "rotateX"]),
            (self.root,  ["translateZ", "rotateX"]),
            (self.scap_l, ["rotateZ", "rotateY", "rotateX"]),
            (self.scap_r, ["rotateZ", "rotateY", "rotateX"]),
            (self.pole_l, ["translateX", "translateY", "translateZ"]),
            (self.pole_r, ["translateX", "translateY", "translateZ"]),
        ]:
            resolved = self.resolve_node(node) or node
            for a in attrs:
                self.cut_attr_keys_in_range(resolved, a, s, e, reset_to_zero=True)

    def key_arms(self):
        start, quarter, _, three_quarter, end = self.frames
        for node in [self.ik_arm_l, self.ik_arm_r]:
            self.set_key(node, "translateZ", start,         0.0)
            self.set_key(node, "translateZ", quarter,       float(self.ik_arms_down))
            self.set_key(node, "translateZ", three_quarter, float(self.ik_arms_up))
            self.set_key(node, "translateZ", end,           0.0)
        for node in [self.ik_arm_l, self.ik_arm_r]:
            val = float(self.arm_rotateX_value)
            self.set_key(node, "rotateX", start, val)
            self.set_key(node, "rotateX", end,   val)

    def key_hand_flap(self):
        start, quarter, mid, three_quarter, end = self.frames
        pairs = [(self.ik_arm_l, +1.0), (self.ik_arm_r, -1.0)]
        for node, sgn in pairs:
            self.set_key(node, "rotateY", start,         0.0)
            self.set_key(node, "rotateY", quarter,       sgn * float(self.hand_flap_down))
            self.set_key(node, "rotateY", three_quarter, sgn * float(self.hand_flap_up))
            self.set_key(node, "rotateY", end,           0.0)

    def key_hand_positioning(self):
        start, quarter, mid, three_quarter, end = self.frames
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

        baseY = float(self.hands_base_y)
        flapY = float(self.hands_flap)
        for node in [self.ik_arm_l, self.ik_arm_r]:
            self.set_key(node, "translateY", start,         baseY)
            self.set_key(node, "translateY", quarter,       baseY + flapY)
            self.set_key(node, "translateY", three_quarter, baseY)
            self.set_key(node, "translateY", end,           baseY)

    def key_stretch_bend_posture(self):
        start, _, _, _, end = self.frames
        third       = start + (end - start) / 3.0
        two_thirds  = start + 2.0 * (end - start) / 3.0

        def do(node, off, v1, v2):
            self.set_key(node, "rotateZ", start,      float(off))
            self.set_key(node, "rotateZ", third,      float(off) + float(v1))
            self.set_key(node, "rotateZ", two_thirds, float(off) + float(v2))
            self.set_key(node, "rotateZ", end,        float(off))

        do(self.spine, self.spine_off, self.spine_1_3, self.spine_2_3)
        do(self.chest, self.chest_off, self.chest_1_3, self.chest_2_3)
        do(self.neck,  self.neck_off,  self.neck_1_3,  self.neck_2_3)
        do(self.head,  self.head_off,  self.head_1_3,  self.head_2_3)

    def key_root_movement(self):
        start, quarter, mid, three_quarter, end = self.frames
        baseZ = float(self.root_updown_base)
        midZ  = float(self.root_updown_mid)
        self.set_key(self.root, "translateZ", start,         baseZ)
        self.set_key(self.root, "translateZ", quarter,       midZ)
        self.set_key(self.root, "translateZ", three_quarter, -midZ)
        self.set_key(self.root, "translateZ", end,           baseZ)

        off = float(self.root_bf_off)
        q = float(self.root_bf_q)
        m = float(self.root_bf_mid)
        q3 = float(self.root_bf_3q)
        self.set_key(self.root, "translateY", start,         off)
        self.set_key(self.root, "translateY", quarter,       off + q)
        self.set_key(self.root, "translateY", mid,           off + m)
        self.set_key(self.root, "translateY", three_quarter, off + q3)
        self.set_key(self.root, "translateY", end,           off)

        baseRX = float(self.root_backforth_base)
        midRX  = float(self.root_backforth_mid)
        self.set_key(self.root, "rotateX", start,         baseRX)
        self.set_key(self.root, "rotateX", quarter,       midRX)
        self.set_key(self.root, "rotateX", three_quarter, -midRX)
        self.set_key(self.root, "rotateX", end,           baseRX)

    def key_legs(self):
        start, quarter, mid, three_quarter, end = self.frames

        bx = float(self.leg_tx_base); qx = float(self.leg_tx_q); mx = float(self.leg_tx_mid); q3x = float(self.leg_tx_3q)
        for node, sgn in [(self.leg_l, +1.0), (self.leg_r, -1.0)]:
            self.set_key(node, "translateX", start,         sgn * bx)
            self.set_key(node, "translateX", quarter,       sgn * (bx + qx))
            self.set_key(node, "translateX", mid,           sgn * (bx + mx))
            self.set_key(node, "translateX", three_quarter, sgn * (bx + q3x))
            self.set_key(node, "translateX", end,           sgn * bx)

        by = float(self.leg_ty_base); qy = float(self.leg_ty_q); my = float(self.leg_ty_mid); q3y = float(self.leg_ty_3q)
        for node in [self.leg_l, self.leg_r]:
            self.set_key(node, "translateY", start,         by)
            self.set_key(node, "translateY", quarter,       by + qy)
            self.set_key(node, "translateY", mid,           by + my)
            self.set_key(node, "translateY", three_quarter, by + q3y)
            self.set_key(node, "translateY", end,           by)

        bz = float(self.leg_tz_base); qz = float(self.leg_tz_q); mz = float(self.leg_tz_mid); q3z = float(self.leg_tz_3q)
        for node in [self.leg_l, self.leg_r]:
            self.set_key(node, "translateZ", start,         bz)
            self.set_key(node, "translateZ", quarter,       bz + qz)
            self.set_key(node, "translateZ", mid,           bz + mz)
            self.set_key(node, "translateZ", three_quarter, bz + q3z)
            self.set_key(node, "translateZ", end,           bz)

        roff = float(self.leg_rx_off); rq = float(self.leg_rx_q); rm = float(self.leg_rx_mid); r3 = float(self.leg_rx_3q)
        for node in [self.leg_l, self.leg_r]:
            self.set_key(node, "rotateX", start,         roff)
            self.set_key(node, "rotateX", quarter,       roff + rq)
            self.set_key(node, "rotateX", mid,           roff + rm)
            self.set_key(node, "rotateX", three_quarter, roff + r3)
            self.set_key(node, "rotateX", end,           roff)

    def key_scapula(self):
        start, quarter, mid, three_quarter, end = self.frames
        rz_off = float(self.scap_rz_off)
        rz_b   = float(self.scap_flap_base)
        rz_m   = float(self.scap_flap_mid)
        rx_off = float(self.scap_rx_off); rx_b = float(self.scap_rx_base); rx_m = float(self.scap_rx_mid)
        ry_off = float(self.scap_ry_off); ry_b = float(self.scap_ry_base); ry_m = float(self.scap_ry_mid)

        for node in [self.scap_l, self.scap_r]:
            self.set_key(node, "rotateZ", start,         rz_off)
            self.set_key(node, "rotateZ", quarter,       rz_off + rz_b)
            self.set_key(node, "rotateZ", three_quarter, rz_off + rz_m)
            self.set_key(node, "rotateZ", end,           rz_off)
            self.set_key(node, "rotateY", start,         ry_off)
            self.set_key(node, "rotateY", quarter,       ry_off + ry_b)
            self.set_key(node, "rotateY", three_quarter, ry_off + ry_m)
            self.set_key(node, "rotateY", end,           ry_off)
            self.set_key(node, "rotateX", start,         rx_off)
            self.set_key(node, "rotateX", quarter,       rx_off + rx_b)
            self.set_key(node, "rotateX", three_quarter, rx_off + rx_m)
            self.set_key(node, "rotateX", end,           rx_off)

    def key_elbow_poles(self):
        start, quarter, mid, three_quarter, end = self.frames
        offX = float(self.pole_off_x); baseX = float(self.pole_base_x); midX = float(self.pole_mid_x)
        offY = float(self.pole_off_y); baseY = float(self.pole_base_y); midY = float(self.pole_mid_y)
        offZ = float(self.pole_off_z); baseZ = float(self.pole_base_z); midZ = float(self.pole_mid_z)

        for node, sgn in [(self.pole_l, +1.0), (self.pole_r, -1.0)]:
            self.set_key(node, "translateX", start,         sgn * offX)
            self.set_key(node, "translateX", quarter,       sgn * (offX + baseX))
            self.set_key(node, "translateX", three_quarter, sgn * (offX + midX))
            self.set_key(node, "translateX", end,           sgn * offX)
            self.set_key(node, "translateY", start,         offY)
            self.set_key(node, "translateY", quarter,       offY + baseY)
            self.set_key(node, "translateY", three_quarter, offY + midY)
            self.set_key(node, "translateY", end,           offY)
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
        self.key_stretch_bend_posture()
        self.key_legs()
        self.key_scapula()
        self.key_elbow_poles()
        self.key_fkik_blend()
        self.print_settings()
        try:
            cmds.inViewMessage(
                amg='[FlightGenerator] Keys set.',
                pos='midCenter', fade=True)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Settings I/O
    # ------------------------------------------------------------------ #
    def _get_settings_dict(self):
        return {
            'ik_arms_down': self.ik_arms_down, 'ik_arms_up': self.ik_arms_up,
            'arm_rotateX_value': self.arm_rotateX_value,
            'hand_flap_down': self.hand_flap_down, 'hand_flap_up': self.hand_flap_up,
            'hands_base_x': self.hands_base_x, 'hands_x_q': self.hands_x_q,
            'hands_x_mid': self.hands_x_mid, 'hands_x_3q': self.hands_x_3q,
            'hands_base_y': self.hands_base_y, 'hands_flap': self.hands_flap,
            'root_updown_base': self.root_updown_base, 'root_updown_mid': self.root_updown_mid,
            'root_backforth_base': self.root_backforth_base, 'root_backforth_mid': self.root_backforth_mid,
            'spine_off': self.spine_off, 'spine_1_3': self.spine_1_3, 'spine_2_3': self.spine_2_3,
            'chest_off': self.chest_off, 'chest_1_3': self.chest_1_3, 'chest_2_3': self.chest_2_3,
            'neck_off': self.neck_off, 'neck_1_3': self.neck_1_3, 'neck_2_3': self.neck_2_3,
            'head_off': self.head_off, 'head_1_3': self.head_1_3, 'head_2_3': self.head_2_3,
            'scap_flap_base': self.scap_flap_base, 'scap_flap_mid': self.scap_flap_mid,
            'scap_rz_off': self.scap_rz_off,
            'scap_rx_off': self.scap_rx_off, 'scap_rx_base': self.scap_rx_base, 'scap_rx_mid': self.scap_rx_mid,
            'scap_ry_off': self.scap_ry_off, 'scap_ry_base': self.scap_ry_base, 'scap_ry_mid': self.scap_ry_mid,
            'pole_off_x': self.pole_off_x, 'pole_base_x': self.pole_base_x, 'pole_mid_x': self.pole_mid_x,
            'pole_off_y': self.pole_off_y, 'pole_base_y': self.pole_base_y, 'pole_mid_y': self.pole_mid_y,
            'pole_off_z': self.pole_off_z, 'pole_base_z': self.pole_base_z, 'pole_mid_z': self.pole_mid_z,
            'fkik_blend_value': self.fkik_blend_value,
            'root_bf_off': self.root_bf_off, 'root_bf_q': self.root_bf_q,
            'root_bf_mid': self.root_bf_mid, 'root_bf_3q': self.root_bf_3q,
            'leg_tx_base': self.leg_tx_base, 'leg_tx_q': self.leg_tx_q,
            'leg_tx_mid': self.leg_tx_mid, 'leg_tx_3q': self.leg_tx_3q,
            'leg_ty_base': self.leg_ty_base, 'leg_ty_q': self.leg_ty_q,
            'leg_ty_mid': self.leg_ty_mid, 'leg_ty_3q': self.leg_ty_3q,
            'leg_tz_base': self.leg_tz_base, 'leg_tz_q': self.leg_tz_q,
            'leg_tz_mid': self.leg_tz_mid, 'leg_tz_3q': self.leg_tz_3q,
            'leg_rx_off': self.leg_rx_off, 'leg_rx_q': self.leg_rx_q,
            'leg_rx_mid': self.leg_rx_mid, 'leg_rx_3q': self.leg_rx_3q,
        }

    def print_settings(self, *args):
        self.print_settings_json("FlightGenerator", self._get_settings_dict())

    def apply_settings(self, settings):
        for k, v in settings.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if 'hands_x_q' not in settings and 'hands_x_flap' in settings:
            self.hands_x_q = settings['hands_x_flap']
        if 'hands_x_3q' not in settings and 'hands_apart' in settings:
            self.hands_x_3q = settings['hands_apart']

    def prompt_and_apply_settings(self, *args):
        self.prompt_and_apply(
            lambda s: (self.apply_settings(s),
                       cmds.evalDeferred(lambda *a: self.refresh_ui_fields())))

    def refresh_ui_fields(self):
        field_map = {
            'ik_arms_down_field': 'ik_arms_down', 'ik_arms_up_field': 'ik_arms_up',
            'arm_rotateX_field': 'arm_rotateX_value',
            'hand_flap_down_field': 'hand_flap_down', 'hand_flap_up_field': 'hand_flap_up',
            'hands_base_x_field': 'hands_base_x', 'hands_x_q_field': 'hands_x_q',
            'hands_x_mid_field': 'hands_x_mid', 'hands_x_3q_field': 'hands_x_3q',
            'hands_base_y_field': 'hands_base_y', 'hands_flap_field': 'hands_flap',
            'root_updown_base_field': 'root_updown_base', 'root_updown_mid_field': 'root_updown_mid',
            'root_backforth_base_field': 'root_backforth_base', 'root_backforth_mid_field': 'root_backforth_mid',
            'spine_off_field': 'spine_off', 'spine_1_3_field': 'spine_1_3', 'spine_2_3_field': 'spine_2_3',
            'chest_off_field': 'chest_off', 'chest_1_3_field': 'chest_1_3', 'chest_2_3_field': 'chest_2_3',
            'neck_off_field': 'neck_off', 'neck_1_3_field': 'neck_1_3', 'neck_2_3_field': 'neck_2_3',
            'head_off_field': 'head_off', 'head_1_3_field': 'head_1_3', 'head_2_3_field': 'head_2_3',
            'scap_rz_off_field': 'scap_rz_off', 'scap_flap_base_field': 'scap_flap_base',
            'scap_flap_mid_field': 'scap_flap_mid',
            'scap_ry_off_field': 'scap_ry_off', 'scap_ry_base_field': 'scap_ry_base',
            'scap_ry_mid_field': 'scap_ry_mid',
            'scap_rx_off_field': 'scap_rx_off', 'scap_rx_base_field': 'scap_rx_base',
            'scap_rx_mid_field': 'scap_rx_mid',
            'pole_off_x_field': 'pole_off_x', 'pole_base_x_field': 'pole_base_x',
            'pole_mid_x_field': 'pole_mid_x',
            'pole_off_y_field': 'pole_off_y', 'pole_base_y_field': 'pole_base_y',
            'pole_mid_y_field': 'pole_mid_y',
            'pole_off_z_field': 'pole_off_z', 'pole_base_z_field': 'pole_base_z',
            'pole_mid_z_field': 'pole_mid_z',
            'root_bf_off_field': 'root_bf_off', 'root_bf_q_field': 'root_bf_q',
            'root_bf_mid_field': 'root_bf_mid', 'root_bf_3q_field': 'root_bf_3q',
        }
        for field_attr, data_attr in field_map.items():
            self.try_set_float(getattr(self, field_attr, None), getattr(self, data_attr))
        self.try_set_float(getattr(self, 'fkik_blend_slider', None), self.fkik_blend_value)
        for name in ['leg_tx_base_field', 'leg_tx_q_field', 'leg_tx_mid_field', 'leg_tx_3q_field',
                      'leg_ty_base_field', 'leg_ty_q_field', 'leg_ty_mid_field', 'leg_ty_3q_field',
                      'leg_tz_base_field', 'leg_tz_q_field', 'leg_tz_mid_field', 'leg_tz_3q_field',
                      'leg_rx_off_field', 'leg_rx_q_field', 'leg_rx_mid_field', 'leg_rx_3q_field']:
            self.try_set_float(getattr(self, name, None), getattr(self, name.replace('_field', '')))

    # ------------------------------------------------------------------ #
    #  on_generate  (read UI -> self, then generate)
    # ------------------------------------------------------------------ #
    def on_generate(self, *args):
        self.ik_arms_down      = cmds.floatField(self.ik_arms_down_field, q=True, v=True)
        self.ik_arms_up        = cmds.floatField(self.ik_arms_up_field,   q=True, v=True)
        self.arm_rotateX_value = cmds.floatField(self.arm_rotateX_field,  q=True, v=True)
        self.hand_flap_down    = cmds.floatField(self.hand_flap_down_field, q=True, v=True)
        self.hand_flap_up      = cmds.floatField(self.hand_flap_up_field,   q=True, v=True)
        self.hands_base_x = cmds.floatField(self.hands_base_x_field, q=True, v=True)
        self.hands_x_q    = cmds.floatField(self.hands_x_q_field,    q=True, v=True)
        self.hands_x_mid  = cmds.floatField(self.hands_x_mid_field,  q=True, v=True)
        self.hands_x_3q   = cmds.floatField(self.hands_x_3q_field,   q=True, v=True)
        self.hands_base_y = cmds.floatField(self.hands_base_y_field, q=True, v=True)
        self.hands_flap   = cmds.floatField(self.hands_flap_field,   q=True, v=True)
        self.root_updown_base    = cmds.floatField(self.root_updown_base_field,    q=True, v=True)
        self.root_updown_mid     = cmds.floatField(self.root_updown_mid_field,     q=True, v=True)
        self.root_backforth_base = cmds.floatField(self.root_backforth_base_field, q=True, v=True)
        self.root_backforth_mid  = cmds.floatField(self.root_backforth_mid_field,  q=True, v=True)
        self.root_bf_off = cmds.floatField(self.root_bf_off_field, q=True, v=True)
        self.root_bf_q   = cmds.floatField(self.root_bf_q_field,   q=True, v=True)
        self.root_bf_mid = cmds.floatField(self.root_bf_mid_field, q=True, v=True)
        self.root_bf_3q  = cmds.floatField(self.root_bf_3q_field,  q=True, v=True)
        for name in ['leg_tx_base', 'leg_tx_q', 'leg_tx_mid', 'leg_tx_3q',
                      'leg_ty_base', 'leg_ty_q', 'leg_ty_mid', 'leg_ty_3q',
                      'leg_tz_base', 'leg_tz_q', 'leg_tz_mid', 'leg_tz_3q',
                      'leg_rx_off', 'leg_rx_q', 'leg_rx_mid', 'leg_rx_3q']:
            setattr(self, name, cmds.floatField(getattr(self, name + '_field'), q=True, v=True))
        self.spine_off = cmds.floatField(self.spine_off_field, q=True, v=True)
        self.spine_1_3 = cmds.floatField(self.spine_1_3_field, q=True, v=True)
        self.spine_2_3 = cmds.floatField(self.spine_2_3_field, q=True, v=True)
        self.chest_off = cmds.floatField(self.chest_off_field, q=True, v=True)
        self.chest_1_3 = cmds.floatField(self.chest_1_3_field, q=True, v=True)
        self.chest_2_3 = cmds.floatField(self.chest_2_3_field, q=True, v=True)
        self.neck_off = cmds.floatField(self.neck_off_field, q=True, v=True)
        self.neck_1_3 = cmds.floatField(self.neck_1_3_field, q=True, v=True)
        self.neck_2_3 = cmds.floatField(self.neck_2_3_field, q=True, v=True)
        self.head_off = cmds.floatField(self.head_off_field, q=True, v=True)
        self.head_1_3 = cmds.floatField(self.head_1_3_field, q=True, v=True)
        self.head_2_3 = cmds.floatField(self.head_2_3_field, q=True, v=True)
        self.scap_rz_off    = cmds.floatField(self.scap_rz_off_field,   q=True, v=True)
        self.scap_flap_base = cmds.floatField(self.scap_flap_base_field, q=True, v=True)
        self.scap_flap_mid  = cmds.floatField(self.scap_flap_mid_field,  q=True, v=True)
        self.scap_ry_off  = cmds.floatField(self.scap_ry_off_field,  q=True, v=True)
        self.scap_ry_base = cmds.floatField(self.scap_ry_base_field, q=True, v=True)
        self.scap_ry_mid  = cmds.floatField(self.scap_ry_mid_field,  q=True, v=True)
        self.scap_rx_off  = cmds.floatField(self.scap_rx_off_field,  q=True, v=True)
        self.scap_rx_base = cmds.floatField(self.scap_rx_base_field, q=True, v=True)
        self.scap_rx_mid  = cmds.floatField(self.scap_rx_mid_field,  q=True, v=True)
        self.pole_off_x  = cmds.floatField(self.pole_off_x_field,  q=True, v=True)
        self.pole_base_x = cmds.floatField(self.pole_base_x_field, q=True, v=True)
        self.pole_mid_x  = cmds.floatField(self.pole_mid_x_field,  q=True, v=True)
        self.pole_off_y  = cmds.floatField(self.pole_off_y_field,  q=True, v=True)
        self.pole_base_y = cmds.floatField(self.pole_base_y_field, q=True, v=True)
        self.pole_mid_y  = cmds.floatField(self.pole_mid_y_field,  q=True, v=True)
        self.pole_off_z  = cmds.floatField(self.pole_off_z_field,  q=True, v=True)
        self.pole_base_z = cmds.floatField(self.pole_base_z_field, q=True, v=True)
        self.pole_mid_z  = cmds.floatField(self.pole_mid_z_field,  q=True, v=True)
        self.fkik_blend_value = cmds.floatSlider(self.fkik_blend_slider, q=True, v=True)
        self.generate()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #
    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title=self.WINDOW_TITLE,
                                  widthHeight=self.WINDOW_SIZE, sizeable=True)
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        # -- IK Arms --
        cmds.frameLayout(label="IK Arms", collapsable=True, marginWidth=10)
        self.two_col_row(
            "IK Arms down (Z @ 1/4):", lambda: setattr(self, 'ik_arms_down_field', cmds.floatField(value=self.ik_arms_down)),
            "IK Arms up (Z @ 3/4):",   lambda: setattr(self, 'ik_arms_up_field',   cmds.floatField(value=self.ik_arms_up)),
            widths=(320, 100, 320, 100))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 100))
        cmds.text(label="IK Arms rotateX (start=end):")
        self.arm_rotateX_field = cmds.floatField(value=self.arm_rotateX_value)
        cmds.setParent('..'); cmds.setParent('..')

        # -- Hand Flap --
        cmds.frameLayout(label="Hand Flap (IK rotateY, L/R oppose)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Hand Flap down (1/4):", lambda: setattr(self, 'hand_flap_down_field', cmds.floatField(value=self.hand_flap_down)),
            "Hand Flap up (3/4):",   lambda: setattr(self, 'hand_flap_up_field',   cmds.floatField(value=self.hand_flap_up)),
            widths=(320, 100, 320, 100))
        cmds.setParent('..')

        # -- Hand Positioning --
        cmds.frameLayout(label="Hand Positioning (IK translates)", collapsable=True, marginWidth=10)
        row = cmds.rowLayout(numberOfColumns=8, adjustableColumn=8)
        for i, w in [(1,120),(2,80),(3,120),(4,80),(5,120),(6,80),(7,120),(8,80)]:
            cmds.rowLayout(row, e=True, columnWidth=(i, w))
        cmds.text(label="Base X (L=+, R=-):");  self.hands_base_x_field = cmds.floatField(value=self.hands_base_x)
        cmds.text(label="X @ 1/4:");            self.hands_x_q_field    = cmds.floatField(value=self.hands_x_q)
        cmds.text(label="X @ 1/2:");            self.hands_x_mid_field  = cmds.floatField(value=self.hands_x_mid)
        cmds.text(label="X @ 3/4:");            self.hands_x_3q_field   = cmds.floatField(value=self.hands_x_3q)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(160, 100, 140, 100), adjustableColumn=4)
        cmds.text(label="Base Y:"); self.hands_base_y_field = cmds.floatField(value=self.hands_base_y)
        cmds.text(label="Flap (Y @ 1/4):"); self.hands_flap_field = cmds.floatField(value=self.hands_flap)
        cmds.setParent('..'); cmds.setParent('..')

        # -- Root Movement --
        cmds.frameLayout(label="Root Movement (RootX_M)", collapsable=True, marginWidth=10)
        self.two_col_row(
            "Up/Down Base (translateZ):", lambda: setattr(self, 'root_updown_base_field', cmds.floatField(value=self.root_updown_base)),
            "Up/Down Mid (translateZ):",  lambda: setattr(self, 'root_updown_mid_field',  cmds.floatField(value=self.root_updown_mid)),
            widths=(320, 100, 320, 100))
        self.two_col_row(
            "Back/Forth Base (rotateX):", lambda: setattr(self, 'root_backforth_base_field', cmds.floatField(value=self.root_backforth_base)),
            "Back/Forth Mid (rotateX):",  lambda: setattr(self, 'root_backforth_mid_field',  cmds.floatField(value=self.root_backforth_mid)),
            widths=(320, 100, 320, 100))
        row = cmds.rowLayout(numberOfColumns=8, adjustableColumn=8)
        for i, w in [(1,160),(2,90),(3,120),(4,90),(5,120),(6,90),(7,140),(8,90)]:
            cmds.rowLayout(row, e=True, columnWidth=(i, w))
        cmds.text(label="Back/Forth Y Offset:"); self.root_bf_off_field = cmds.floatField(value=self.root_bf_off)
        cmds.text(label="Y @ 1/4:");             self.root_bf_q_field   = cmds.floatField(value=self.root_bf_q)
        cmds.text(label="Y @ 1/2:");             self.root_bf_mid_field = cmds.floatField(value=self.root_bf_mid)
        cmds.text(label="Y @ 3/4:");             self.root_bf_3q_field  = cmds.floatField(value=self.root_bf_3q)
        cmds.setParent('..'); cmds.setParent('..')

        # -- Stretch & Bend Posture --
        cmds.frameLayout(label="Stretch And Bend Posture", collapsable=True, marginWidth=10)
        def posture_row(title, off_attr, one_attr, two_attr):
            row = cmds.rowLayout(numberOfColumns=6, adjustableColumn=6)
            for i, w in [(1,140),(2,80),(3,90),(4,80),(5,90),(6,80)]:
                cmds.rowLayout(row, e=True, columnWidth=(i, w))
            cmds.text(label=title + " Off:")
            setattr(self, off_attr, cmds.floatField(value=getattr(self, off_attr.replace('_field', ''))))
            cmds.text(label="1/3:")
            setattr(self, one_attr, cmds.floatField(value=getattr(self, one_attr.replace('_field', ''))))
            cmds.text(label="2/3:")
            setattr(self, two_attr, cmds.floatField(value=getattr(self, two_attr.replace('_field', ''))))
            cmds.setParent('..')
        posture_row("Spine", 'spine_off_field', 'spine_1_3_field', 'spine_2_3_field')
        posture_row("Chest", 'chest_off_field', 'chest_1_3_field', 'chest_2_3_field')
        posture_row("Neck",  'neck_off_field',  'neck_1_3_field',  'neck_2_3_field')
        posture_row("Head",  'head_off_field',  'head_1_3_field',  'head_2_3_field')
        cmds.setParent('..')

        # -- Scapula --
        cmds.frameLayout(label="Scapula Rotations", collapsable=True, marginWidth=10)
        def scap_row(axis_label, off_attr, base_attr, mid_attr):
            row = cmds.rowLayout(numberOfColumns=6, adjustableColumn=6)
            for i, w in [(1,140),(2,90),(3,120),(4,90),(5,100),(6,90)]:
                cmds.rowLayout(row, e=True, columnWidth=(i, w))
            cmds.text(label=axis_label + " Offset:")
            setattr(self, off_attr,  cmds.floatField(value=getattr(self, off_attr.replace('_field', ''))))
            cmds.text(label=axis_label + " @ 1/4:")
            setattr(self, base_attr, cmds.floatField(value=getattr(self, base_attr.replace('_field', ''))))
            cmds.text(label=axis_label + " @ 3/4:")
            setattr(self, mid_attr,  cmds.floatField(value=getattr(self, mid_attr.replace('_field', ''))))
            cmds.setParent('..')
        scap_row("Z", 'scap_rz_off_field', 'scap_flap_base_field', 'scap_flap_mid_field')
        scap_row("Y", 'scap_ry_off_field', 'scap_ry_base_field',  'scap_ry_mid_field')
        scap_row("X", 'scap_rx_off_field', 'scap_rx_base_field',  'scap_rx_mid_field')
        cmds.setParent('..')

        # -- IK Legs --
        cmds.frameLayout(label="IK Legs (Feet)", collapsable=True, marginWidth=10)
        def legs_row(title, base_attr, q_attr, mid_attr, q3_attr, hint=""):
            row = cmds.rowLayout(numberOfColumns=8, adjustableColumn=8)
            for i, w in [(1,160),(2,90),(3,110),(4,90),(5,110),(6,90),(7,130),(8,90)]:
                cmds.rowLayout(row, e=True, columnWidth=(i, w))
            cmds.text(label=title + (" " + hint if hint else ""))
            setattr(self, base_attr, cmds.floatField(value=getattr(self, base_attr.replace('_field', ''))))
            cmds.text(label="@ 1/4:")
            setattr(self, q_attr, cmds.floatField(value=getattr(self, q_attr.replace('_field', ''))))
            cmds.text(label="@ 1/2:")
            setattr(self, mid_attr, cmds.floatField(value=getattr(self, mid_attr.replace('_field', ''))))
            cmds.text(label="@ 3/4:")
            setattr(self, q3_attr, cmds.floatField(value=getattr(self, q3_attr.replace('_field', ''))))
            cmds.setParent('..')
        legs_row("Feet Translate X (Base)", 'leg_tx_base_field', 'leg_tx_q_field', 'leg_tx_mid_field', 'leg_tx_3q_field', "(L=+, R=-)")
        legs_row("Feet Translate Y (Base)", 'leg_ty_base_field', 'leg_ty_q_field', 'leg_ty_mid_field', 'leg_ty_3q_field')
        legs_row("Feet Translate Z (Base)", 'leg_tz_base_field', 'leg_tz_q_field', 'leg_tz_mid_field', 'leg_tz_3q_field')
        row = cmds.rowLayout(numberOfColumns=8, adjustableColumn=8)
        for i, w in [(1,160),(2,90),(3,110),(4,90),(5,110),(6,90),(7,130),(8,90)]:
            cmds.rowLayout(row, e=True, columnWidth=(i, w))
        cmds.text(label="Feet Rotate X Offset:")
        self.leg_rx_off_field = cmds.floatField(value=self.leg_rx_off)
        cmds.text(label="@ 1/4:"); self.leg_rx_q_field   = cmds.floatField(value=self.leg_rx_q)
        cmds.text(label="@ 1/2:"); self.leg_rx_mid_field = cmds.floatField(value=self.leg_rx_mid)
        cmds.text(label="@ 3/4:"); self.leg_rx_3q_field  = cmds.floatField(value=self.leg_rx_3q)
        cmds.setParent('..'); cmds.setParent('..')

        # -- Elbow Poles --
        cmds.frameLayout(label="Elbow Poles (PoleArm_* translates)", collapsable=True, marginWidth=10)
        def three_col_row(l1, fn1, l2, fn2, l3, fn3):
            cmds.rowLayout(numberOfColumns=6, columnWidth6=(220, 90, 140, 90, 100, 90), adjustableColumn=6)
            cmds.text(label=l1); fn1()
            cmds.text(label=l2); fn2()
            cmds.text(label=l3); fn3()
            cmds.setParent('..')
        three_col_row("X Offset (L=+, R=- mirrored):",
            lambda: setattr(self, 'pole_off_x_field',  cmds.floatField(value=self.pole_off_x)),
            "X Base:", lambda: setattr(self, 'pole_base_x_field', cmds.floatField(value=self.pole_base_x)),
            "X Mid:",  lambda: setattr(self, 'pole_mid_x_field',  cmds.floatField(value=self.pole_mid_x)))
        three_col_row("Y Offset:",
            lambda: setattr(self, 'pole_off_y_field',  cmds.floatField(value=self.pole_off_y)),
            "Y Base:", lambda: setattr(self, 'pole_base_y_field', cmds.floatField(value=self.pole_base_y)),
            "Y Mid:",  lambda: setattr(self, 'pole_mid_y_field',  cmds.floatField(value=self.pole_mid_y)))
        three_col_row("Z Offset:",
            lambda: setattr(self, 'pole_off_z_field',  cmds.floatField(value=self.pole_off_z)),
            "Z Base:", lambda: setattr(self, 'pole_base_z_field', cmds.floatField(value=self.pole_base_z)),
            "Z Mid:",  lambda: setattr(self, 'pole_mid_z_field',  cmds.floatField(value=self.pole_mid_z)))
        cmds.setParent('..')

        # -- FK IK Blend --
        cmds.frameLayout(label="FK IK Blend", collapsable=True, marginWidth=10)
        self.fkik_blend_slider = cmds.floatSlider(min=0.0, max=10.0, value=self.fkik_blend_value, step=0.1)
        cmds.setParent('..')

        # -- Actions --
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(320, 320, 320), adjustableColumn=3)
        cmds.button(label="Generate Flight", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)
