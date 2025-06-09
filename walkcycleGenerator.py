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

        self.arm_params = {
            'shoulder_down_y': -30.0,
            'scapula_down': -15.0,  # ?? NEW
            'scapula_z': 8.0,
            'shoulder_z': 20.0,
            'shoulder_x': 0.0,
            'elbow_z': 12.0,
            'wrist_z': 6.0,
        }

        self.upper_body_params = {
            'spine1': {'name': 'FKSpine1_M', 'rx': 5.0, 'ry': 2.0, 'rz': 1.5},  # ?? NEW
            'chest':  {'name': 'FKChest_M',  'rx': 7.0, 'ry': 3.0, 'rz': 2.0},
            'neck':   {'name': 'FKNeck_M',   'rx': 4.0, 'ry': 2.0, 'rz': 1.0},
            'head':   {'name': 'FKHead_M',   'rx': 3.0, 'ry': 1.5, 'rz': 1.5},
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
            self.upper_body_params[key]['rz_field'] = cmds.floatField(value=self.upper_body_params[key]['rz'])  # ?? NEW

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
        Resolves a node name, supporting case-insensitive search and name aliasing.
        """
        aliases = {
            'fkscapula_r': 'fkscapula1_r',
            'fkscapula_l': 'fkscapula1_l',
        }
    
        name_lower = name.lower()
    
        # Try alias lookup first
        if name_lower in aliases:
            alias_target = aliases[name_lower]
        else:
            alias_target = name_lower
    
        all_nodes = cmds.ls(type="transform") + cmds.ls(type="joint") + cmds.ls(type="locator")
    
        # First try exact case-insensitive match of alias
        for node in all_nodes:
            if node.lower() == alias_target:
                return node
    
        # Then try original name (maybe it's valid)
        for node in all_nodes:
            if node.lower() == name_lower:
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
            resolved = self.resolve_node_case_insensitive(ctrl)
            if not resolved:
                continue
            for attr in attrs:
                if cmds.attributeQuery(attr, node=resolved, exists=True):
                    cmds.cutKey(resolved, at=attr, time=(start, end))



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

        for key in self.upper_body_params:
            self.upper_body_params[key]['rx'] = cmds.floatField(self.upper_body_params[key]['rx_field'], query=True, value=True)
            self.upper_body_params[key]['ry'] = cmds.floatField(self.upper_body_params[key]['ry_field'], query=True, value=True)
            self.upper_body_params[key]['rz'] = cmds.floatField(self.upper_body_params[key]['rz_field'], query=True, value=True)


        for key in ['shoulder_down_y', 'scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z']:
            self.arm_params[key] = cmds.floatField(self.arm_params[key + '_field'], query=True, value=True)
            
        self.arm_params['scapula_down'] = cmds.floatField(self.arm_params['scapula_down_field'], query=True, value=True)
        
        self.arm_params['shoulder_x'] = cmds.floatField(self.arm_params['shoulder_x_field'], query=True, value=True)

        original_time = cmds.currentTime(query=True)
        self.clear_keys()
        self.compute_frame_data()
        self.set_feet_keys()
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
        if not cmds.objExists(obj):
            resolved = self.resolve_node_case_insensitive(obj)
            if resolved:
                obj = resolved
            else:
                print(f"?? Skipping key: {obj}.{attr} (not found)")
                return
    
        if not cmds.attributeQuery(attr, node=obj, exists=True):
            print(f"?? Skipping key: {obj}.{attr} (attr not found)")
            return
    
        cmds.currentTime(time, edit=True)
        cmds.setAttr(f"{obj}.{attr}", value)
        cmds.setKeyframe(obj, attribute=attr, t=time)


    def apply_keyframe_pattern(self, obj_attr, values_per_frame):
        obj, attr = obj_attr
        for (t, *_), v in zip(self.frames_stride_halved, values_per_frame):
            self.set_key(obj, attr, t, v)

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

        # Bounce and rock: 5 keys
        for attr, up, down in [('translateY', self.root_bounce, -self.root_bounce),
                               ('rotateX', self.root_rock, -self.root_rock)]:
            self.set_key(root, attr, start, up)
            self.set_key(root, attr, self.quarter, down)
            self.set_key(root, attr, mid, up)
            self.set_key(root, attr, self.three_quarter, down)
            self.set_key(root, attr, end, up)
        
        # Sway: only 3 keys
        self.set_key(root, 'rotateY', start, self.root_sway)
        self.set_key(root, 'rotateY', mid, -self.root_sway)
        self.set_key(root, 'rotateY', end, self.root_sway)

    def set_spine_keys(self):
        for key, data in self.upper_body_params.items():
            ctrl = data['name']
            rx_vals = [data['rx'], -data['rx'], data['rx']]
            ry_vals = [data['ry'], -data['ry'], data['ry']]
            self.apply_keyframe_pattern((ctrl, 'rotateX'), rx_vals)
            self.apply_keyframe_pattern((ctrl, 'rotateY'), ry_vals)
            # Rock (rotateZ)
            rz = data['rz']
            times = [self.frames_stride_halved[0][0], self.quarter, self.frames_stride_halved[1][0], self.three_quarter, self.frames_stride_halved[2][0]]
            values = [ rz, -rz,  rz, -rz,  rz ]
            for t, v in zip(times, values):
                self.set_key(ctrl, 'rotateZ', t, v)


    def set_right_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        shoulder = self.resolve_node_case_insensitive(self.arm_ctrls['shoulder'])
        scapula = self.resolve_node_case_insensitive(self.arm_ctrls['scapula'])
        elbow = self.resolve_node_case_insensitive(self.arm_ctrls['elbow'])
        wrist = self.resolve_node_case_insensitive(self.arm_ctrls['wrist'])
    
        static_ry = self.arm_params['shoulder_down_y']
        scapula_down = self.arm_params['scapula_down']
    
        if shoulder:
            cmds.setAttr(f"{shoulder}.rotateY", static_ry)
            self.set_key(shoulder, 'rotateY', start, static_ry)
            self.set_key(shoulder, 'rotateY', end, static_ry)
            x_vals = [self.arm_params['shoulder_x'], -self.arm_params['shoulder_x'], self.arm_params['shoulder_x']]
            self.apply_keyframe_pattern((shoulder, 'rotateX'), x_vals)
    
        if scapula:
            cmds.setAttr(f"{scapula}.rotateY", scapula_down)
            self.set_key(scapula, 'rotateY', start, scapula_down)
            self.set_key(scapula, 'rotateY', end, scapula_down)
    
        for key, ctrl_raw in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                                 ['scapula', 'shoulder', 'elbow', 'wrist']):
            val = self.arm_params[key]
            ctrl = self.resolve_node_case_insensitive(self.arm_ctrls[ctrl_raw])
            if not ctrl:
                continue
            if key == 'elbow_z':
                val = max(val, 0)
                values = [0, val, 0]
            else:
                values = [val, -val, val]
            self.apply_keyframe_pattern((ctrl, 'rotateZ'), values)




            
    # append this new function inside your WalkCycleTool class
    
    def set_left_arm_keys(self):
        start, mid, end = [f[0] for f in self.frames_stride_halved]
        # Resolve L controls
        shoulder = self.resolve_node_case_insensitive(self.arm_ctrls['shoulder'].replace('_R', '_L'))
        scapula = self.resolve_node_case_insensitive(self.arm_ctrls['scapula'].replace('_R', '_L'))
        elbow = self.resolve_node_case_insensitive(self.arm_ctrls['elbow'].replace('_R', '_L'))
        wrist = self.resolve_node_case_insensitive(self.arm_ctrls['wrist'].replace('_R', '_L'))
    
        static_ry = self.arm_params['shoulder_down_y']
        scapula_down = self.arm_params['scapula_down']
    
        if shoulder:
            cmds.setAttr(f"{shoulder}.rotateY", static_ry)
            self.set_key(shoulder, 'rotateY', start, static_ry)
            self.set_key(shoulder, 'rotateY', end, static_ry)
            x_vals = [-self.arm_params['shoulder_x'], self.arm_params['shoulder_x'], -self.arm_params['shoulder_x']]
            self.apply_keyframe_pattern((shoulder, 'rotateX'), x_vals)
    
        if scapula:
            cmds.setAttr(f"{scapula}.rotateY", scapula_down)
            self.set_key(scapula, 'rotateY', start, scapula_down)
            self.set_key(scapula, 'rotateY', end, scapula_down)
    
        for key, ctrl_raw in zip(['scapula_z', 'shoulder_z', 'elbow_z', 'wrist_z'],
                                 ['scapula', 'shoulder', 'elbow', 'wrist']):
            val = self.arm_params[key]
            ctrl = self.resolve_node_case_insensitive(self.arm_ctrls[ctrl_raw].replace('_R', '_L'))
            if not ctrl:
                continue
            if key == 'elbow_z':
                val = max(val, 0)
                values = [val, 0, val]
            else:
                values = [-val, val, -val]
            self.apply_keyframe_pattern((ctrl, 'rotateZ'), values)





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
            'upper_body': {
                k: {'rx': v['rx'], 'ry': v['ry'], 'rz': v['rz']} for k, v in self.upper_body_params.items()
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
            text = cmds.promptDialog(query=True, text=True)
            settings = json.loads(text)
            self.apply_settings(settings)
            
            # manually update field values instead of calling self.show()
            self.update_ui_fields_from_settings()

        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    def apply_settings(self, settings):
        self.stride = settings.get('stride', self.stride)
        self.stride_width = settings.get('stride_width', self.stride_width)
        self.stride_height = settings.get('stride_height', self.stride_height)
        self.swing_extend = settings.get('swing_extend', self.swing_extend)
        self.hip_sway_lr = settings.get('hip_sway_lr', self.hip_sway_lr)
        self.root_bounce = settings.get('root_bounce', self.root_bounce)
        self.root_sway = settings.get('root_sway', self.root_sway)
        self.root_rock = settings.get('root_rock', self.root_rock)

        for key, vals in settings.get('upper_body', {}).items():
            if key in self.upper_body_params:
                self.upper_body_params[key]['rx'] = vals.get('rx', self.upper_body_params[key]['rx'])
                self.upper_body_params[key]['ry'] = vals.get('ry', self.upper_body_params[key]['ry'])
                self.upper_body_params[key]['rz'] = vals.get('rz', self.upper_body_params[key]['rz'])  # ?? NEW


        for k in ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']:
            if 'arms' in settings and k in settings['arms']:
                self.arm_params[k] = settings['arms'][k]

    def update_ui_fields_from_settings(self):
        cmds.floatField(self.stride_field, e=True, value=self.stride)
        cmds.floatField(self.stride_width_field, e=True, value=self.stride_width)
        cmds.floatField(self.stride_height_field, e=True, value=self.stride_height)
        cmds.floatField(self.swing_field, e=True, value=self.swing_extend)
        cmds.floatField(self.hip_sway_field, e=True, value=self.hip_sway_lr)
        cmds.floatField(self.root_bounce_field, e=True, value=self.root_bounce)
        cmds.floatField(self.root_sway_field, e=True, value=self.root_sway)
        cmds.floatField(self.root_rock_field, e=True, value=self.root_rock)
    
        for key in self.upper_body_params:
            cmds.floatField(self.upper_body_params[key]['rx_field'], e=True, value=self.upper_body_params[key]['rx'])
            cmds.floatField(self.upper_body_params[key]['ry_field'], e=True, value=self.upper_body_params[key]['ry'])
            cmds.floatField(self.upper_body_params[key]['rz_field'], e=True, value=self.upper_body_params[key]['rz'])  # ?? NEW

    
        for key in ['shoulder_down_y', 'scapula_down', 'scapula_z', 'shoulder_z', 'shoulder_x', 'elbow_z', 'wrist_z']:
            field_key = key + '_field'
            if field_key in self.arm_params:
                cmds.floatField(self.arm_params[field_key], e=True, value=self.arm_params[key])



# ?? To run:
WalkCycleTool().show()
