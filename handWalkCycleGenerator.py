import maya.cmds as cmds
import json

class HandWalkCycleTool:
    def __init__(self):
        self.window = "HandWalkCycleWindow"
        self.stride = 8.0
        self.stride_width = 2.0
        self.stride_height = 3.0
        
        self.hand_offsets = {
            'offset_x': 2.0,
            'offset_y': -5.0,
            'offset_z': 0.0,
            'rotation_y': 0.0
        }

        # Ground clamp height (used to prevent hands from dipping below this)
        self.groundHeight = -57.04

        self.stride_limbs = {
            'right': "IKArm_R",
            'left': "IKArm_L"
        }

        self.root_ctrl = "RootX_M"
        
        self.hip_ctrl = "HipSwinger_M"
        
        self.root_params = {
            'offset_y': 0.0,
            'offset_z': 0.0,
            'offset_rx': 0.0,
            'bounce': 1.5,
            'sway': 2.0,
            'rock': 1.0
        }
        
        self.hip_params = {
            'swing': 10.0,
            'sway': 5.0
        }
        
        self.feet = {
            'right': "IKLeg_R",  # ✅ CORRECTED
            'left': "IKLeg_L"
        }

        
        self.feet_follow = {
            'moveFeetWithRoot': 1.0,
            'offset_x': 3.0,
            'offset_y': 5.0,
            'offset_z': 0.0,
            'rotate_x': 20.0
        }
        
        self.scapula_ctrls = {
            'left': "FKScapula_L",
            'right': "FKScapula_R"
        }
        self.scapula_params = {
            'rotateZ': 5.0,
            'rotateX': -10.0
        }
        
        # --- REPLACE THIS BLOCK ---
        self.head_ctrls = {
            'neck': "FKNeck_M",
            'head': "FKHead_M"
        }
        self.head_params = {
            'counter_rotateX': -5.0,
            'counter_rotateY': -5.0,
            'rock': 3.0  
        }
        # --- WITH THIS ---
        self.head_ctrls = {'neck': "FKNeck_M", 'head': "FKHead_M"}

        # per-joint params
        # rotateX/rotateY: thirds pattern; rotateZ: fifths
        # translateX (Bounce): fifths; translateY (Bob): fifths; translateZ (Sway): thirds
        self.neck_params = {
            'counter_rotateX': -3.0,   # thirds
            'counter_rotateY': -3.0,   # thirds
            'counter_rotateZ':  2.0,   # fifths
            'bounce_tx':        0.0,   # fifths
            'bob_ty':           0.5,   # fifths
            'sway_tz':          0.5    # thirds
        }
        self.head_params = {
            'counter_rotateX': -5.0,   # thirds
            'counter_rotateY': -5.0,   # thirds
            'counter_rotateZ':  3.0,   # fifths
            'bounce_tx':        0.0,   # fifths
            'bob_ty':           0.8,   # fifths
            'sway_tz':          0.8    # thirds
        }

        # Spine & Chest controls
        self.spine_ctrl_candidates = ["FKSpine_M", "FKSpine1_M"]  # alias support
        self.chest_ctrl = "FKChest_M"

        # Per-joint params
        # swing_rx: thirds, rock_rz: fifths, sway_ry: thirds
        self.spine_params = {
            'swing_rx': 5.0,
            'rock_rz': 3.0,
            'sway_ry': 3.0,
        }
        self.chest_params = {
            'swing_rx': 6.0,
            'rock_rz': 4.0,
            'sway_ry': 4.0,
        }



        self.frames_stride_halved = []

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Hand Walk Cycle Tool", widthHeight=(500, 300))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        cmds.frameLayout(label="Stride Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])

        cmds.text(label="Stride Length")
        self.stride_field = cmds.floatField(value=self.stride)

        cmds.text(label="Stride Width (X)")
        self.stride_width_field = cmds.floatField(value=self.stride_width)

        cmds.text(label="Stride Height (Y)")
        self.stride_height_field = cmds.floatField(value=self.stride_height)

        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.frameLayout(label="Root Controls (RootX_M)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        
        cmds.text(label="Offset Y (translateY)")
        self.root_offset_y_field = cmds.floatField(value=self.root_params['offset_y'])
        
        cmds.text(label="Offset Z (translateZ)")
        self.root_offset_z_field = cmds.floatField(value=self.root_params['offset_z'])
        
        cmds.text(label="Offset Rock (rotateX)")
        self.root_offset_rx_field = cmds.floatField(value=self.root_params['offset_rx'])
        
        cmds.text(label="Bounce (translateY)")
        self.root_bounce_field = cmds.floatField(value=self.root_params['bounce'])
        
        cmds.text(label="Side Sway (rotateY)")
        self.root_sway_field = cmds.floatField(value=self.root_params['sway'])
        
        cmds.text(label="Rock (rotateX)")
        self.root_rock_field = cmds.floatField(value=self.root_params['rock'])
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.frameLayout(label="Spine & Chest", collapsable=True, marginWidth=10, marginHeight=5)

        # Spine UI
        cmds.text(label="SPINE (FKSpine_M / FKSpine1_M)", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,150),(2,150)])
        cmds.text(label="Swing rotateX (thirds)")
        self.spine_rx_field = cmds.floatField(value=self.spine_params['swing_rx'])
        cmds.text(label="Rock rotateZ (fifths)")
        self.spine_rz_field = cmds.floatField(value=self.spine_params['rock_rz'])
        cmds.text(label="Sway rotateY (thirds)")
        self.spine_ry_field = cmds.floatField(value=self.spine_params['sway_ry'])
        cmds.setParent('..')

        cmds.separator(height=8, style='in')

        # Chest UI
        cmds.text(label="CHEST (FKChest_M)", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,150),(2,150)])
        cmds.text(label="Swing rotateX (thirds)")
        self.chest_rx_field = cmds.floatField(value=self.chest_params['swing_rx'])
        cmds.text(label="Rock rotateZ (fifths)")
        self.chest_rz_field = cmds.floatField(value=self.chest_params['rock_rz'])
        cmds.text(label="Sway rotateY (thirds)")
        self.chest_ry_field = cmds.floatField(value=self.chest_params['sway_ry'])
        cmds.setParent('..')
        cmds.setParent('..')

        
        cmds.frameLayout(label="Scapula Movement", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        cmds.text(label="Rotate Z")
        self.scapula_z_field = cmds.floatField(value=self.scapula_params['rotateZ'])
        cmds.text(label="Rotate X")
        self.scapula_x_field = cmds.floatField(value=self.scapula_params['rotateX'])
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.frameLayout(label="Neck & Head Motion", collapsable=True, marginWidth=10, marginHeight=5)

        # Neck row/column
        cmds.text(label="NECK", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,150),(2,150)])
        cmds.text(label="Counter Rotate X (thirds)")
        self.neck_rx_field = cmds.floatField(value=self.neck_params['counter_rotateX'])
        cmds.text(label="Counter Rotate Y (thirds)")
        self.neck_ry_field = cmds.floatField(value=self.neck_params['counter_rotateY'])
        cmds.text(label="Counter Rotate Z (fifths)")
        self.neck_rz_field = cmds.floatField(value=self.neck_params['counter_rotateZ'])
        cmds.text(label="Bounce X tx (fifths)")
        self.neck_tx_field = cmds.floatField(value=self.neck_params['bounce_tx'])
        cmds.text(label="Bob Y ty (fifths)")
        self.neck_ty_field = cmds.floatField(value=self.neck_params['bob_ty'])
        cmds.text(label="Sway Z tz (thirds)")
        self.neck_tz_field = cmds.floatField(value=self.neck_params['sway_tz'])
        cmds.setParent('..')

        cmds.separator(height=8, style='in')

        # Head row/column
        cmds.text(label="HEAD", align='left')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,150),(2,150)])
        cmds.text(label="Counter Rotate X (thirds)")
        self.head_rx_field = cmds.floatField(value=self.head_params['counter_rotateX'])
        cmds.text(label="Counter Rotate Y (thirds)")
        self.head_ry_field = cmds.floatField(value=self.head_params['counter_rotateY'])
        cmds.text(label="Counter Rotate Z (fifths)")
        self.head_rz_field = cmds.floatField(value=self.head_params['counter_rotateZ'])
        cmds.text(label="Bounce X tx (fifths)")
        self.head_tx_field = cmds.floatField(value=self.head_params['bounce_tx'])
        cmds.text(label="Bob Y ty (fifths)")
        self.head_ty_field = cmds.floatField(value=self.head_params['bob_ty'])
        cmds.text(label="Sway Z tz (thirds)")
        self.head_tz_field = cmds.floatField(value=self.head_params['sway_tz'])
        cmds.setParent('..')
        cmds.setParent('..')



        cmds.frameLayout(label="Hip Controls (HipSwinger_M)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        
        cmds.text(label="Hip Swing (rotateX)")
        self.hip_swing_field = cmds.floatField(value=self.hip_params['swing'])
        
        cmds.text(label="Hip Sway (rotateY)")
        self.hip_sway_field = cmds.floatField(value=self.hip_params['sway'])
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.frameLayout(label="Feet Follow Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        
        cmds.text(label="Move Feet With Root")
        self.move_feet_slider = cmds.floatSlider(min=0, max=1, value=self.feet_follow['moveFeetWithRoot'], step=0.01)
        
        cmds.text(label="Offset X (mirrored)")
        self.feet_offset_x_field = cmds.floatField(value=self.feet_follow['offset_x'])
        
        cmds.text(label="Offset Y")
        self.feet_offset_y_field = cmds.floatField(value=self.feet_follow['offset_y'])
        
        cmds.text(label="Offset Z")
        self.feet_offset_z_field = cmds.floatField(value=self.feet_follow['offset_z'])
        
        cmds.text(label="Rotate X")
        self.feet_rotate_x_field = cmds.floatField(value=self.feet_follow['rotate_x'])
        
        cmds.setParent('..')
        cmds.setParent('..')



        cmds.frameLayout(label="Hand Position Offsets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 150), (2, 150)])
        
        cmds.text(label="Offset X (side)")
        self.offset_x_field = cmds.floatField(value=self.hand_offsets['offset_x'])
        
        cmds.text(label="Offset Y (height)")
        self.offset_y_field = cmds.floatField(value=self.hand_offsets['offset_y'])
        
        cmds.text(label="Offset Z (forward)")
        self.offset_z_field = cmds.floatField(value=self.hand_offsets['offset_z'])
        
        cmds.text(label="Rotate Y")
        self.rotate_y_field = cmds.floatField(value=self.hand_offsets['rotation_y'])
        
        cmds.setParent('..')
        cmds.setParent('..')

        cmds.frameLayout(label="Ground Clamp", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,150),(2,150)])
        cmds.text(label="groundHeight (Y threshold)")
        self.ground_height_field = cmds.floatField(value=self.groundHeight)
        cmds.setParent('..')
        cmds.setParent('..')


        cmds.separator(height=10, style='in')
        cmds.button(label="Create Hand Walk Cycle", height=40, command=self.create_walk_cycle)
        cmds.separator(height=10, style='in')

        cmds.frameLayout(label="Presets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(250, 250), columnAlign=(1, 'left'))

        cmds.button(label="Print Current Settings", command=self.print_settings)
        cmds.button(label="Apply Settings From String", command=self.prompt_and_apply_settings)

        cmds.setParent('..')
        cmds.setParent('..')
        cmds.showWindow(self.window)

    def clear_keys(self):
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        
        all_controls = (
            list(self.stride_limbs.values()) +
            list(self.feet.values()) +
            [self.root_ctrl, self.hip_ctrl] +
            list(self.scapula_ctrls.values()) +
            list(self.head_ctrls.values())
        )

        
        for ctrl in all_controls:
            if not cmds.objExists(ctrl):
                continue
            for attr in attrs:
                if cmds.attributeQuery(attr, node=ctrl, exists=True):
                    try:
                        # Zero out value first
                        if not cmds.getAttr(f"{ctrl}.{attr}", lock=True):
                            cmds.setAttr(f"{ctrl}.{attr}", 0)
    
                        # Then clear animation keys
                        cmds.cutKey(ctrl, at=attr, time=(start, end))
                    except:
                        pass  # ignore locked/connected



    def create_walk_cycle(self, *args):
        self.stride = cmds.floatField(self.stride_field, query=True, value=True)
        self.stride_width = cmds.floatField(self.stride_width_field, query=True, value=True)
        self.stride_height = cmds.floatField(self.stride_height_field, query=True, value=True)
        
        self.hand_offsets['offset_x'] = cmds.floatField(self.offset_x_field, query=True, value=True)
        self.hand_offsets['offset_y'] = cmds.floatField(self.offset_y_field, query=True, value=True)
        self.hand_offsets['offset_z'] = cmds.floatField(self.offset_z_field, query=True, value=True)
        self.hand_offsets['rotation_y'] = cmds.floatField(self.rotate_y_field, query=True, value=True)
        
        self.root_params['offset_y'] = cmds.floatField(self.root_offset_y_field, q=True, value=True)
        self.root_params['offset_z'] = cmds.floatField(self.root_offset_z_field, q=True, value=True)
        self.root_params['offset_rx'] = cmds.floatField(self.root_offset_rx_field, q=True, value=True)
        self.root_params['bounce'] = cmds.floatField(self.root_bounce_field, q=True, value=True)
        self.root_params['sway'] = cmds.floatField(self.root_sway_field, q=True, value=True)
        self.root_params['rock'] = cmds.floatField(self.root_rock_field, q=True, value=True)
        
        # Spine/Chest UI reads
        self.spine_params['swing_rx'] = cmds.floatField(self.spine_rx_field, q=True, value=True)
        self.spine_params['rock_rz']  = cmds.floatField(self.spine_rz_field, q=True, value=True)
        self.spine_params['sway_ry']  = cmds.floatField(self.spine_ry_field, q=True, value=True)

        self.chest_params['swing_rx'] = cmds.floatField(self.chest_rx_field, q=True, value=True)
        self.chest_params['rock_rz']  = cmds.floatField(self.chest_rz_field, q=True, value=True)
        self.chest_params['sway_ry']  = cmds.floatField(self.chest_ry_field, q=True, value=True)

        
        self.hip_params['swing'] = cmds.floatField(self.hip_swing_field, q=True, value=True)
        self.hip_params['sway'] = cmds.floatField(self.hip_sway_field, q=True, value=True)
        
        self.feet_follow['moveFeetWithRoot'] = cmds.floatSlider(self.move_feet_slider, q=True, value=True)
        self.feet_follow['offset_x'] = cmds.floatField(self.feet_offset_x_field, q=True, value=True)
        self.feet_follow['offset_y'] = cmds.floatField(self.feet_offset_y_field, q=True, value=True)
        self.feet_follow['offset_z'] = cmds.floatField(self.feet_offset_z_field, q=True, value=True)
        self.feet_follow['rotate_x'] = cmds.floatField(self.feet_rotate_x_field, q=True, value=True)

        self.scapula_params['rotateZ'] = cmds.floatField(self.scapula_z_field, q=True, value=True)
        self.scapula_params['rotateX'] = cmds.floatField(self.scapula_x_field, q=True, value=True)
        # Neck fields
        self.neck_params['counter_rotateX'] = cmds.floatField(self.neck_rx_field, q=True, value=True)
        self.neck_params['counter_rotateY'] = cmds.floatField(self.neck_ry_field, q=True, value=True)
        self.neck_params['counter_rotateZ'] = cmds.floatField(self.neck_rz_field, q=True, value=True)
        self.neck_params['bounce_tx']      = cmds.floatField(self.neck_tx_field, q=True, value=True)
        self.neck_params['bob_ty']         = cmds.floatField(self.neck_ty_field, q=True, value=True)
        self.neck_params['sway_tz']        = cmds.floatField(self.neck_tz_field, q=True, value=True)

        # Head fields
        self.head_params['counter_rotateX'] = cmds.floatField(self.head_rx_field, q=True, value=True)
        self.head_params['counter_rotateY'] = cmds.floatField(self.head_ry_field, q=True, value=True)
        self.head_params['counter_rotateZ'] = cmds.floatField(self.head_rz_field, q=True, value=True)
        self.head_params['bounce_tx']       = cmds.floatField(self.head_tx_field, q=True, value=True)
        self.head_params['bob_ty']          = cmds.floatField(self.head_ty_field, q=True, value=True)
        self.head_params['sway_tz']         = cmds.floatField(self.head_tz_field, q=True, value=True)

        self.groundHeight = cmds.floatField(self.ground_height_field, q=True, value=True)


        original_time = cmds.currentTime(query=True)
        self.clear_keys()
        self.compute_frame_data()
        self.set_stride_keys()
        self.set_root_keys()
        self.set_spine_chest_keys()
        self.set_hip_keys()
        self.set_feet_follow_keys()
        self.set_scapula_keys()
        self.set_head_and_neck_keys()
        
        # finally: clamp hands so they never dip below ground
        # Enforce ground clamp on hands using the configured groundHeight
        self.clamp_hands_ty_two_stage_ground()
        
        cmds.currentTime(original_time, edit=True)
        
    def pattern_thirds(self, amp):
        # start, mid, end
        return [ amp, -amp, amp ]

    def pattern_fifths(self, amp):
        # start, quarter, mid, three_quarter, end
        return [ amp, -amp, amp, -amp, amp ]

    def compute_frame_data(self):
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        mid = (start + end) / 2.0
        self.quarter = (start + mid) / 2.0
        self.three_quarter = (mid + end) / 2.0

        self.frames_stride_halved = [
            (start,  self.stride / 2.0, -self.stride / 2.0),
            (mid,   -self.stride / 2.0,  self.stride / 2.0),
            (end,    self.stride / 2.0, -self.stride / 2.0)
        ]

    def set_key(self, obj, attr, time, value):
        cmds.currentTime(time, edit=True)
        try:
            cmds.setAttr(f"{obj}.{attr}", value)
            cmds.setKeyframe(obj, attribute=attr, t=time)
        except:
            pass  # skip if locked/connected

    def set_stride_keys(self):
        r = self.stride_limbs['right']
        l = self.stride_limbs['left']
        rz_values = [f[1] for f in self.frames_stride_halved]
        lz_values = [f[2] for f in self.frames_stride_halved]
    
        # Z
        for (t, val_r, val_l) in zip([f[0] for f in self.frames_stride_halved], rz_values, lz_values):
            self.set_key(r, 'translateZ', t, val_r + self.hand_offsets['offset_z'])
            self.set_key(l, 'translateZ', t, val_l + self.hand_offsets['offset_z'])
    
        # X
        for t in [f[0] for f in self.frames_stride_halved]:
            self.set_key(r, 'translateX', t, self.stride_width + self.hand_offsets['offset_x'])
            self.set_key(l, 'translateX', t, -self.stride_width - self.hand_offsets['offset_x'])
    
        # Y stride and lift
        self.set_key(l, 'translateY', self.quarter, self.stride_height + self.hand_offsets['offset_y'])
        self.set_key(r, 'translateY', self.three_quarter, self.stride_height + self.hand_offsets['offset_y'])
        for t in [f[0] for f in self.frames_stride_halved]:
            self.set_key(l, 'translateY', t, self.hand_offsets['offset_y'])
            self.set_key(r, 'translateY', t, self.hand_offsets['offset_y'])
    
        # Y rotation
        for t in [f[0] for f in self.frames_stride_halved]:
            self.set_key(r, 'rotateY', t, self.hand_offsets['rotation_y'])
            self.set_key(l, 'rotateY', t, -self.hand_offsets['rotation_y'])


    def set_root_keys(self):
        root = self.root_ctrl
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        offset_y = self.root_params['offset_y']
        offset_z = self.root_params['offset_z']
        offset_rx = self.root_params['offset_rx']
    
        # Bounce and Rock (5 keys)
        for attr, amp, off in [('translateY', self.root_params['bounce'], offset_y),
                               ('rotateX', self.root_params['rock'], offset_rx)]:
            self.set_key(root, attr, start,  amp + off)
            self.set_key(root, attr, self.quarter, -amp + off)
            self.set_key(root, attr, mid, amp + off)
            self.set_key(root, attr, self.three_quarter, -amp + off)
            self.set_key(root, attr, end, amp + off)
    
        # Sway (3 keys)
        self.set_key(root, 'rotateY', start,  self.root_params['sway'])
        self.set_key(root, 'rotateY', mid,   -self.root_params['sway'])
        self.set_key(root, 'rotateY', end,    self.root_params['sway'])
    
        # Offset Z (static)
        for t in [start, mid, end]:
            self.set_key(root, 'translateZ', t, offset_z)

    def resolve_first_existing(self, names):
        """Return the first existing node from a list of candidate names, else None."""
        for n in names:
            if n and cmds.objExists(n):
                return n
        return None

    def set_spine_chest_keys(self):
        """Animate FKSpine_M (alias FKSpine1_M) and FKChest_M: RX thirds, RZ fifths, RY thirds."""
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        times_thirds = [start, mid, end]
        times_fifths = [start, self.quarter, mid, self.three_quarter, end]

        def apply_joint(ctrl, p):
            if not ctrl:
                return
            # RX thirds (swing)
            rx_vals = self.pattern_thirds(p['swing_rx'])
            for t, v in zip(times_thirds, rx_vals):
                self.set_key(ctrl, 'rotateX', t, v)

            # RZ fifths (rock)
            rz_vals = self.pattern_fifths(p['rock_rz'])
            for t, v in zip(times_fifths, rz_vals):
                self.set_key(ctrl, 'rotateZ', t, v)

            # RY thirds (sway)
            ry_vals = self.pattern_thirds(p['sway_ry'])
            for t, v in zip(times_thirds, ry_vals):
                self.set_key(ctrl, 'rotateY', t, v)

        spine_ctrl = self.resolve_first_existing(self.spine_ctrl_candidates)
        chest_ctrl = self.chest_ctrl if cmds.objExists(self.chest_ctrl) else None

        apply_joint(spine_ctrl, self.spine_params)
        apply_joint(chest_ctrl, self.chest_params)

    
    def set_hip_keys(self):
        hip = self.hip_ctrl
        swing = self.hip_params['swing']
        sway = self.hip_params['sway']
        x_vals = [swing, -swing, swing]
        y_vals = [sway, -sway, sway]
        self.apply_keyframe_pattern((hip, 'rotateX'), x_vals)
        self.apply_keyframe_pattern((hip, 'rotateY'), y_vals)

    def set_feet_follow_keys(self):
        right = self.feet['right']
        left = self.feet['left']
        blend = self.feet_follow['moveFeetWithRoot']
        
        offset_x = self.feet_follow['offset_x']
        offset_y = self.feet_follow['offset_y']
        offset_z = self.feet_follow['offset_z']
        rotate_x = self.feet_follow['rotate_x']
    
        for t in [f[0] for f in self.frames_stride_halved] + [self.quarter, self.three_quarter]:
            # Get root values
            ry = cmds.getAttr(f"{self.root_ctrl}.translateY", time=t) if cmds.objExists(self.root_ctrl) else 0
            rz = cmds.getAttr(f"{self.root_ctrl}.translateZ", time=t) if cmds.objExists(self.root_ctrl) else 0
            rx = cmds.getAttr(f"{self.root_ctrl}.rotateX", time=t) if cmds.objExists(self.root_ctrl) else 0
    
            # Blend root values with 0
            y = ry * blend + offset_y
            z = rz * blend + offset_z
            r = rx * blend + rotate_x
    
            # Apply mirrored X offset
            self.set_key(right, 'translateX', t,  offset_x)
            self.set_key(left,  'translateX', t, -offset_x)
    
            self.set_key(right, 'translateY', t, y)
            self.set_key(left,  'translateY', t, y)
    
            self.set_key(right, 'translateZ', t, z)
            self.set_key(left,  'translateZ', t, z)
    
            self.set_key(right, 'rotateX', t, r)
            self.set_key(left,  'rotateX', t, r)

    def set_scapula_keys(self):
        times = [f[0] for f in self.frames_stride_halved]
        for side in ['left', 'right']:
            ctrl = self.scapula_ctrls[side]
            sign = 1 if side == 'left' else -1  # mirror values for right
    
            z_vals = [ sign * self.scapula_params['rotateZ'],
                      -sign * self.scapula_params['rotateZ'],
                       sign * self.scapula_params['rotateZ'] ]
    
            x_vals = [ self.scapula_params['rotateX'],
                      -self.scapula_params['rotateX'],
                       self.scapula_params['rotateX'] ]
    
            for t, z, x in zip(times, z_vals, x_vals):
                self.set_key(ctrl, 'rotateZ', t, z)
                self.set_key(ctrl, 'rotateX', t, x)

    def set_head_and_neck_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        times_thirds = [start, mid, end]
        times_fifths = [start, self.quarter, mid, self.three_quarter, end]

        def apply_joint(ctrl, p):
            # Rotations
            rx_vals = self.pattern_thirds(p['counter_rotateX'])
            ry_vals = self.pattern_thirds(p['counter_rotateY'])
            rz_vals = self.pattern_fifths(p['counter_rotateZ'])

            for t, v in zip(times_thirds, rx_vals):
                self.set_key(ctrl, 'rotateX', t, v)
            for t, v in zip(times_thirds, ry_vals):
                self.set_key(ctrl, 'rotateY', t, v)
            for t, v in zip(times_fifths, rz_vals):
                self.set_key(ctrl, 'rotateZ', t, v)

            # Translations
            tx_vals = self.pattern_fifths(p['bounce_tx'])   # Bounce X
            ty_vals = self.pattern_fifths(p['bob_ty'])      # Bob Y
            tz_vals = self.pattern_thirds(p['sway_tz'])     # Sway Z

            for t, v in zip(times_fifths, tx_vals):
                self.set_key(ctrl, 'translateX', t, v)
            for t, v in zip(times_fifths, ty_vals):
                self.set_key(ctrl, 'translateY', t, v)
            for t, v in zip(times_thirds, tz_vals):
                self.set_key(ctrl, 'translateZ', t, v)

        # Apply to neck and head separately
        if cmds.objExists(self.head_ctrls['neck']):
            apply_joint(self.head_ctrls['neck'], self.neck_params)
        if cmds.objExists(self.head_ctrls['head']):
            apply_joint(self.head_ctrls['head'], self.head_params)


    def set_head_counter_keys(self):
        times = [f[0] for f in self.frames_stride_halved]
        rx_vals = [ self.head_params['counter_rotateX'],
                   -self.head_params['counter_rotateX'],
                    self.head_params['counter_rotateX'] ]
        ry_vals = [ self.head_params['counter_rotateY'],
                   -self.head_params['counter_rotateY'],
                    self.head_params['counter_rotateY'] ]
    
        for ctrl in [self.head_ctrls['neck'], self.head_ctrls['head']]:
            for t, rx, ry in zip(times, rx_vals, ry_vals):
                self.set_key(ctrl, 'rotateX', t, rx)
                self.set_key(ctrl, 'rotateY', t, ry)



    def print_settings(self, *args):
        settings = {
            'stride': self.stride,
            'stride_width': self.stride_width,
            'stride_height': self.stride_height,
            'offsets': self.hand_offsets.copy(),
            'root': self.root_params.copy(),
            'hip': self.hip_params.copy(),
            'feet_follow': self.feet_follow.copy(),
            'scapula': self.scapula_params.copy(),
            'neck': getattr(self, 'neck_params', {}).copy() if hasattr(self, 'neck_params') else {},
            'head': self.head_params.copy(),
            'groundHeight': self.groundHeight,   # ← add this
            'spine': self.spine_params.copy(),
            'chest': self.chest_params.copy(),
        }

        print("// HandWalkCycleTool Settings:\n" + json.dumps(settings, indent=2))

    def prompt_and_apply_settings(self, *args):
        result = cmds.promptDialog(title="Apply Settings",
                                   message="Paste JSON settings string here:",
                                   button=['Apply', 'Cancel'],
                                   defaultButton='Apply',
                                   cancelButton='Cancel',
                                   dismissString='Cancel')
        if result != 'Apply':
            return
        try:
            text = cmds.promptDialog(query=True, text=True)
            settings = json.loads(text)
            self.apply_settings(settings)
            self.update_ui_fields()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    def apply_keyframe_pattern(self, obj_attr, values_per_frame):
        obj, attr = obj_attr
        for (t, *_), v in zip(self.frames_stride_halved, values_per_frame):
            self.set_key(obj, attr, t, v)

    def clamp_hands_ty_two_stage_ground(self):
        """
        Step 1: For every whole frame, if IKArm_[R/L].translateY < groundHeight,
                set a key at that frame with the current (negative/below-threshold) value.
        Step 2: Iterate all keys on IKArm_[R/L].translateY and clamp any value below groundHeight to groundHeight.
        """
        import math

        start = cmds.playbackOptions(q=True, min=True)
        end   = cmds.playbackOptions(q=True, max=True)
        s = int(math.floor(start))
        e = int(math.ceil(end))

        gh = float(self.groundHeight)
        attr = 'translateY'

        controls = [self.stride_limbs.get('right'), self.stride_limbs.get('left')]
        controls = [c for c in controls if c and cmds.objExists(c)]

        for ctrl in controls:
            if not cmds.attributeQuery(attr, node=ctrl, exists=True):
                continue

            # --- Step 1: sample every whole frame; key only where value is below groundHeight ---
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

            # --- Step 2: get all keys and clamp any below groundHeight to groundHeight ---
            key_times = cmds.keyframe(ctrl, at=attr, q=True, timeChange=True)
            if not key_times:
                continue

            # De-dup times while preserving float precision
            seen = set()
            ordered_times = []
            for kt in key_times:
                if kt not in seen:
                    seen.add(kt)
                    ordered_times.append(kt)

            for kt in ordered_times:
                try:
                    v = cmds.getAttr(f"{ctrl}.{attr}", time=kt)
                except Exception:
                    continue
                if v is not None and v < gh:
                    try:
                        cmds.setKeyframe(ctrl, attribute=attr, t=kt, v=gh)
                    except Exception:
                        pass



    def apply_settings(self, settings):
        self.stride = settings.get('stride', self.stride)
        self.stride_width = settings.get('stride_width', self.stride_width)
        self.stride_height = settings.get('stride_height', self.stride_height)
        self.hand_offsets.update(settings.get('offsets', self.hand_offsets))
        self.feet_follow.update(settings.get('feet_follow', self.feet_follow))
        self.scapula_params.update(settings.get('scapula', self.scapula_params))
        self.neck_params.update(settings.get('neck', self.neck_params))
        self.head_params.update(settings.get('head', self.head_params))
        if 'head' in settings and 'neck' not in settings:
            # mirror old single-head config into neck as a starting point
            self.neck_params.update({k: settings['head'].get(k, self.neck_params[k]) for k in self.neck_params})
        self.groundHeight = settings.get('groundHeight', self.groundHeight)
        self.spine_params.update(settings.get('spine', self.spine_params))
        self.chest_params.update(settings.get('chest', self.chest_params))



    def update_ui_fields(self):
        cmds.floatField(self.stride_field, e=True, value=self.stride)
        cmds.floatField(self.stride_width_field, e=True, value=self.stride_width)
        cmds.floatField(self.stride_height_field, e=True, value=self.stride_height)
        cmds.floatField(self.offset_x_field, e=True, value=self.hand_offsets['offset_x'])
        cmds.floatField(self.offset_y_field, e=True, value=self.hand_offsets['offset_y'])
        cmds.floatField(self.offset_z_field, e=True, value=self.hand_offsets['offset_z'])
        cmds.floatField(self.rotate_y_field, e=True, value=self.hand_offsets['rotation_y'])
        cmds.floatField(self.root_offset_y_field, e=True, value=self.root_params['offset_y'])
        cmds.floatField(self.root_offset_z_field, e=True, value=self.root_params['offset_z'])
        cmds.floatField(self.root_offset_rx_field, e=True, value=self.root_params['offset_rx'])
        cmds.floatField(self.root_bounce_field, e=True, value=self.root_params['bounce'])
        cmds.floatField(self.root_sway_field, e=True, value=self.root_params['sway'])
        cmds.floatField(self.root_rock_field, e=True, value=self.root_params['rock'])
        
        cmds.floatSlider(self.move_feet_slider, e=True, value=self.feet_follow['moveFeetWithRoot'])
        cmds.floatField(self.feet_offset_x_field, e=True, value=self.feet_follow['offset_x'])
        cmds.floatField(self.feet_offset_y_field, e=True, value=self.feet_follow['offset_y'])
        cmds.floatField(self.feet_offset_z_field, e=True, value=self.feet_follow['offset_z'])
        cmds.floatField(self.feet_rotate_x_field, e=True, value=self.feet_follow['rotate_x'])
        
        cmds.floatField(self.scapula_z_field, e=True, value=self.scapula_params['rotateZ'])
        cmds.floatField(self.scapula_x_field, e=True, value=self.scapula_params['rotateX'])
        # Neck UI
        cmds.floatField(self.neck_rx_field, e=True, value=self.neck_params['counter_rotateX'])
        cmds.floatField(self.neck_ry_field, e=True, value=self.neck_params['counter_rotateY'])
        cmds.floatField(self.neck_rz_field, e=True, value=self.neck_params['counter_rotateZ'])
        cmds.floatField(self.neck_tx_field, e=True, value=self.neck_params['bounce_tx'])
        cmds.floatField(self.neck_ty_field, e=True, value=self.neck_params['bob_ty'])
        cmds.floatField(self.neck_tz_field, e=True, value=self.neck_params['sway_tz'])

        # Head UI
        cmds.floatField(self.head_rx_field, e=True, value=self.head_params['counter_rotateX'])
        cmds.floatField(self.head_ry_field, e=True, value=self.head_params['counter_rotateY'])
        cmds.floatField(self.head_rz_field, e=True, value=self.head_params['counter_rotateZ'])
        cmds.floatField(self.head_tx_field, e=True, value=self.head_params['bounce_tx'])
        cmds.floatField(self.head_ty_field, e=True, value=self.head_params['bob_ty'])
        cmds.floatField(self.head_tz_field, e=True, value=self.head_params['sway_tz'])
        
        cmds.floatField(self.hip_swing_field, e=True, value=self.hip_params['swing'])
        cmds.floatField(self.hip_sway_field, e=True, value=self.hip_params['sway'])

        if hasattr(self, 'ground_height_field'):
            cmds.floatField(self.ground_height_field, e=True, value=self.groundHeight)
        if hasattr(self, 'spine_rx_field'):
            cmds.floatField(self.spine_rx_field, e=True, value=self.spine_params['swing_rx'])
            cmds.floatField(self.spine_rz_field, e=True, value=self.spine_params['rock_rz'])
            cmds.floatField(self.spine_ry_field, e=True, value=self.spine_params['sway_ry'])

        if hasattr(self, 'chest_rx_field'):
            cmds.floatField(self.chest_rx_field, e=True, value=self.chest_params['swing_rx'])
            cmds.floatField(self.chest_rz_field, e=True, value=self.chest_params['rock_rz'])
            cmds.floatField(self.chest_ry_field, e=True, value=self.chest_params['sway_ry'])



HandWalkCycleTool().show()
