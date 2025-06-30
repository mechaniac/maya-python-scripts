import maya.cmds as cmds
import json

class RunCycleGenerator:
    def __init__(self):
        self.window = "RunCycleGeneratorWindow"
        self.root_ctrl = "RootX_M"
        self.leg_r = "IKLeg_R"
        self.leg_l = "IKLeg_L"
        self.chest_ctrl = "FKChest_M"
        self.hip_ctrl = "HipSwinger_M"
        self.head_ctrl = "FKHead_M"

        
        self.arm_ctrls = {
            'scapula_l': "FKScapula1_L",
            'shoulder_l': "FKShoulder_L",
            'elbow_l': "FKElbow_L",
            'scapula_r': "FKScapula1_R",
            'shoulder_r': "FKShoulder_R",
            'elbow_r': "FKElbow_R",
        }
        
        # Head motion (FKHead_M)
        self.head_bounce = 1.5
        self.head_rock = 2.0
        self.head_lean = -10.0  # Now affects rotateZ
        self.head_sway = 1.0
        self.head_swing = 2.0   # This is on 4ths


        # Root movement
        self.root_bounce_up = 3.0
        self.root_bounce_down = -3.0
        self.root_lean = -20.0
        self.root_sway = 5.0
        self.root_swing = 4.0
        self.corkscrew = False

        # Leg stride
        self.stride_length = 10.0
        self.stride_width = 2.0
        self.stride_height = 5.0

        # Chest motion
        self.chest_bounce = 2.0
        self.chest_swing = 5.0
        self.chest_tilt = 3.0

        # Hip motion
        self.hip_swing = 6.0
        self.hip_side = 4.0
        
        # Arm Swing
        self.shoulder_down_y = -30.0
        self.scapula_down_y = -12.0  # default value matching your UI
        self.scapula_z = 10.0
        self.elbow_z = 15.0

        self.frames_stride_halved = []
        
        self.alias_map = {
            'fkchest_m': 'FKChest1_M',
            'fkhead_m': 'FKHead1_M',
            'rootswinger_m': 'RootX_M',
            'hipswinger_m': 'HipSwinger1_M',
            'ikleg_r': 'IKLeg_R',
            'ikleg_l': 'IKLeg_L',
            # Add more as needed
        }


    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
    
        self.window = cmds.window(self.window, title="Run Cycle Generator", widthHeight=(600, 600))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    
        def two_column_row(label1, field1, label2, field2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(120, 80, 120, 80), adjustableColumn=4)
            cmds.text(label=label1)
            field1()
            cmds.text(label=label2)
            field2()
            cmds.setParent('..')
    
        # === ROOT ===
        cmds.frameLayout(label="Root (RootX_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Bounce Up (Y):", lambda: setattr(self, 'root_bounce_up_field', cmds.floatField(value=self.root_bounce_up)),
            "Bounce Down (Y):", lambda: setattr(self, 'root_bounce_down_field', cmds.floatField(value=self.root_bounce_down))
        )
        two_column_row(
            "Lean (X):", lambda: setattr(self, 'root_lean_field', cmds.floatField(value=self.root_lean)),
            "Swing (Z):", lambda: setattr(self, 'root_swing_field', cmds.floatField(value=self.root_swing))
        )
        two_column_row(
            "Sway (Y):", lambda: setattr(self, 'root_sway_field', cmds.floatField(value=self.root_sway)),
            "", lambda: None
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 200))
        cmds.text(label="Corkscrew Twist:")
        self.corkscrew_field = cmds.checkBox(value=self.corkscrew)
        cmds.setParent('..')
        cmds.setParent('..')
    
        # === LEGS ===
        cmds.frameLayout(label="Legs", collapsable=True, marginWidth=10)
        two_column_row(
            "Stride Length (Z):", lambda: setattr(self, 'stride_length_field', cmds.floatField(value=self.stride_length)),
            "Stride Width (X):", lambda: setattr(self, 'stride_width_field', cmds.floatField(value=self.stride_width))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Stride Height (Y):")
        self.stride_height_field = cmds.floatField(value=self.stride_height)
        cmds.setParent('..')
        cmds.setParent('..')
    
        # === CHEST ===
        cmds.frameLayout(label="Chest / Shoulders (FKChest_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Chest Bounce (Z):", lambda: setattr(self, 'chest_bounce_field', cmds.floatField(value=self.chest_bounce)),
            "Chest Swing (X):", lambda: setattr(self, 'chest_swing_field', cmds.floatField(value=self.chest_swing))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Chest Tilt (Y):")
        self.chest_tilt_field = cmds.floatField(value=self.chest_tilt)
        cmds.setParent('..')
        cmds.setParent('..')
    
        # === HIPS ===
        cmds.frameLayout(label="HipSwinger (HipSwinger_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Hip Swing (X):", lambda: setattr(self, 'hip_swing_field', cmds.floatField(value=self.hip_swing)),
            "Hip Side (Y):", lambda: setattr(self, 'hip_side_field', cmds.floatField(value=self.hip_side))
        )
        cmds.setParent('..')
    
        # === ARMS ===
        cmds.frameLayout(label="Arms (Left / Right)", collapsable=True, marginWidth=10)
        two_column_row(
            "Shoulder Down (Y):", lambda: setattr(self, 'shoulder_down_y_field', cmds.floatField(value=self.shoulder_down_y)),
            "Scapula Down (Y):", lambda: setattr(self, 'scapula_down_y_field', cmds.floatField(value=self.scapula_down_y))
        )
        two_column_row(
            "Shoulder Swing (X):", lambda: setattr(self, 'shoulder_x_field', cmds.floatField(value=0)),
            "Scapula Swing (Z):", lambda: setattr(self, 'scapula_z_field', cmds.floatField(value=self.scapula_z))
        )

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(160, 80))
        cmds.text(label="Elbow Swing (Z, fwd only):")
        self.elbow_z_field = cmds.floatField(value=self.elbow_z)
        cmds.setParent('..')
        cmds.setParent('..')
    
        # === HEAD ===
        cmds.frameLayout(label="Head (FKHead_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Bounce (translateY):", lambda: setattr(self, 'head_bounce_field', cmds.floatField(value=self.head_bounce)),
            "Rock (rotateX):", lambda: setattr(self, 'head_rock_field', cmds.floatField(value=self.head_rock))
        )
        two_column_row(
            "Lean (rotateZ):", lambda: setattr(self, 'head_lean_field', cmds.floatField(value=self.head_lean)),
            "Swing (rotateY, 4ths):", lambda: setattr(self, 'head_swing_field', cmds.floatField(value=self.head_swing))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Sway (rotateY):")
        self.head_sway_field = cmds.floatField(value=self.head_sway)
        cmds.setParent('..')
        cmds.setParent('..')

    
        # === ACTIONS ===
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 180, 180), adjustableColumn=3)
        cmds.button(label="Generate Run Cycle", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')
    
        cmds.setParent('..')
        cmds.showWindow(self.window)



    def on_generate(self, *args):
        self.root_bounce_up = cmds.floatField(self.root_bounce_up_field, q=True, value=True)
        self.root_bounce_down = cmds.floatField(self.root_bounce_down_field, q=True, value=True)
        self.root_lean = cmds.floatField(self.root_lean_field, q=True, value=True)
        self.root_sway = cmds.floatField(self.root_sway_field, q=True, value=True)
        self.root_swing = cmds.floatField(self.root_swing_field, q=True, value=True)
        self.corkscrew = cmds.checkBox(self.corkscrew_field, q=True, value=True)

        self.stride_length = cmds.floatField(self.stride_length_field, q=True, value=True)
        self.stride_width = cmds.floatField(self.stride_width_field, q=True, value=True)
        self.stride_height = cmds.floatField(self.stride_height_field, q=True, value=True)

        self.chest_bounce = cmds.floatField(self.chest_bounce_field, q=True, value=True)
        self.chest_swing = cmds.floatField(self.chest_swing_field, q=True, value=True)
        self.chest_tilt = cmds.floatField(self.chest_tilt_field, q=True, value=True)
        
        self.head_bounce = cmds.floatField(self.head_bounce_field, q=True, value=True)
        self.head_rock = cmds.floatField(self.head_rock_field, q=True, value=True)
        self.head_lean = cmds.floatField(self.head_lean_field, q=True, value=True)
        self.head_sway = cmds.floatField(self.head_sway_field, q=True, value=True)
        self.head_swing = cmds.floatField(self.head_swing_field, q=True, value=True)


        self.hip_swing = cmds.floatField(self.hip_swing_field, q=True, value=True)
        self.hip_side = cmds.floatField(self.hip_side_field, q=True, value=True)
        
        self.shoulder_down_y = cmds.floatField(self.shoulder_down_y_field, q=True, value=True)
        self.scapula_down_y = cmds.floatField(self.scapula_down_y_field, q=True, value=True)

        self.scapula_z = cmds.floatField(self.scapula_z_field, q=True, value=True)
        self.elbow_z = abs(cmds.floatField(self.elbow_z_field, q=True, value=True))  # ensure non-negative


        self.generate()

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
            self.show()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    def apply_settings(self, settings):
        self.root_bounce_up = settings.get('root_bounce_up', self.root_bounce_up)
        self.root_bounce_down = settings.get('root_bounce_down', self.root_bounce_down)
        self.root_lean = settings.get('root_lean', self.root_lean)
        self.root_sway = settings.get('root_sway', self.root_sway)
        self.root_swing = settings.get('root_swing', self.root_swing)
        self.corkscrew = settings.get('corkscrew', self.corkscrew)

        self.stride_length = settings.get('stride_length', self.stride_length)
        self.stride_width = settings.get('stride_width', self.stride_width)
        self.stride_height = settings.get('stride_height', self.stride_height)

        self.chest_bounce = settings.get('chest_bounce', self.chest_bounce)
        self.chest_swing = settings.get('chest_swing', self.chest_swing)
        self.chest_tilt = settings.get('chest_tilt', self.chest_tilt)
        
        self.head_bounce = settings.get('head_bounce', self.head_bounce)
        self.head_rock = settings.get('head_rock', self.head_rock)
        self.head_lean = settings.get('head_lean', self.head_lean)
        self.head_sway = settings.get('head_sway', self.head_sway)
        self.head_swing = settings.get('head_swing', self.head_swing)

        self.scapula_down_y = arm.get('scapula_down_y', self.scapula_down_y)

        self.hip_swing = settings.get('hip_swing', self.hip_swing)
        self.hip_side = settings.get('hip_side', self.hip_side)
        
        if 'arm' in settings:
            arm = settings['arm']
            self.shoulder_down_y = arm.get('shoulder_down_y', self.shoulder_down_y)
            self.scapula_z = arm.get('scapula_z', self.scapula_z)
            self.elbow_z = abs(arm.get('elbow_z', self.elbow_z))

        
    def print_settings(self, *args):
        settings = {
            'root_bounce_up': self.root_bounce_up,
            'root_bounce_down': self.root_bounce_down,
            'root_lean': self.root_lean,
            'root_sway': self.root_sway,
            'root_swing': self.root_swing,
            'corkscrew': self.corkscrew,
            'stride_length': self.stride_length,
            'stride_width': self.stride_width,
            'stride_height': self.stride_height,
            'chest_bounce': self.chest_bounce,
            'chest_swing': self.chest_swing,
            'chest_tilt': self.chest_tilt,
            'hip_swing': self.hip_swing,
            'hip_side': self.hip_side,
            'arm': {
                'shoulder_down_y': self.shoulder_down_y,
                'scapula_z': self.scapula_z,
                'elbow_z': self.elbow_z,
            },
            'scapula_down_y': self.scapula_down_y

        }
        print("// RunCycleGenerator Settings:\n" + json.dumps(settings, indent=2))
        

    def generate(self):
        self.clear_keys()
    
        # Compute frame timing first
        self.compute_frames()
    
        # Resolve nodes second
        self.root_ctrl = self.resolve(self.root_ctrl)
        self.leg_r = self.resolve(self.leg_r)
        self.leg_l = self.resolve(self.leg_l)
        self.chest_ctrl = self.resolve(self.chest_ctrl)
        self.hip_ctrl = self.resolve(self.hip_ctrl)
        self.head_ctrl = self.resolve(self.head_ctrl)
        for k in self.arm_ctrls:
            self.arm_ctrls[k] = self.resolve(self.arm_ctrls[k])
    
        # Only now set keys
        self.set_root_keys()
        self.set_leg_keys()
        self.set_chest_keys()
        self.set_hip_keys()
        self.set_arm_keys()
        self.set_head_keys()





    def compute_frames(self):
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        mid = (start + end) / 2.0
        self.quarter = (start + mid) / 2.0
        self.three_quarter = (mid + end) / 2.0
        self.frames_stride_halved = [start, self.quarter, mid, self.three_quarter, end]

    def clear_keys(self):
        attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
    
        all_ctrls = [
            self.root_ctrl,
            self.leg_r, self.leg_l,
            self.chest_ctrl,
            self.hip_ctrl,
            getattr(self, 'head_ctrl', 'FKHead_M'),
        ]
        all_ctrls += list(self.arm_ctrls.values())
    
        for ctrl in all_ctrls:
            if not cmds.objExists(ctrl):
                continue
            for attr in attrs:
                full_attr = f"{ctrl}.{attr}"
                if not cmds.attributeQuery(attr, node=ctrl, exists=True):
                    continue
    
                cmds.cutKey(ctrl, at=attr, time=(start, end))
                if not cmds.getAttr(full_attr, lock=True) and not cmds.connectionInfo(full_attr, isDestination=True):
                    cmds.setAttr(full_attr, 0)



    def set_key(self, obj, attr, time, value):
        cmds.currentTime(time, edit=True)
        cmds.setAttr(f"{obj}.{attr}", value)
        cmds.setKeyframe(obj, at=attr, t=time)

    def set_root_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        self.set_key(self.root_ctrl, 'rotateX', start, self.root_lean)
        self.set_key(self.root_ctrl, 'rotateX', end, self.root_lean)

        self.set_key(self.root_ctrl, 'translateY', start, self.root_bounce_up)
        self.set_key(self.root_ctrl, 'translateY', quarter, self.root_bounce_down)
        self.set_key(self.root_ctrl, 'translateY', mid, self.root_bounce_up)
        self.set_key(self.root_ctrl, 'translateY', three_quarter, self.root_bounce_down)
        self.set_key(self.root_ctrl, 'translateY', end, self.root_bounce_up)

        if self.corkscrew:
            self.set_key(self.root_ctrl, 'rotateY', quarter, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', three_quarter, -self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', start, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', end, self.root_sway)
        else:
            self.set_key(self.root_ctrl, 'rotateY', start, self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', mid, -self.root_sway)
            self.set_key(self.root_ctrl, 'rotateY', end, self.root_sway)

        self.set_key(self.root_ctrl, 'rotateZ', start, self.root_swing)
        self.set_key(self.root_ctrl, 'rotateZ', mid, -self.root_swing)
        self.set_key(self.root_ctrl, 'rotateZ', end, self.root_swing)

    def set_leg_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        half_stride = self.stride_length / 2.0

        for leg, x in [(self.leg_r, self.stride_width), (self.leg_l, -self.stride_width)]:
            z_vals = [half_stride, -half_stride, half_stride] if leg == self.leg_r else [-half_stride, half_stride, -half_stride]
            for i, t in enumerate([start, mid, end]):
                self.set_key(leg, 'translateZ', t, z_vals[i])
                self.set_key(leg, 'translateX', t, x)

        # Lift at peak stride arc
        self.set_key(self.leg_r, 'translateY', three_quarter, self.stride_height)
        self.set_key(self.leg_l, 'translateY', quarter, self.stride_height)
        
        # Grounded at start, mid, end
        for t in [start, mid, end]:
            self.set_key(self.leg_r, 'translateY', t, 0)
            self.set_key(self.leg_l, 'translateY', t, 0)


    def set_chest_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        self.set_key(self.chest_ctrl, 'rotateZ', start, self.chest_bounce)
        self.set_key(self.chest_ctrl, 'rotateZ', quarter, -self.chest_bounce)
        self.set_key(self.chest_ctrl, 'rotateZ', mid, self.chest_bounce)
        self.set_key(self.chest_ctrl, 'rotateZ', three_quarter, -self.chest_bounce)
        self.set_key(self.chest_ctrl, 'rotateZ', end, self.chest_bounce)

        for attr, val in [('rotateX', self.chest_swing), ('rotateY', self.chest_tilt)]:
            self.set_key(self.chest_ctrl, attr, start, val)
            self.set_key(self.chest_ctrl, attr, mid, -val)
            self.set_key(self.chest_ctrl, attr, end, val)

    def set_hip_keys(self):
        start, mid, end = self.frames_stride_halved[0], self.frames_stride_halved[2], self.frames_stride_halved[4]
        for attr, val in [('rotateX', self.hip_swing), ('rotateY', self.hip_side)]:
            self.set_key(self.hip_ctrl, attr, start, val)
            self.set_key(self.hip_ctrl, attr, mid, -val)
            self.set_key(self.hip_ctrl, attr, end, val)
            
    def set_head_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        ctrl = self.head_ctrl
    
        # Bounce on 5ths
        self.set_key(ctrl, 'translateY', start, self.head_bounce)
        self.set_key(ctrl, 'translateY', quarter, -self.head_bounce)
        self.set_key(ctrl, 'translateY', mid, self.head_bounce)
        self.set_key(ctrl, 'translateY', three_quarter, -self.head_bounce)
        self.set_key(ctrl, 'translateY', end, self.head_bounce)
    
        # Rock (rotateX): 3-key loop
        self.set_key(ctrl, 'rotateX', start, -self.head_rock)
        self.set_key(ctrl, 'rotateX', mid, self.head_rock)
        self.set_key(ctrl, 'rotateX', end, -self.head_rock)
    
        # Lean (rotateZ): static offset
        self.set_key(ctrl, 'rotateZ', start, self.head_lean)
        self.set_key(ctrl, 'rotateZ', end, self.head_lean)
    
        # Swing (rotateY): animated on fourths
        self.set_key(ctrl, 'rotateY', start, self.head_swing)
        self.set_key(ctrl, 'rotateY', quarter, 0)
        self.set_key(ctrl, 'rotateY', mid, -self.head_swing)
        self.set_key(ctrl, 'rotateY', three_quarter, 0)
        self.set_key(ctrl, 'rotateY', end, self.head_swing)



    def set_arm_keys(self):
        start, mid, end = self.frames_stride_halved[0], self.frames_stride_halved[2], self.frames_stride_halved[4]

        for side in ['l', 'r']:
            scapula = self.arm_ctrls[f'scapula_{side}']
            shoulder = self.arm_ctrls[f'shoulder_{side}']
            elbow = self.arm_ctrls[f'elbow_{side}']
            
            # Scapula Down (translateY)
            cmds.setAttr(f"{scapula}.translateY", self.scapula_down_y)
            self.set_key(scapula, 'translateY', start, self.scapula_down_y)
            self.set_key(scapula, 'translateY', end, self.scapula_down_y)


            # Static arm down
            cmds.setAttr(f"{shoulder}.rotateY", self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', start, self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', end, self.shoulder_down_y)

            # Opposing scapula swings
            scapula_vals = [self.scapula_z, -self.scapula_z, self.scapula_z] if side == 'l' else [-self.scapula_z, self.scapula_z, -self.scapula_z]
            for t, val in zip([start, mid, end], scapula_vals):
                self.set_key(scapula, 'rotateZ', t, val)

            # Elbow: forward-only swing with mirrored timing
            if side == 'l':
                elbow_vals = [self.elbow_z, 0, self.elbow_z]
            else:
                elbow_vals = [0, self.elbow_z, 0]  # mirrored motion but only positive

            for t, val in zip([start, mid, end], elbow_vals):
                self.set_key(elbow, 'rotateZ', t, val)

    def resolve(self, name):
        all_nodes = cmds.ls(type='transform')
        name_lower = name.lower()

        # First try exact case-insensitive match
        for node in all_nodes:
            if node.lower() == name_lower:
                return node

        # Then try alias fallback
        if name_lower in self.alias_map:
            alias_target = self.alias_map[name_lower]
            if cmds.objExists(alias_target):
                return alias_target

        raise RuntimeError("Node not found: {}".format(name))


# ?? To run:
RunCycleGenerator().show()
