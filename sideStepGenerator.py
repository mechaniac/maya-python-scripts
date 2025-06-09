import maya.cmds as cmds
import json

class SideStepGenerator:
    def __init__(self):
        self.window = "SideStepGeneratorWindow"

        # Controls
        self.root = "RootX_M"
        self.leg_r = "IKLeg_R"
        self.leg_l = "IKLeg_L"
        self.hip = "HipSwinger_M"
        self.spine = "FKSpine1_M"
        self.chest = "FKChest_M"
        self.neck = "FKNeck_M"
        self.head = "FKHead_M"
        self.scapula_l = "FKScapula1_L"
        self.scapula_r = "FKScapula1_R"

        # Step settings
        self.step_width = 5.0
        self.step_height = 2.0
        self.foot_bounce = 1.0
        self.mirror = False

        # Root motion
        self.root_tilt = 5.0
        self.root_bounce = 1.0

        # Arm motion
        self.scapula_swing = 10.0
        self.shoulder_swing = 5.0
        self.elbow_swing = 5.0

        # Sidewhip motion
        self.hip_sway = 3.0
        self.spine_sway = 2.0
        self.chest_sway = 1.5
        self.neck_sway = 1.0
        self.head_sway = 0.5

        self.frames = []

    def resolve_node_case_insensitive(self, name):
        aliases = {
            'fkscapula_r': 'fkscapula1_r',
            'fkscapula_l': 'fkscapula1_l',
        }
        name_lower = name.lower()
        alias_target = aliases.get(name_lower, name_lower)

        all_nodes = cmds.ls(type="transform") + cmds.ls(type="joint") + cmds.ls(type="locator")
        for node in all_nodes:
            if node.lower() == alias_target:
                return node
        for node in all_nodes:
            if node.lower() == name_lower:
                return node
        return None

    def clear_keys(self):
        attrs = ['translateX', 'translateY', 'rotateX', 'rotateY', 'rotateZ']
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)

        controls = [
            self.root, self.leg_r, self.leg_l, self.hip,
            self.spine, self.chest, self.neck, self.head,
            self.scapula_l, self.scapula_r
        ]

        for ctrl in controls:
            resolved = self.resolve_node_case_insensitive(ctrl)
            if not resolved:
                print(f"?? Could not resolve: {ctrl}")
                continue
            for attr in attrs:
                full_attr = f"{resolved}.{attr}"
                if cmds.attributeQuery(attr, node=resolved, exists=True):
                    cmds.cutKey(resolved, at=attr, time=(start, end))
                    if not cmds.getAttr(full_attr, lock=True) and not cmds.connectionInfo(full_attr, isDestination=True):
                        cmds.setAttr(full_attr, 0)

    def compute_frames(self):
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
        quarter = start + (end - start) / 4.0
        mid = (start + end) / 2.0
        three_quarter = start + 3 * (end - start) / 4.0
        self.frames = [start, quarter, mid, three_quarter, end]

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
        cmds.setKeyframe(obj, at=attr, t=time)

    def set_leg_keys(self):
        start, quarter, mid, three_quarter, end = self.frames
        direction = -1 if self.mirror else 1
        step_x = direction * self.step_width
        lift_y = self.step_height

        first_leg = self.leg_r if self.mirror else self.leg_l
        second_leg = self.leg_l if self.mirror else self.leg_r

        self.set_key(first_leg, 'translateX', start, 0)
        self.set_key(first_leg, 'translateY', start, 0)
        self.set_key(first_leg, 'translateY', quarter, lift_y)
        self.set_key(first_leg, 'translateX', mid, step_x)
        self.set_key(first_leg, 'translateY', mid, 0)
        self.set_key(first_leg, 'translateX', end, 0)
        self.set_key(first_leg, 'translateY', end, 0)

        self.set_key(second_leg, 'translateX', start, 0)
        self.set_key(second_leg, 'translateY', start, 0)
        self.set_key(second_leg, 'translateX', mid, 0)
        self.set_key(second_leg, 'translateY', mid, 0)
        self.set_key(second_leg, 'translateY', three_quarter, lift_y)
        self.set_key(second_leg, 'translateX', three_quarter, step_x * 0.5)
        self.set_key(second_leg, 'translateX', end, 0)
        self.set_key(second_leg, 'translateY', end, 0)

    def set_root_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        direction = -1 if self.mirror else 1
        self.set_key(self.root, 'translateX', start, 0)
        self.set_key(self.root, 'rotateZ', start, 0)
        self.set_key(self.root, 'translateY', start, 0)
        self.set_key(self.root, 'translateX', mid, direction * self.step_width)
        self.set_key(self.root, 'rotateZ', mid, direction * self.root_tilt)
        self.set_key(self.root, 'translateY', mid, self.root_bounce)
        self.set_key(self.root, 'translateX', end, 0)
        self.set_key(self.root, 'rotateZ', end, 0)
        self.set_key(self.root, 'translateY', end, 0)

    def set_scapula_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        swing = self.scapula_swing
        self.set_key(self.scapula_l, 'rotateY', start, swing)
        self.set_key(self.scapula_l, 'rotateY', mid, -swing)
        self.set_key(self.scapula_l, 'rotateY', end, swing)
        self.set_key(self.scapula_r, 'rotateY', start, -swing)
        self.set_key(self.scapula_r, 'rotateY', mid, swing)
        self.set_key(self.scapula_r, 'rotateY', end, -swing)

    def set_sidewhip_keys(self):
        start, mid, end = self.frames[0], self.frames[2], self.frames[4]
        for ctrl, amount in [
            (self.hip, self.hip_sway),
            (self.spine, self.spine_sway),
            (self.chest, self.chest_sway),
            (self.neck, self.neck_sway),
            (self.head, self.head_sway),
        ]:
            sway = amount * (-1 if self.mirror else 1)
            self.set_key(ctrl, 'rotateY', start, sway)
            self.set_key(ctrl, 'rotateY', mid, -sway)
            self.set_key(ctrl, 'rotateY', end, sway)

    def generate(self):
        self.clear_keys()
        self.compute_frames()
        self.set_leg_keys()
        self.set_root_keys()
        self.set_scapula_keys()
        self.set_sidewhip_keys()

    def print_settings(self, *args):
        settings = {
            'step_width': self.step_width,
            'step_height': self.step_height,
            'foot_bounce': self.foot_bounce,
            'mirror': self.mirror,
            'root_tilt': self.root_tilt,
            'root_bounce': self.root_bounce,
            'scapula_swing': self.scapula_swing,
            'shoulder_swing': self.shoulder_swing,
            'elbow_swing': self.elbow_swing,
            'hip_sway': self.hip_sway,
            'spine_sway': self.spine_sway,
            'chest_sway': self.chest_sway,
            'neck_sway': self.neck_sway,
            'head_sway': self.head_sway,
        }
        print("// SideStepGenerator Settings:\n" + json.dumps(settings, indent=2))

    def apply_settings(self, settings):
        for k in settings:
            if hasattr(self, k):
                setattr(self, k, settings[k])

    def prompt_and_apply_settings(self, *args):
        result = cmds.promptDialog(
            title="Apply Settings",
            message="Paste JSON settings string here:",
            button=['Apply', 'Cancel'],
            defaultButton='Apply',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        if result != 'Apply':
            return
        try:
            text = cmds.promptDialog(query=True, text=True)
            settings = json.loads(text)
            self.apply_settings(settings)
            self.show()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    def on_generate(self, *args):
        self.step_width = cmds.floatField(self.step_width_field, query=True, value=True)
        self.step_height = cmds.floatField(self.step_height_field, query=True, value=True)
        self.foot_bounce = cmds.floatField(self.foot_bounce_field, query=True, value=True)
        self.mirror = cmds.checkBox(self.mirror_field, query=True, value=True)
    
        self.root_tilt = cmds.floatField(self.root_tilt_field, query=True, value=True)
        self.root_bounce = cmds.floatField(self.root_bounce_field, query=True, value=True)
    
        self.scapula_swing = cmds.floatField(self.scapula_swing_field, query=True, value=True)
        self.shoulder_swing = cmds.floatField(self.shoulder_swing_field, query=True, value=True)
        self.elbow_swing = cmds.floatField(self.elbow_swing_field, query=True, value=True)
    
        self.hip_sway = cmds.floatField(self.hip_sway_field, query=True, value=True)
        self.spine_sway = cmds.floatField(self.spine_sway_field, query=True, value=True)
        self.chest_sway = cmds.floatField(self.chest_sway_field, query=True, value=True)
        self.neck_sway = cmds.floatField(self.neck_sway_field, query=True, value=True)
        self.head_sway = cmds.floatField(self.head_sway_field, query=True, value=True)
    
        self.generate()


    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        self.window = cmds.window(self.window, title="Side Step Generator", widthHeight=(600, 800))
        cmds.scrollLayout()
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

        def two_col_row(label1, field_fn1, label2, field_fn2):
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(120, 80, 120, 80), adjustableColumn=4)
            cmds.text(label=label1)
            field_fn1()
            cmds.text(label=label2)
            field_fn2()
            cmds.setParent('..')

        # Step Settings
        cmds.frameLayout(label="Step Settings", collapsable=True, marginWidth=10)
        two_col_row(
            "Step Width (X):", lambda: setattr(self, 'step_width_field', cmds.floatField(value=self.step_width)),
            "Step Height (Y):", lambda: setattr(self, 'step_height_field', cmds.floatField(value=self.step_height))
        )
        two_col_row(
            "Foot Bounce (Y):", lambda: setattr(self, 'foot_bounce_field', cmds.floatField(value=self.foot_bounce)),
            "Mirror Step (Left):", lambda: setattr(self, 'mirror_field', cmds.checkBox(value=self.mirror))
        )
        cmds.setParent('..')

        # Root Settings
        cmds.frameLayout(label="Root Settings", collapsable=True, marginWidth=10)
        two_col_row(
            "Root Tilt (rotateZ):", lambda: setattr(self, 'root_tilt_field', cmds.floatField(value=self.root_tilt)),
            "Root Bounce (translateY):", lambda: setattr(self, 'root_bounce_field', cmds.floatField(value=self.root_bounce))
        )
        cmds.setParent('..')

        # Arm Settings
        cmds.frameLayout(label="Arm / Scapula Animation", collapsable=True, marginWidth=10)
        two_col_row(
            "Scapula Swing (rotateY):", lambda: setattr(self, 'scapula_swing_field', cmds.floatField(value=self.scapula_swing)),
            "Shoulder Swing (rotateZ):", lambda: setattr(self, 'shoulder_swing_field', cmds.floatField(value=self.shoulder_swing))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Elbow Bend (rotateZ):")
        self.elbow_swing_field = cmds.floatField(value=self.elbow_swing)
        cmds.setParent('..')
        cmds.setParent('..')

        # Torso Whip Settings
        cmds.frameLayout(label="SideWhip (Torso)", collapsable=True, marginWidth=10)
        two_col_row(
            "Hip Sway (rotateY):", lambda: setattr(self, 'hip_sway_field', cmds.floatField(value=self.hip_sway)),
            "Spine Sway (rotateY):", lambda: setattr(self, 'spine_sway_field', cmds.floatField(value=self.spine_sway))
        )
        two_col_row(
            "Chest Sway (rotateY):", lambda: setattr(self, 'chest_sway_field', cmds.floatField(value=self.chest_sway)),
            "Neck Sway (rotateY):", lambda: setattr(self, 'neck_sway_field', cmds.floatField(value=self.neck_sway))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Head Sway (rotateY):")
        self.head_sway_field = cmds.floatField(value=self.head_sway)
        cmds.setParent('..')
        cmds.setParent('..')

        # Actions
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 180, 180), adjustableColumn=3)
        cmds.button(label="Generate Side Step", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.setParent('..')

        cmds.showWindow(self.window)


# ? To run:
SideStepGenerator().show()
