import maya.cmds as cmds
import json

class WalkCycleTool:
    def __init__(self):
        self.window = "WalkCycleWindow"
        self.stride = 10.0
        self.stride_width = 2.0
        self.stride_height = 4.0
        self.swing_extend = 10.0
        self.hip_sway_lr = 5.0
        self.root_bounce = 1.5
        self.root_sway = 2.0
        self.root_rock = 1.0
        self.foot_raise = 10.0  # new default value
        self.root_bounce_offset = 0.0  # translateY

        self.root_twist = 0.0  # 🔹 NEW — rotateZ on thirds


        self.root_bounce_offset = 0.0  # 🔹 NEW
        self.root_side_sway = 0.0      # 🔹 NEW
        
        self.root_backforth = 0.0  # 🔹 NEW — translateZ on fifths
        self.root_leftright = 0.0  # 🔹 NEW — translateX on thirds (replaces/renames root_side_sway)

        self.leg_stretch_L = 0.0
        self.leg_stretch_R = 0.0



        self.arm_params = {
            'shoulder_down_y': -30.0,
            'scapula_down': -15.0,  # 🔹 NEW
            'scapula_z': 8.0,
            'shoulder_z': 20.0,
            'shoulder_x': 0.0,
            'elbow_z': 12.0,
            'wrist_z': 6.0,
        }

        self.root_rock_offset = 0.0  # 🔹 NEW
        
        self.upper_body_params = {
            'spine1': {'name': 'FKSpine1_M', 'rx': 5.0, 'ry': 2.0, 'rz': 1.5, 'rz_offset': 0.0},
            'chest':  {'name': 'FKChest_M',  'rx': 7.0, 'ry': 3.0, 'rz': 2.0, 'rz_offset': 0.0},
            'neck':   {'name': 'FKNeck_M',   'rx': 4.0, 'ry': 2.0, 'rz': 1.0, 'rz_offset': 0.0},
            'head':   {'name': 'FKHead_M',   'rx': 3.0, 'ry': 1.5, 'rz': 1.5, 'rz_offset': 0.0},
        }



        self.frames_stride_halved = []
        self.limbs = {
            'right_leg': "IKLeg_R",
            'left_leg': "IKLeg_L",
            'hip': "HipSwinger_M",
            'root': "RootX_M"
        }

        self.arm_ctrls = {
            'scapula': "FKScapula_R",
            'shoulder': "FKShoulder_R",
            'elbow': "FKElbow_R",
            'wrist': "FKWrist_R"
        }

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
    
        self.window = cmds.window(self.window, title="Walk Cycle Tool", widthHeight=(800, 600))
        cmds.scrollLayout(horizontalScrollBarThickness=0)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    
        # --- Global Settings ---
        cmds.frameLayout(label="Global Settings", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
    
        cmds.text(label="Stride Length")
        self.stride_field = cmds.floatField(value=self.stride)
    
        cmds.text(label="Stride Width (X)")
        self.stride_width_field = cmds.floatField(value=self.stride_width)
    
        cmds.text(label="Stride Height (Y)")
        self.stride_height_field = cmds.floatField(value=self.stride_height)
    
        cmds.text(label="Hip Swing (rotateX)")
        self.swing_field = cmds.floatField(value=self.swing_extend)
    
        cmds.text(label="Hip Sway (rotateY)")
        self.hip_sway_field = cmds.floatField(value=self.hip_sway_lr)
        
        cmds.text(label="Foot Raise (rotateX)")
        self.foot_raise_field = cmds.floatField(value=self.foot_raise)
        
        cmds.rowLayout(numberOfColumns=2)
        cmds.text(label="Bounce Offset (Y):")
        self.root_bounce_offset_field = cmds.floatField(value=self.root_bounce_offset)
        cmds.setParent('..')
        

    
        cmds.setParent('..')
        cmds.setParent('..')
    
        # --- Root Controls ---
        cmds.frameLayout(label="Root Controls (RootX_M)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
    
        cmds.text(label="Bounce (translateY)")
        self.root_bounce_field = cmds.floatField(value=self.root_bounce)
    
        cmds.text(label="Side Sway (rotateY)")
        self.root_sway_field = cmds.floatField(value=self.root_sway)
    
        cmds.text(label="Rock (rotateX)")
        self.root_rock_field = cmds.floatField(value=self.root_rock)
        
        cmds.text(label="Rock Offset (rotateX)")
        self.root_rock_offset_field = cmds.floatField(value=self.root_rock_offset)
        
        cmds.text(label="Twist (rotateZ)")
        self.root_twist_field = cmds.floatField(value=self.root_twist)

        cmds.text(label="LeftRight (translateX on thirds):")
        self.root_leftright_field = cmds.floatField(value=self.root_leftright)
        
        cmds.text(label="BackForth (translateZ on fifths):")
        self.root_backforth_field = cmds.floatField(value=self.root_backforth)

    
        cmds.setParent('..')
        cmds.setParent('..')

        # --- Leg Stretch (IKLeg_*.Stretchy) ---
        cmds.frameLayout(label="Leg Stretch (IKLeg_*.Stretchy)", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 220), (2, 400)])
        
        cmds.text(label="IKLeg_L.Stretchy (0–10)")
        self.leg_stretch_L_slider = cmds.floatSliderGrp(label="", field=True, min=0.0, max=10.0, value=self.leg_stretch_L)
        
        cmds.text(label="IKLeg_R.Stretchy (0–10)")
        self.leg_stretch_R_slider = cmds.floatSliderGrp(label="", field=True, min=0.0, max=10.0, value=self.leg_stretch_R)
        
        cmds.setParent('..')
        cmds.setParent('..')

        # --- Spine / Neck / Head ---
        cmds.frameLayout(label="Spine / Neck / Head", collapsable=True, marginWidth=10, marginHeight=5)
        for key in self.upper_body_params:
            cmds.text(label=key.capitalize(), align='left')
            cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[
                (1, 60), (2, 90),
                (3, 60), (4, 90),
                (5, 60), (6, 90)
            ])
            
            cmds.text(label="Rotate X:")
            self.upper_body_params[key]['rx_field'] = cmds.floatField(value=self.upper_body_params[key]['rx'])
            
            cmds.text(label="Rotate Y:")
            self.upper_body_params[key]['ry_field'] = cmds.floatField(value=self.upper_body_params[key]['ry'])
            
            cmds.text(label="Rotate Z:")
            self.upper_body_params[key]['rz_field'] = cmds.floatField(value=self.upper_body_params[key]['rz'])  # 🔹 NEW
            
            cmds.text(label="Offset Z:")
            self.upper_body_params[key]['rz_offset_field'] = cmds.floatField(value=self.upper_body_params[key]['rz_offset'])


            cmds.setParent('..')
        cmds.setParent('..')
    
        # --- Right Arm Swing ---
        cmds.frameLayout(label="Right Arm Swing", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)])
    
        cmds.text(label="Shoulder Down (rotateY):")
        self.arm_params['shoulder_down_y_field'] = cmds.floatField(value=self.arm_params['shoulder_down_y'])
        
        cmds.text(label="Scapula Down (rotateY):")
        self.arm_params['scapula_down_field'] = cmds.floatField(value=self.arm_params['scapula_down'])

        
        cmds.text(label="Shoulder X (rotateX):")
        self.arm_params['shoulder_x_field'] = cmds.floatField(value=self.arm_params['shoulder_x'])

    
        for label, key in [('Scapula Z', 'scapula_z'), ('Shoulder Z', 'shoulder_z'),
                           ('Elbow Z', 'elbow_z'), ('Wrist Z', 'wrist_z')]:
            cmds.text(label=label)
            self.arm_params[key + '_field'] = cmds.floatField(value=self.arm_params[key])
    
        cmds.setParent('..')
        cmds.setParent('..')
    
        # --- Action Buttons ---
        cmds.separator(height=10, style='in')
        cmds.button(label="Create Walk Cycle", height=40, command=self.create_walk_cycle)
        cmds.separator(height=10, style='in')
    
        # --- Presets ---
        cmds.frameLayout(label="Presets", collapsable=True, marginWidth=10, marginHeight=5)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(300, 300), columnAlign=(1, 'left'))
    
        cmds.button(label="Print Current Settings to Console", command=self.print_settings)
        cmds.button(label="Apply Settings From String", command=self.prompt_and_apply_settings)
    
        cmds.setParent('..')
        cmds.setParent('..')
    
        cmds.showWindow(self.window)
        
    def resolve_node_case_insensitive(self, name):
        """
        Tries to find a scene node that matches the given name (case-insensitive).
        Returns the actual name if found, otherwise returns None.
        """
        all_nodes = cmds.ls(type="transform") + cmds.ls(type="joint") + cmds.ls(type="locator")
        for node in all_nodes:
            if node.lower() == name.lower():
                return node
        return None



    def clear_keys(self):
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
    
        all_controls = list(self.limbs.values()) + [data['name'] for data in self.upper_body_params.values()]
        all_controls += list(self.arm_ctrls.values())
        all_controls += [ctrl.replace('_R', '_L') for ctrl in self.arm_ctrls.values()]
    
        for ctrl in all_controls:
            for attr in attrs:
                if cmds.objExists(ctrl) and cmds.attributeQuery(attr, node=ctrl, exists=True):
                    cmds.cutKey(ctrl, at=attr, time=(start, end))


    def create_walk_cycle(self, *args):
        # Load main params
        self.stride = cmds.floatField(self.stride_field, query=True, value=True)
        self.stride_width = cmds.floatField(self.stride_width_field, query=True, value=True)
        self.stride_height = cmds.floatField(self.stride_height_field, query=True, value=True)
        self.swing_extend = cmds.floatField(self.swing_field, query=True, value=True)
        self.hip_sway_lr = cmds.floatField(self.hip_sway_field, query=True, value=True)
        self.root_bounce = cmds.floatField(self.root_bounce_field, query=True, value=True)
        self.root_sway = cmds.floatField(self.root_sway_field, query=True, value=True)
        self.root_rock = cmds.floatField(self.root_rock_field, query=True, value=True)
        self.root_rock_offset = cmds.floatField(self.root_rock_offset_field, query=True, value=True)
        self.foot_raise = cmds.floatField(self.foot_raise_field, query=True, value=True)
        self.root_bounce_offset = cmds.floatField(self.root_bounce_offset_field, query=True, value=True)
        self.root_twist = cmds.floatField(self.root_twist_field, query=True, value=True)
        self.root_backforth = cmds.floatField(self.root_backforth_field, query=True, value=True)
        self.root_leftright = cmds.floatField(self.root_leftright_field, query=True, value=True)




        for key in self.upper_body_params:
            self.upper_body_params[key]['rx'] = cmds.floatField(self.upper_body_params[key]['rx_field'], query=True, value=True)
            self.upper_body_params[key]['ry'] = cmds.floatField(self.upper_body_params[key]['ry_field'], query=True, value=True)
            self.upper_body_params[key]['rz'] = cmds.floatField(self.upper_body_params[key]['rz_field'], query=True, value=True)
            self.upper_body_params[key]['rz_offset'] = cmds.floatField(self.upper_body_params[key]['rz_offset_field'], query=True, value=True)

        self.leg_stretch_L = cmds.floatSliderGrp(self.leg_stretch_L_slider, query=True, value=True)
        self.leg_stretch_R = cmds.floatSliderGrp(self.leg_stretch_R_slider, query=True, value=True)

        for key in ['shoulder_down_y', 'scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z']:
            self.arm_params[key] = cmds.floatField(self.arm_params[key + '_field'], query=True, value=True)
            
        self.arm_params['scapula_down'] = cmds.floatField(self.arm_params['scapula_down_field'], query=True, value=True)
        
        self.arm_params['shoulder_x'] = cmds.floatField(self.arm_params['shoulder_x_field'], query=True, value=True)

        original_time = cmds.currentTime(query=True)
        self.clear_keys()
        self.compute_frame_data()
        
        self.set_leg_stretch_keys()
        self.set_feet_keys()
        self.set_foot_raise_keys()
        self.set_hip_swinger_keys()
        self.set_spine_keys()
        self.set_root_keys()
        self.set_right_arm_keys()
        self.set_left_arm_keys()
        cmds.currentTime(original_time, edit=True)

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
        cmds.setAttr(f"{obj}.{attr}", value)
        cmds.setKeyframe(obj, attribute=attr, t=time)

    def apply_keyframe_pattern(self, obj_attr, values_per_frame):
        obj, attr = obj_attr
        for (t, *_), v in zip(self.frames_stride_halved, values_per_frame):
            self.set_key(obj, attr, t, v)

    
    def set_leg_stretch_keys(self):
        """
        Uses existing IKLeg_*.stretchy (0..10). 
        If the attribute doesn't exist, skip and warn. Sets static start/end keys.
        """
        leg_l = self.limbs['left_leg']
        leg_r = self.limbs['right_leg']
        start = cmds.playbackOptions(q=True, min=True)
        end   = cmds.playbackOptions(q=True, max=True)
    
        for node, val in [(leg_l, self.leg_stretch_L), (leg_r, self.leg_stretch_R)]:
            if not cmds.objExists(node):
                cmds.warning("Node not found: {}".format(node))
                continue
            if not cmds.attributeQuery('stretchy', node=node, exists=True):
                cmds.warning("Attribute 'stretchy' not found on {} — skipping".format(node))
                continue
    
            # Clear old keys on 'stretchy' in the current range
            try:
                cmds.cutKey(node, at='stretchy', time=(start, end))
            except Exception:
                pass
    
            # Static value + start/end keys
            cmds.setAttr("{}.stretchy".format(node), val)
            self.set_key(node, 'stretchy', start, val)
            self.set_key(node, 'stretchy', end,   val)

    def set_feet_keys(self):
        r = self.limbs['right_leg']
        l = self.limbs['left_leg']
        rz_values = [f[1] for f in self.frames_stride_halved]
        lz_values = [f[2] for f in self.frames_stride_halved]
        x_vals_r = [self.stride_width] * 3
        x_vals_l = [-self.stride_width] * 3

        self.apply_keyframe_pattern((r, 'translateZ'), rz_values)
        self.apply_keyframe_pattern((l, 'translateZ'), lz_values)
        self.apply_keyframe_pattern((r, 'translateX'), x_vals_r)
        self.apply_keyframe_pattern((l, 'translateX'), x_vals_l)

        start, mid, end = [f[0] for f in self.frames_stride_halved]
        self.set_key(l, 'translateY', self.quarter, self.stride_height)
        self.set_key(r, 'translateY', self.three_quarter, self.stride_height)
        for t in [start, mid, end]:
            self.set_key(l, 'translateY', t, 0)
            self.set_key(r, 'translateY', t, 0)

    def set_hip_swinger_keys(self):
        hip = self.limbs['hip']
        x_vals = [self.swing_extend, -self.swing_extend, self.swing_extend]
        y_vals = [self.hip_sway_lr, -self.hip_sway_lr, self.hip_sway_lr]
        self.apply_keyframe_pattern((hip, 'rotateX'), x_vals)
        self.apply_keyframe_pattern((hip, 'rotateY'), y_vals)

    def set_root_keys(self):
        root = self.limbs['root']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        quarter = self.quarter
        three_quarter = self.three_quarter
    
        # Bounce with offset (translateY)
        bounce_vals = [self.root_bounce + self.root_bounce_offset,
                       -self.root_bounce + self.root_bounce_offset,
                        self.root_bounce + self.root_bounce_offset,
                       -self.root_bounce + self.root_bounce_offset,
                        self.root_bounce + self.root_bounce_offset]
        for t, v in zip([start, quarter, mid, three_quarter, end], bounce_vals):
            self.set_key(root, 'translateY', t, v)
    
        # LeftRight sway on thirds (translateX)
        leftright_vals = [self.root_leftright, 0, -self.root_leftright, 0, self.root_leftright]
        for t, v in zip([start, quarter, mid, three_quarter, end], leftright_vals):
            self.set_key(root, 'translateX', t, v)
            
        # BackForth on fifths (translateZ)
        backforth_vals = [self.root_backforth, -self.root_backforth, self.root_backforth, -self.root_backforth, self.root_backforth]
        for t, v in zip([start, quarter, mid, three_quarter, end], backforth_vals):
            self.set_key(root, 'translateZ', t, v)

    
        # Rock (rotateX) with offset
        rx_vals = [self.root_rock + self.root_rock_offset, 
                   -self.root_rock + self.root_rock_offset,
                    self.root_rock + self.root_rock_offset,
                   -self.root_rock + self.root_rock_offset,
                    self.root_rock + self.root_rock_offset]
        for t, v in zip([start, quarter, mid, three_quarter, end], rx_vals):
            self.set_key(root, 'rotateX', t, v)
    
        # Sway (rotateY) — still just on thirds
        self.set_key(root, 'rotateY', start, self.root_sway)
        self.set_key(root, 'rotateY', mid, -self.root_sway)
        self.set_key(root, 'rotateY', end, self.root_sway)
        # Twist (rotateZ) on thirds
        rz_vals = [self.root_twist, -self.root_twist, self.root_twist]
        self.apply_keyframe_pattern((root, 'rotateZ'), rz_vals)


    def set_foot_raise_keys(self):
        leg_l = self.limbs['left_leg']
        leg_r = self.limbs['right_leg']
        start, mid, end = [f[0] for f in self.frames_stride_halved]
    
        # 5ths
        quarter = self.quarter
        three_quarter = self.three_quarter
        fifth1 = start
        fifth2 = quarter
        fifth3 = mid
        fifth4 = three_quarter
        fifth5 = end
    
        # IKLeg_L keys
        self.set_key(leg_l, 'rotateX', fifth1, 0)
        self.set_key(leg_l, 'rotateX', fifth2, 0)
        self.set_key(leg_l, 'rotateX', (fifth2 + fifth3) / 2.0, self.foot_raise)
        self.set_key(leg_l, 'rotateX', fifth3, 0)
        self.set_key(leg_l, 'rotateX', fifth4, 0)
        self.set_key(leg_l, 'rotateX', fifth5, 0)
    
        # IKLeg_R keys
        self.set_key(leg_r, 'rotateX', fifth1, 0)
        self.set_key(leg_r, 'rotateX', fifth2, 0)
        self.set_key(leg_r, 'rotateX', fifth3, 0)
        self.set_key(leg_r, 'rotateX', fifth4, 0)
        self.set_key(leg_r, 'rotateX', (fifth4 + fifth5) / 2.0, self.foot_raise)
        self.set_key(leg_r, 'rotateX', fifth5, 0)


    def set_spine_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        quarter = self.quarter
        three_quarter = self.three_quarter
        fifths = [start, quarter, mid, three_quarter, end]
    
        for key, data in self.upper_body_params.items():
            ctrl = data['name']
    
            # X and Y remain on thirds
            rx_vals = [data['rx'], -data['rx'], data['rx']]
            ry_vals = [data['ry'], -data['ry'], data['ry']]
            self.apply_keyframe_pattern((ctrl, 'rotateX'), rx_vals)
            self.apply_keyframe_pattern((ctrl, 'rotateY'), ry_vals)
    
            # Z (Rock) is now on fifths
            rz = data['rz']
            offset = data.get('rz_offset', 0)
            rz_vals = [ rz + offset, -rz + offset,  rz + offset, -rz + offset,  rz + offset ]
            for t, v in zip(fifths, rz_vals):
                self.set_key(ctrl, 'rotateZ', t, v)



    def set_right_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
    
        # static Y downs
        static_ry = self.arm_params['shoulder_down_y']
        cmds.setAttr(f"{self.arm_ctrls['shoulder']}.rotateY", static_ry)
        self.set_key(self.arm_ctrls['shoulder'], 'rotateY', start, static_ry)
        self.set_key(self.arm_ctrls['shoulder'], 'rotateY', end,   static_ry)
    
        scapula_ctrl = self.arm_ctrls['scapula']
        scapula_down = self.arm_params['scapula_down']
        cmds.setAttr(f"{scapula_ctrl}.rotateY", scapula_down)
        self.set_key(scapula_ctrl, 'rotateY', start, scapula_down)
        self.set_key(scapula_ctrl, 'rotateY', end,   scapula_down)
    
        # Shoulder X (thirds)
        x_vals = [self.arm_params['shoulder_x'], -self.arm_params['shoulder_x'], self.arm_params['shoulder_x']]
        self.apply_keyframe_pattern((self.arm_ctrls['shoulder'], 'rotateX'), x_vals)
    
        # Z swings
        for key, ctrl in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                             ['scapula',   'shoulder',   'elbow',   'wrist']):
            val = self.arm_params[key]
            if key == 'elbow_z':
                # right elbow peaks at mid; allow negatives
                values = [0, val, 0]
            else:
                values = [val, -val, val]
            self.apply_keyframe_pattern((self.arm_ctrls[ctrl], 'rotateZ'), values)


            
    # append this new function inside your WalkCycleTool class
    
    def set_left_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
    
        # static Y downs
        static_ry = self.arm_params['shoulder_down_y']
        l_shoulder = self.arm_ctrls['shoulder'].replace('_R', '_L')
        cmds.setAttr(f"{l_shoulder}.rotateY", static_ry)
        self.set_key(l_shoulder, 'rotateY', start, static_ry)
        self.set_key(l_shoulder, 'rotateY', end,   static_ry)
    
        l_scapula = self.arm_ctrls['scapula'].replace('_R', '_L')
        scapula_down = self.arm_params['scapula_down']
        cmds.setAttr(f"{l_scapula}.rotateY", scapula_down)
        self.set_key(l_scapula, 'rotateY', start, scapula_down)
        self.set_key(l_scapula, 'rotateY', end,   scapula_down)
    
        # Shoulder X (mirrored on thirds)
        x_vals = [-self.arm_params['shoulder_x'], self.arm_params['shoulder_x'], -self.arm_params['shoulder_x']]
        self.apply_keyframe_pattern((l_shoulder, 'rotateX'), x_vals)
    
        # Z swings
        for key, ctrl in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                             ['scapula',   'shoulder',   'elbow',   'wrist']):
            val = self.arm_params[key]
            l_ctrl = self.arm_ctrls[ctrl].replace('_R', '_L')
            if key == 'elbow_z':
                # left elbow peaks at start/end; allow negatives
                values = [val, 0, val]
            else:
                values = [-val, val, -val]
            self.apply_keyframe_pattern((l_ctrl, 'rotateZ'), values)



    def print_settings(self, *args):
        settings = {
            'stride': self.stride,
            'stride_width': self.stride_width,
            'stride_height': self.stride_height,
            'swing_extend': self.swing_extend,
            'hip_sway_lr': self.hip_sway_lr,
            'root_bounce': self.root_bounce,
            'root_sway': self.root_sway,
            'root_rock': self.root_rock,
            'foot_raise': self.foot_raise,
            'root_bounce_offset': self.root_bounce_offset,
            'root_twist': self.root_twist,
            'root_backforth': self.root_backforth,
            'root_leftright': self.root_leftright,
            'leg_stretch_L': self.leg_stretch_L,
            'leg_stretch_R': self.leg_stretch_R,
            'upper_body': {
                k: {
                    'rx': v['rx'],
                    'ry': v['ry'],
                    'rz': v['rz'],
                    'rz_offset': v.get('rz_offset', 0)
                } for k, v in self.upper_body_params.items()
            },
            'arms': {k: self.arm_params[k] for k in self.arm_params if not k.endswith('_field')}
        }
        print("// WalkCycleTool Settings:\n" + json.dumps(settings, indent=2))

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
            text = cmds.promptDialog(query=True, text=True).strip()
            if not text:
                raise ValueError("No input provided.")
            settings = json.loads(text)
            self.apply_settings(settings)
            self.update_ui_fields_from_settings()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))


    def apply_settings(self, settings):
        self.stride = settings.get('stride', 0.0)
        self.stride_width = settings.get('stride_width', 0.0)
        self.stride_height = settings.get('stride_height', 0.0)
        self.swing_extend = settings.get('swing_extend', 0.0)
        self.hip_sway_lr = settings.get('hip_sway_lr', 0.0)
        self.root_bounce = settings.get('root_bounce', 0.0)
        self.root_sway = settings.get('root_sway', 0.0)
        self.root_rock = settings.get('root_rock', 0.0)
        self.root_rock_offset = settings.get('root_rock_offset', 0.0)
        self.foot_raise = settings.get('foot_raise', 0.0)
        self.root_bounce_offset = settings.get('root_bounce_offset', 0.0)
        self.root_twist = settings.get('root_twist', 0.0)
        self.leg_stretch_L = settings.get('leg_stretch_L', 0.0)
        self.leg_stretch_R = settings.get('leg_stretch_R', 0.0)

        self.root_backforth = settings.get('root_backforth', 0.0)
        self.root_leftright = settings.get('root_leftright', 0.0)

    
        for key, vals in settings.get('upper_body', {}).items():
            if key in self.upper_body_params:
                self.upper_body_params[key]['rx'] = vals.get('rx', 0.0)
                self.upper_body_params[key]['ry'] = vals.get('ry', 0.0)
                self.upper_body_params[key]['rz'] = vals.get('rz', 0.0)
                self.upper_body_params[key]['rz_offset'] = vals.get('rz_offset', 0.0)
    
        arm_defaults = ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']
        for k in arm_defaults:
            if 'arms' in settings:
                self.arm_params[k] = settings['arms'].get(k, 0.0)
            else:
                self.arm_params[k] = 0.0


    def update_ui_fields_from_settings(self):
        cmds.floatField(self.stride_field, e=True, value=self.stride)
        cmds.floatField(self.stride_width_field, e=True, value=self.stride_width)
        cmds.floatField(self.stride_height_field, e=True, value=self.stride_height)
        cmds.floatField(self.swing_field, e=True, value=self.swing_extend)
        cmds.floatField(self.hip_sway_field, e=True, value=self.hip_sway_lr)
        cmds.floatField(self.root_bounce_field, e=True, value=self.root_bounce)
        cmds.floatField(self.root_sway_field, e=True, value=self.root_sway)
        cmds.floatField(self.root_rock_field, e=True, value=self.root_rock)
        cmds.floatField(self.root_rock_offset_field, e=True, value=self.root_rock_offset)
        cmds.floatField(self.foot_raise_field, e=True, value=self.foot_raise)
        cmds.floatField(self.root_bounce_offset_field, e=True, value=self.root_bounce_offset)
        cmds.floatField(self.root_twist_field, e=True, value=self.root_twist)
        cmds.floatField(self.root_backforth_field, e=True, value=self.root_backforth)
        cmds.floatField(self.root_leftright_field, e=True, value=self.root_leftright)

        cmds.floatSliderGrp(self.leg_stretch_L_slider, e=True, value=self.leg_stretch_L)
        cmds.floatSliderGrp(self.leg_stretch_R_slider, e=True, value=self.leg_stretch_R)

    
        for key in self.upper_body_params:
            cmds.floatField(self.upper_body_params[key]['rx_field'], e=True, value=self.upper_body_params[key]['rx'])
            cmds.floatField(self.upper_body_params[key]['ry_field'], e=True, value=self.upper_body_params[key]['ry'])
            cmds.floatField(self.upper_body_params[key]['rz_field'], e=True, value=self.upper_body_params[key]['rz'])  # 🔹 NEW
            cmds.floatField(self.upper_body_params[key]['rz_offset_field'], e=True, value=self.upper_body_params[key]['rz_offset'])
    
        for key in ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']:
            field_key = key + '_field'
            if field_key in self.arm_params:
                cmds.floatField(self.arm_params[field_key], e=True, value=self.arm_params[key])



# ?? To run:
WalkCycleTool().show()
