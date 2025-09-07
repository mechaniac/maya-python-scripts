import maya.cmds as cmds
import json
import re

class RunCycleGenerator:
    def __init__(self):
        self.window = "RunCycleGeneratorWindow"
        self.root_ctrl = "RootX_M"
        self.leg_r = "IKLeg_R"
        self.leg_l = "IKLeg_L"
        self.chest_ctrl = "FKChest_M"
        self.hip_ctrl = "HipSwinger_M"
        self.head_ctrl = "FKHead_M"
            # alongside self.head_ctrl:
        self.neck_ctrl = "FKNeck_M"

        # at the top of __init__, alongside other motions:
        self.foot_raise = 10.0   # degrees of toe-lift (rotateX) on each step

        
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

        # Neck motion (FKNeck_M), start it off matching head
        self.neck_bounce = self.head_bounce
        self.neck_rock   = self.head_rock
        self.neck_lean   = self.head_lean
        self.neck_sway   = self.head_sway
        self.neck_swing  = self.head_swing
        
        # Spine motion (FKSpine_M)
        self.spine_ctrl       = "FKSpine_M"
        self.spine_bounce     = 0.0
        self.spine_swing      = 0.0
        self.spine_tilt       = 0.0

        # Rotate-Z offsets for chest, spine, neck, head
        self.chest_z_offset   = 0.0
        self.spine_z_offset   = 0.0
        self.neck_z_offset    = 0.0
        self.head_z_offset    = 0.0


        # Root movement
        self.root_bounce_up = 3.0
        self.root_bounce_down = -3.0
        self.root_lean = -20.0
        self.root_sway = 5.0
        self.root_swing = 4.0
        self.corkscrew = False
        self.root_back_forth = 0.0    # translateZ on fifths


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
        self.shoulder_rotate_x    = 0.0   # rotateX offset on the shoulder
        self.shoulder_swing_z     = 0.0   # rotateZ swing on the shoulder
        self.shoulder_sway_out_y  = 0.0   # rotateY “sway out” on the shoulder

        self.frames_stride_halved = []
        
        self.alias_map = {
            'fkchest_m': 'FKChest1_M',
            'fkhead_m': 'FKHead1_M',
            'fkspine_m': 'FKSpine1_M',      # ← add this
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
        
        two_column_row(
            "Back/Forth (Z):",
            lambda: setattr(self, 'root_back_forth_field', cmds.floatField(value=self.root_back_forth)),
            "",
            lambda: None
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
        
            # immediately after you create the stride-height floatField:
        two_column_row(
            "Foot Raise (rotateX):", 
            lambda: setattr(self, 'foot_raise_field', cmds.floatField(value=self.foot_raise)),
            "", 
            lambda: None
        )

    
        # === CHEST ===
        cmds.frameLayout(label="Chest / Shoulders (FKChest_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Chest Bounce (Z):", lambda: setattr(self, 'chest_bounce_field', cmds.floatField(value=self.chest_bounce)),
            "Chest Swing (X):", lambda: setattr(self, 'chest_swing_field', cmds.floatField(value=self.chest_swing))
        )
        
        two_column_row(
            "Rotate Z Offset:", lambda: setattr(self, 'chest_z_offset_field', cmds.floatField(value=self.chest_z_offset)),
            "", lambda: None
        )

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Chest Tilt (Y):")
        self.chest_tilt_field = cmds.floatField(value=self.chest_tilt)
        cmds.setParent('..')
        cmds.setParent('..')

        # === SPINE ===
        cmds.frameLayout(label="Spine (FKSpine_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Spine Bounce (Z):", lambda: setattr(self, 'spine_bounce_field', cmds.floatField(value=self.spine_bounce)),
            "Spine Swing (X):",  lambda: setattr(self, 'spine_swing_field',  cmds.floatField(value=self.spine_swing))
        )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Spine Tilt (Y):")
        self.spine_tilt_field = cmds.floatField(value=self.spine_tilt)
        cmds.setParent('..')
        two_column_row(
            "Rotate Z Offset:", lambda: setattr(self, 'spine_z_offset_field', cmds.floatField(value=self.spine_z_offset)),
            "", lambda: None
        )
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
            "Scapula Swing (Z):", lambda: setattr(self, 'scapula_z_field', cmds.floatField(value=self.scapula_z)),
            "", lambda: None
        )

        
        two_column_row(
            "Shoulder Rotate (X):", lambda: setattr(self, 'shoulder_rotate_x_field', cmds.floatField(value=self.shoulder_rotate_x)),
            "Shoulder Swing (Z):",  lambda: setattr(self, 'shoulder_swing_z_field', cmds.floatField(value=self.shoulder_swing_z))
        )
        two_column_row(
            "Shoulder SwayOut (Y):", lambda: setattr(self, 'shoulder_sway_out_y_field', cmds.floatField(value=self.shoulder_sway_out_y)),
            "",                     lambda: None
        )


        cmds.rowLayout(numberOfColumns=2, columnWidth2=(160, 80))
        cmds.text(label="Elbow Swing (Z, fwd only):")
        self.elbow_z_field = cmds.floatField(value=self.elbow_z)
        cmds.setParent('..')
        cmds.setParent('..')

        # === NECK ===
        cmds.frameLayout(label="Neck (FKNeck_M)", collapsable=True, marginWidth=10)
        two_column_row(
            "Bounce (translateY):", 
            lambda: setattr(self, 'neck_bounce_field', cmds.floatField(value=self.neck_bounce)),
            "Rock (rotateX):", 
            lambda: setattr(self, 'neck_rock_field',   cmds.floatField(value=self.neck_rock))
        )
        two_column_row(
            "Lean (rotateZ):",        
            lambda: setattr(self, 'neck_lean_field',   cmds.floatField(value=self.neck_lean)),
            "Swing (rotateY, 4ths):", 
            lambda: setattr(self, 'neck_swing_field',  cmds.floatField(value=self.neck_swing))
        )        
        two_column_row(
            "Rotate Z Offset:", lambda: setattr(self, 'neck_z_offset_field', cmds.floatField(value=self.neck_z_offset)),
            "", lambda: None
        )

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Sway (rotateY):")
        self.neck_sway_field = cmds.floatField(value=self.neck_sway)
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
        two_column_row(
            "Rotate Z Offset:", lambda: setattr(self, 'head_z_offset_field', cmds.floatField(value=self.head_z_offset)),
            "", lambda: None
        )

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 80))
        cmds.text(label="Sway (rotateY):")
        self.head_sway_field = cmds.floatField(value=self.head_sway)
        cmds.setParent('..')
        cmds.setParent('..')

    
        # === ACTIONS ===
        cmds.separator(height=10, style='in')
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(150, 150, 150, 150), adjustableColumn=4)
        cmds.button(label="Generate Run Cycle", command=self.on_generate)
        cmds.button(label="Print Settings", command=self.print_settings)
        cmds.button(label="Apply Settings", command=self.prompt_and_apply_settings)
        cmds.button(label="Reload UI", command=lambda *_: self.show())
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
        self.root_back_forth = cmds.floatField(self.root_back_forth_field, q=True, value=True)


        self.stride_length = cmds.floatField(self.stride_length_field, q=True, value=True)
        self.stride_width = cmds.floatField(self.stride_width_field, q=True, value=True)
        self.stride_height = cmds.floatField(self.stride_height_field, q=True, value=True)
            # after you pull in stride_height…
        self.foot_raise   = cmds.floatField(self.foot_raise_field, q=True, value=True)


        self.chest_bounce = cmds.floatField(self.chest_bounce_field, q=True, value=True)
        self.chest_swing = cmds.floatField(self.chest_swing_field, q=True, value=True)
        self.chest_tilt = cmds.floatField(self.chest_tilt_field, q=True, value=True)
        
        
        # Spine
        self.spine_bounce   = cmds.floatField(self.spine_bounce_field,   q=True, value=True)
        self.spine_swing    = cmds.floatField(self.spine_swing_field,    q=True, value=True)
        self.spine_tilt     = cmds.floatField(self.spine_tilt_field,     q=True, value=True)
        self.spine_z_offset = cmds.floatField(self.spine_z_offset_field, q=True, value=True)

        # Chest Z-offset
        self.chest_z_offset = cmds.floatField(self.chest_z_offset_field, q=True, value=True)
        # Neck Z-offset
        self.neck_z_offset  = cmds.floatField(self.neck_z_offset_field,  q=True, value=True)
        # Head Z-offset
        self.head_z_offset  = cmds.floatField(self.head_z_offset_field,  q=True, value=True)

        
        self.head_bounce = cmds.floatField(self.head_bounce_field, q=True, value=True)
        self.head_rock = cmds.floatField(self.head_rock_field, q=True, value=True)
        self.head_lean = cmds.floatField(self.head_lean_field, q=True, value=True)
        self.head_sway = cmds.floatField(self.head_sway_field, q=True, value=True)
        self.head_swing = cmds.floatField(self.head_swing_field, q=True, value=True)

        self.neck_bounce = cmds.floatField(self.neck_bounce_field, q=True, value=True)
        self.neck_rock   = cmds.floatField(self.neck_rock_field,   q=True, value=True)
        self.neck_lean   = cmds.floatField(self.neck_lean_field,   q=True, value=True)
        self.neck_sway   = cmds.floatField(self.neck_sway_field,   q=True, value=True)
        self.neck_swing  = cmds.floatField(self.neck_swing_field,  q=True, value=True)

        self.hip_swing = cmds.floatField(self.hip_swing_field, q=True, value=True)
        self.hip_side = cmds.floatField(self.hip_side_field, q=True, value=True)
        
        self.shoulder_down_y = cmds.floatField(self.shoulder_down_y_field, q=True, value=True)
        self.scapula_down_y = cmds.floatField(self.scapula_down_y_field, q=True, value=True)
        self.shoulder_rotate_x   = cmds.floatField(self.shoulder_rotate_x_field,    q=True, value=True)
        self.shoulder_swing_z    = cmds.floatField(self.shoulder_swing_z_field,     q=True, value=True)
        self.shoulder_sway_out_y = cmds.floatField(self.shoulder_sway_out_y_field,  q=True, value=True)

        self.scapula_z = cmds.floatField(self.scapula_z_field, q=True, value=True)
        self.elbow_z = abs(cmds.floatField(self.elbow_z_field, q=True, value=True))  # ensure non-negative


        self.generate()

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
        raw = cmds.promptDialog(query=True, text=True)
        try:
            data = self._parse_settings_text(raw)
            self.apply_settings(data)   # do NOT rebuild UI here
            self.refresh_ui()           # just update fields
        except Exception as e:
            # keep the window alive; show the error
            cmds.confirmDialog(title="Error", message=str(e))



    def apply_settings(self, settings):
        # root / global
        self.root_bounce_up   = self._num(settings.get('root_bounce_up',   self.root_bounce_up),   self.root_bounce_up)
        self.root_bounce_down = self._num(settings.get('root_bounce_down', self.root_bounce_down), self.root_bounce_down)
        self.root_lean        = self._num(settings.get('root_lean',        self.root_lean),        self.root_lean)
        self.root_sway        = self._num(settings.get('root_sway',        self.root_sway),        self.root_sway)
        self.root_swing       = self._num(settings.get('root_swing',       self.root_swing),       self.root_swing)
        self.root_back_forth  = self._num(settings.get('root_back_forth',  self.root_back_forth),  self.root_back_forth)
        self.corkscrew        = self._bool(settings.get('corkscrew',        self.corkscrew),        self.corkscrew)
    
        # stride / legs
        self.stride_length = self._num(settings.get('stride_length', self.stride_length), self.stride_length)
        self.stride_width  = self._num(settings.get('stride_width',  self.stride_width),  self.stride_width)
        self.stride_height = self._num(settings.get('stride_height', self.stride_height), self.stride_height)
        self.foot_raise    = self._num(settings.get('foot_raise',    self.foot_raise),    self.foot_raise)
    
        # chest
        self.chest_bounce   = self._num(settings.get('chest_bounce', self.chest_bounce), self.chest_bounce)
        self.chest_swing    = self._num(settings.get('chest_swing',  self.chest_swing),  self.chest_swing)
        self.chest_tilt     = self._num(settings.get('chest_tilt',   self.chest_tilt),   self.chest_tilt)
        self.chest_z_offset = self._num(settings.get('chest_z_offset', self.chest_z_offset), self.chest_z_offset)
    
        # spine
        self.spine_bounce   = self._num(settings.get('spine_bounce', self.spine_bounce), self.spine_bounce)
        self.spine_swing    = self._num(settings.get('spine_swing',  self.spine_swing),  self.spine_swing)
        self.spine_tilt     = self._num(settings.get('spine_tilt',   self.spine_tilt),   self.spine_tilt)
        self.spine_z_offset = self._num(settings.get('spine_z_offset', self.spine_z_offset), self.spine_z_offset)
    
        # hips
        self.hip_swing = self._num(settings.get('hip_swing', self.hip_swing), self.hip_swing)
        self.hip_side  = self._num(settings.get('hip_side',  self.hip_side),  self.hip_side)
    
        # arms (nested)
        arm = settings.get('arm', {}) if isinstance(settings.get('arm', {}), dict) else {}
        self.shoulder_down_y     = self._num(arm.get('shoulder_down_y', self.shoulder_down_y), self.shoulder_down_y)
        self.scapula_down_y      = self._num(arm.get('scapula_down_y',  self.scapula_down_y),  self.scapula_down_y)
        self.scapula_z           = self._num(arm.get('scapula_z',       self.scapula_z),       self.scapula_z)
        self.elbow_z             = abs(self._num(arm.get('elbow_z',     self.elbow_z),         self.elbow_z))
        self.shoulder_rotate_x   = self._num(arm.get('shoulder_rotate_x',  self.shoulder_rotate_x),  self.shoulder_rotate_x)
        self.shoulder_swing_z    = self._num(arm.get('shoulder_swing_z',   self.shoulder_swing_z),   self.shoulder_swing_z)
        self.shoulder_sway_out_y = self._num(arm.get('shoulder_sway_out_y',self.shoulder_sway_out_y),self.shoulder_sway_out_y)
    
        # head (accept nested or flat)
        hb = settings.get('head_bounce', self._dig(settings, 'head', 'bounce'))
        hr = settings.get('head_rock',   self._dig(settings, 'head', 'rock'))
        hl = settings.get('head_lean',   self._dig(settings, 'head', 'lean'))
        hs = settings.get('head_sway',   self._dig(settings, 'head', 'sway'))
        hY = settings.get('head_swing',  self._dig(settings, 'head', 'swing'))
        self.head_bounce = self._num(hb if hb is not None else self.head_bounce, self.head_bounce)
        self.head_rock   = self._num(hr if hr is not None else self.head_rock,   self.head_rock)
        self.head_lean   = self._num(hl if hl is not None else self.head_lean,   self.head_lean)
        self.head_sway   = self._num(hs if hs is not None else self.head_sway,   self.head_sway)
        self.head_swing  = self._num(hY if hY is not None else self.head_swing,  self.head_swing)
    
        # neck (accept nested or flat)
        nb = settings.get('neck_bounce', self._dig(settings, 'neck', 'bounce'))
        nr = settings.get('neck_rock',   self._dig(settings, 'neck', 'rock'))
        nl = settings.get('neck_lean',   self._dig(settings, 'neck', 'lean'))
        ns = settings.get('neck_sway',   self._dig(settings, 'neck', 'sway'))
        nY = settings.get('neck_swing',  self._dig(settings, 'neck', 'swing'))
        self.neck_bounce = self._num(nb if nb is not None else self.neck_bounce, self.neck_bounce)
        self.neck_rock   = self._num(nr if nr is not None else self.neck_rock,   self.neck_rock)
        self.neck_lean   = self._num(nl if nl is not None else self.neck_lean,   self.neck_lean)
        self.neck_sway   = self._num(ns if ns is not None else self.neck_sway,   self.neck_sway)
        self.neck_swing  = self._num(nY if nY is not None else self.neck_swing,  self.neck_swing)


    # --- tolerant parsing & coercion ---
    def _sanitize_json_text(self, text):
        import re
        # strip // line comments
        text = re.sub(r'//.*', '', text)
        # strip /* block comments */
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        # remove trailing commas before } or ]
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        # common pythonisms -> JSON
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)
        return text
    
    def _parse_settings_text(self, raw):
        import json
        try:
            return json.loads(raw)
        except Exception:
            return json.loads(self._sanitize_json_text(raw))
    
    def _num(self, v, default):
        try:
            # Accept strings like "12", "12.0", "  -3 "
            return float(v)
        except Exception:
            return default
    
    def _bool(self, v, default):
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ('1','true','yes','on'): return True
        if s in ('0','false','no','off'): return False
        return default
    
    def _dig(self, d, *ks):
        cur = d
        for k in ks:
            if not isinstance(cur, dict) or k not in cur: return None
            cur = cur[k]
        return cur
    
    def refresh_ui(self):
        """Update existing UI fields instead of rebuilding the window."""
        def _set(ff, val):
            if hasattr(self, ff):
                try:
                    cmds.floatField(getattr(self, ff), e=True, value=val)
                except:
                    pass
        # root
        _set('root_bounce_up_field',   self.root_bounce_up)
        _set('root_bounce_down_field', self.root_bounce_down)
        _set('root_lean_field',        self.root_lean)
        _set('root_sway_field',        self.root_sway)
        _set('root_swing_field',       self.root_swing)
        _set('root_back_forth_field',  self.root_back_forth)
        try: cmds.checkBox(self.corkscrew_field, e=True, value=self.corkscrew)
        except: pass
    
        # legs
        _set('stride_length_field', self.stride_length)
        _set('stride_width_field',  self.stride_width)
        _set('stride_height_field', self.stride_height)
        _set('foot_raise_field',    self.foot_raise)
    
        # chest
        _set('chest_bounce_field', self.chest_bounce)
        _set('chest_swing_field',  self.chest_swing)
        _set('chest_tilt_field',   self.chest_tilt)
        _set('chest_z_offset_field', self.chest_z_offset)
    
        # spine
        _set('spine_bounce_field', self.spine_bounce)
        _set('spine_swing_field',  self.spine_swing)
        _set('spine_tilt_field',   self.spine_tilt)
        _set('spine_z_offset_field', self.spine_z_offset)
    
        # hips
        _set('hip_swing_field', self.hip_swing)
        _set('hip_side_field',  self.hip_side)
    
        # arms
        _set('shoulder_down_y_field',    self.shoulder_down_y)
        _set('scapula_down_y_field',     self.scapula_down_y)
        _set('scapula_z_field',          self.scapula_z)
        _set('elbow_z_field',            self.elbow_z)
        _set('shoulder_rotate_x_field',  self.shoulder_rotate_x)
        _set('shoulder_swing_z_field',   self.shoulder_swing_z)
        _set('shoulder_sway_out_y_field', self.shoulder_sway_out_y)
    
        # neck
        _set('neck_bounce_field', self.neck_bounce)
        _set('neck_rock_field',   self.neck_rock)
        _set('neck_lean_field',   self.neck_lean)
        _set('neck_sway_field',   self.neck_sway)
        _set('neck_swing_field',  self.neck_swing)
        _set('neck_z_offset_field', self.neck_z_offset)
    
        # head
        _set('head_bounce_field', self.head_bounce)
        _set('head_rock_field',   self.head_rock)
        _set('head_lean_field',   self.head_lean)
        _set('head_sway_field',   self.head_sway)
        _set('head_swing_field',  self.head_swing)
        _set('head_z_offset_field', self.head_z_offset)


        
    def print_settings(self, *args):
        settings = {
            'root_bounce_up':     self.root_bounce_up,
            'root_bounce_down':   self.root_bounce_down,
            'root_lean':          self.root_lean,
            'root_sway':          self.root_sway,
            'root_swing':         self.root_swing,
            'root_back_forth':    self.root_back_forth,
            'corkscrew':          self.corkscrew,
    
            'stride_length':      self.stride_length,
            'stride_width':       self.stride_width,
            'stride_height':      self.stride_height,
            'foot_raise':         self.foot_raise,
    
            'chest_bounce':       self.chest_bounce,
            'chest_swing':        self.chest_swing,
            'chest_tilt':         self.chest_tilt,
    
            'hip_swing':          self.hip_swing,
            'hip_side':           self.hip_side,
    
            'arm': {
                'shoulder_down_y':    self.shoulder_down_y,
                'scapula_down_y':     self.scapula_down_y,
                'scapula_z':          self.scapula_z,
                'elbow_z':            self.elbow_z,
                'shoulder_rotate_x':  self.shoulder_rotate_x,
                'shoulder_swing_z':   self.shoulder_swing_z,
                'shoulder_sway_out_y': self.shoulder_sway_out_y,
            },
    
            'head': {
                'bounce':            self.head_bounce,
                'rock':              self.head_rock,
                'lean':              self.head_lean,
                'sway':              self.head_sway,
                'swing':             self.head_swing,
            },
    
            'neck': {
                'bounce':            self.neck_bounce,
                'rock':              self.neck_rock,
                'lean':              self.neck_lean,
                'sway':              self.neck_sway,
                'swing':             self.neck_swing,
            }
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
        self.neck_ctrl = self.resolve(self.neck_ctrl)    # ← new
        self.spine_ctrl = self.resolve(self.spine_ctrl)  # ← add this
        for k in self.arm_ctrls:
            self.arm_ctrls[k] = self.resolve(self.arm_ctrls[k])
    
        # Only now set keys
        self.set_root_keys()
        self.set_leg_keys()
        self.set_chest_keys()
        self.set_spine_keys()   # ← new
        self.set_hip_keys()
        self.set_arm_keys()
        self.set_head_keys()
        self.set_neck_keys()   # ← new




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
            self.neck_ctrl,
            self.spine_ctrl,                # ← add this
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
        
        # back/forth on fifths
        span = end - start
        first_fifth  = start + span * (1/5.0)
        fourth_fifth = start + span * (4/5.0)
        
        # zero out translateZ at start, mid, end
        for t in (start, mid, end):
            self.set_key(self.root_ctrl, 'translateZ', t, 0)
        
        # apply back/forth
        self.set_key(self.root_ctrl, 'translateZ', first_fifth,  self.root_back_forth)
        self.set_key(self.root_ctrl, 'translateZ', fourth_fifth, self.root_back_forth)


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
        
                # ---- foot-lift on fifths ----
        span = end - start
        first_fifth  = start + span * (1/5.0)
        fourth_fifth = start + span * (4/5.0)
    
        # clear any existing foot rotation at ground
        for t in (start, mid, end):
            self.set_key(self.leg_l, 'rotateX', t, 0)
            self.set_key(self.leg_r, 'rotateX', t, 0)
    
        # apply the toe-lift
        self.set_key(self.leg_l, 'rotateX', first_fifth,  self.foot_raise)
        self.set_key(self.leg_r, 'rotateX', fourth_fifth, self.foot_raise)
        # ------------------------------
        
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
        self.set_key(self.chest_ctrl, 'rotateZ', start,      self.chest_bounce + self.chest_z_offset)
        self.set_key(self.chest_ctrl, 'rotateZ', quarter,   -self.chest_bounce + self.chest_z_offset)
        self.set_key(self.chest_ctrl, 'rotateZ', mid,        self.chest_bounce + self.chest_z_offset)
        self.set_key(self.chest_ctrl, 'rotateZ', three_quarter, -self.chest_bounce + self.chest_z_offset)
        self.set_key(self.chest_ctrl, 'rotateZ', end,        self.chest_bounce + self.chest_z_offset)


        for attr, val in [('rotateX', self.chest_swing), ('rotateY', self.chest_tilt)]:
            self.set_key(self.chest_ctrl, attr, start, val)
            self.set_key(self.chest_ctrl, attr, mid, -val)
            self.set_key(self.chest_ctrl, attr, end, val)

    def set_spine_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        # RotateZ bounce on fifths, with offset
        for t, val in zip(
            [start, quarter, mid, three_quarter, end],
            [self.spine_bounce, -self.spine_bounce, self.spine_bounce, -self.spine_bounce, self.spine_bounce]
        ):
            self.set_key(self.spine_ctrl, 'rotateZ', t, val + self.spine_z_offset)

        # Swing (rotateX) & Tilt (rotateY) exactly like chest
        for attr, base in [('rotateX', self.spine_swing), ('rotateY', self.spine_tilt)]:
            self.set_key(self.spine_ctrl, attr, start,  base)
            self.set_key(self.spine_ctrl, attr, mid,   -base)
            self.set_key(self.spine_ctrl, attr, end,    base)


    def set_hip_keys(self):
        start, mid, end = self.frames_stride_halved[0], self.frames_stride_halved[2], self.frames_stride_halved[4]
        for attr, val in [('rotateX', self.hip_swing), ('rotateY', self.hip_side)]:
            self.set_key(self.hip_ctrl, attr, start, val)
            self.set_key(self.hip_ctrl, attr, mid, -val)
            self.set_key(self.hip_ctrl, attr, end, val)

    def set_neck_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved
        ctrl = self.neck_ctrl
    
        # Bounce (translateY) on fifths
        self.set_key(ctrl, 'translateY', start, self.neck_bounce)
        self.set_key(ctrl, 'translateY', quarter, -self.neck_bounce)
        self.set_key(ctrl, 'translateY', mid, self.neck_bounce)
        self.set_key(ctrl, 'translateY', three_quarter, -self.neck_bounce)
        self.set_key(ctrl, 'translateY', end, self.neck_bounce)
    
        # Rock (rotateX) 3-key loop
        self.set_key(ctrl, 'rotateX', start, -self.neck_rock)
        self.set_key(ctrl, 'rotateX', mid, self.neck_rock)
        self.set_key(ctrl, 'rotateX', end, -self.neck_rock)
    
        # Lean (rotateZ) static
        self.set_key(ctrl, 'rotateZ', start, self.neck_lean + self.neck_z_offset)
        self.set_key(ctrl, 'rotateZ', end,   self.neck_lean + self.neck_z_offset)

    
        # Swing (rotateY) on fourths
        self.set_key(ctrl, 'rotateY', start, self.neck_swing)
        self.set_key(ctrl, 'rotateY', quarter, 0)
        self.set_key(ctrl, 'rotateY', mid, -self.neck_swing)
        self.set_key(ctrl, 'rotateY', three_quarter, 0)
        self.set_key(ctrl, 'rotateY', end, self.neck_swing)


            
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
        self.set_key(ctrl, 'rotateZ', start, self.head_lean + self.head_z_offset)
        self.set_key(ctrl, 'rotateZ', end,   self.head_lean + self.head_z_offset)

    
        # Swing (rotateY): animated on fourths
        self.set_key(ctrl, 'rotateY', start, self.head_swing)
        self.set_key(ctrl, 'rotateY', quarter, 0)
        self.set_key(ctrl, 'rotateY', mid, -self.head_swing)
        self.set_key(ctrl, 'rotateY', three_quarter, 0)
        self.set_key(ctrl, 'rotateY', end, self.head_swing)



    def set_arm_keys(self):
        start, quarter, mid, three_quarter, end = self.frames_stride_halved

        for side in ['l', 'r']:
            scapula = self.arm_ctrls[f'scapula_{side}']
            shoulder = self.arm_ctrls[f'shoulder_{side}']
            elbow = self.arm_ctrls[f'elbow_{side}']
            
            # Scapula Down (rotateY)
            cmds.setAttr(f"{scapula}.rotateY", self.scapula_down_y)
            self.set_key(scapula, 'rotateY', start, self.scapula_down_y)
            self.set_key(scapula, 'rotateY', end, self.scapula_down_y)



            # Static arm down
            cmds.setAttr(f"{shoulder}.rotateY", self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', start, self.shoulder_down_y)
            self.set_key(shoulder, 'rotateY', end, self.shoulder_down_y)
            
            # Shoulder Rotate (X) on thirds, inverted on the right
            if side == 'l':
                rotX_vals = [self.shoulder_rotate_x, -self.shoulder_rotate_x, self.shoulder_rotate_x]
            else:
                rotX_vals = [-self.shoulder_rotate_x, self.shoulder_rotate_x, -self.shoulder_rotate_x]
            for t, val in zip([start, mid, end], rotX_vals):
                self.set_key(shoulder, 'rotateX', t, val)
            
            # Shoulder Swing (Z) on thirds, inverted on the right
            if side == 'l':
                swingZ_vals = [self.shoulder_swing_z, -self.shoulder_swing_z, self.shoulder_swing_z]
            else:
                swingZ_vals = [-self.shoulder_swing_z, self.shoulder_swing_z, -self.shoulder_swing_z]
            for t, val in zip([start, mid, end], swingZ_vals):
                self.set_key(shoulder, 'rotateZ', t, val)

            
            # Shoulder SwayOut (Y) on quarters
            # inside set_arm_keys(), after your rotateX/rotateZ blocks:
        
            # Shoulder Down base (rotateY)
            for t in (start, mid, end):
                self.set_key(shoulder, 'rotateY', t, self.shoulder_down_y)
        
            # Shoulder SwayOut (Y) on quarters, added to base and mirrored per side
            if side == 'l':
                val_q  = self.shoulder_down_y + self.shoulder_sway_out_y
                val_3q = self.shoulder_down_y - self.shoulder_sway_out_y
            else:
                val_q  = self.shoulder_down_y - self.shoulder_sway_out_y
                val_3q = self.shoulder_down_y + self.shoulder_sway_out_y
        
            self.set_key(shoulder, 'rotateY', quarter,       val_q)
            self.set_key(shoulder, 'rotateY', three_quarter, val_3q)



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
        # list all transform nodes once
        all_nodes = cmds.ls(type='transform')
        name_lower = name.lower()
    
        # 1) exact, case‐insensitive match
        for node in all_nodes:
            if node.lower() == name_lower:
                return node
    
        # 2) explicit alias map fallback
        alias = self.alias_map.get(name_lower)
        if alias and cmds.objExists(alias):
            return alias
    
        # 3) try both the “no-1” and “with-1” variants
        #    splits off the trailing underscore+suffix (e.g. "_M", "_R", "_L")
        m = re.match(r"^(.+?)(?:1)?(_[A-Za-z0-9]+)$", name)
        if m:
            base, suffix = m.group(1), m.group(2)
            for variant in (base + suffix, base + "1" + suffix):
                if cmds.objExists(variant):
                    return variant
    
        # 4) last-ditch: strip any “1_” that might remain
        stripped = name.replace("1_", "_")
        if cmds.objExists(stripped):
            return stripped
    
        # nothing found…
        raise RuntimeError(f"Node not found: {name}")



# ?? To run:
RunCycleGenerator().show()
