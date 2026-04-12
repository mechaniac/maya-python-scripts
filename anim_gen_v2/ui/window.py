"""Unified animation generator window.

Usage in Maya::

    from anim_gen_v2.ui.window import show
    show()
"""

import json

import maya.cmds as cmds

from ..core import engine, presets
from ..layers.walk_primary import WalkPrimary
from ..layers.walk_secondary import WalkSecondary
from ..layers.walk_arms import WalkArms

WINDOW_NAME = 'animGenV2Win'
WINDOW_TITLE = 'Animation Generator v2'

# Axis colour coding (RGB = XYZ)
CLR_X = (0.45, 0.18, 0.18)
CLR_Y = (0.18, 0.45, 0.18)
CLR_Z = (0.18, 0.18, 0.45)

# Slider range presets  (min, max, field_min, field_max)
RNG_AMP   = (-60, 60, -180, 180)   # general rotation amplitude
RNG_TRANS = (-20, 20, -100, 100)   # translation
RNG_OFF   = (-30, 30, -90, 90)     # offset
RNG_ROLL  = (-90, 90, -120, 120)   # foot roll


class AnimGenWindow:

    def __init__(self):
        self.walk_primary = WalkPrimary()
        self.walk_secondary = WalkSecondary()
        self.walk_arms = WalkArms()
        self._fields = {}        # key -> widget handle
        self._plain_fields = set()  # keys using floatField (vs floatSliderGrp)
        self._auto_update = False
        self._mute_cbs = {}      # section_name -> checkBox

    # ──────────────────────────────────────────────
    #  Show
    # ──────────────────────────────────────────────

    def show(self):
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)
        win = cmds.window(WINDOW_NAME, title=WINDOW_TITLE,
                          widthHeight=(600, 780), sizeable=True)
        cmds.scrollLayout(childResizable=True)
        tabs = cmds.tabLayout()

        walk_col = cmds.columnLayout(adjustableColumn=True, parent=tabs)
        self._build_walk_primary(walk_col)
        self._build_walk_secondary(walk_col)
        self._build_walk_arms(walk_col)
        self._build_actions(walk_col)

        cmds.tabLayout(tabs, e=True, tabLabel=[(walk_col, 'Walk Cycle')])
        cmds.showWindow(win)

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _sel(ctrls):
        from ..core import resolver
        nodes = []
        for c in ctrls:
            n = resolver.resolve(c)
            if n and cmds.objExists(n):
                nodes.append(n)
        if nodes:
            cmds.select(nodes, r=True)

    def _slider(self, label, key, default, rng=RNG_AMP, color=None):
        """Create a compact floatSliderGrp and register it."""
        kw = dict(label=label, field=True, value=default,
                  minValue=rng[0], maxValue=rng[1],
                  fieldMinValue=rng[2], fieldMaxValue=rng[3],
                  columnWidth3=(130, 50, 10), adjustableColumn=3,
                  precision=2)
        if color:
            kw['backgroundColor'] = color
        f = cmds.floatSliderGrp(**kw)
        self._fields[key] = f
        return f

    def _nod_range(self, key_front, key_back, def_front, def_back, color=None):
        """Compact Nod row: label + Front field + Back field on one line."""
        bg = dict(backgroundColor=color) if color else {}
        cmds.rowLayout(numberOfColumns=5, columnWidth5=(130, 35, 60, 35, 60),
                       adjustableColumn=5, height=22)
        cmds.text(label='Nod  rZ', align='left', **bg)
        cmds.text(label='Front:', align='right', font='smallPlainLabelFont')
        ff = cmds.floatField(v=def_front, precision=2, width=55)
        cmds.text(label='Back:', align='right', font='smallPlainLabelFont')
        fb = cmds.floatField(v=def_back, precision=2, width=55)
        cmds.setParent('..')
        self._fields[key_front] = ff
        self._fields[key_back] = fb
        self._plain_fields.add(key_front)
        self._plain_fields.add(key_back)

    def _get_val(self, key):
        h = self._fields[key]
        if key in self._plain_fields:
            return cmds.floatField(h, q=True, v=True)
        return cmds.floatSliderGrp(h, q=True, v=True)

    def _set_val(self, key, val):
        h = self._fields[key]
        if key in self._plain_fields:
            cmds.floatField(h, e=True, v=val)
        else:
            cmds.floatSliderGrp(h, e=True, v=val)

    def _set_field_enabled(self, key, enabled):
        h = self._fields[key]
        if key in self._plain_fields:
            cmds.floatField(h, e=True, enable=enabled)
        else:
            cmds.floatSliderGrp(h, e=True, enable=enabled)

    def _section_header(self, label, ctrls, mute_key):
        """Joint header: big label + select button + mute checkbox."""
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 60, 80),
                       adjustableColumn=1, height=24)
        cmds.text(label='  ' + label, align='left', font='boldLabelFont')
        cmds.button(label='Select', height=20, width=50,
                    command=lambda *_, c=list(ctrls): self._sel(c))
        cb = cmds.checkBox(label='Mute', value=False,
                           changeCommand=lambda val, k=mute_key: self._toggle_mute(k, val))
        self._mute_cbs[mute_key] = cb
        cmds.setParent('..')

    def _zero_fields(self, keys):
        for k in keys:
            if k in self._fields:
                self._set_val(k, 0)
        if self._auto_update:
            self._generate()

    def _toggle_mute(self, section, val):
        """Mute/unmute a section by setting all its sliders to 0 or restoring."""
        if val:
            if not hasattr(self, '_muted_vals'):
                self._muted_vals = {}
            self._muted_vals[section] = {}
            for key, fld in self._fields.items():
                if key.startswith(section + '_') or key in self._section_keys.get(section, []):
                    self._muted_vals[section][key] = self._get_val(key)
                    self._set_val(key, 0)
                    self._set_field_enabled(key, False)
        else:
            stored = getattr(self, '_muted_vals', {}).get(section, {})
            for key, val in stored.items():
                if key in self._fields:
                    self._set_val(key, val)
                    self._set_field_enabled(key, True)
        if self._auto_update:
            self._generate()

    # ──────────────────────────────────────────────
    #  Walk Primary section
    # ──────────────────────────────────────────────

    def _build_walk_primary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Primary  (Root / Hips / Legs)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        d = self.walk_primary.DEFAULTS

        # Track which keys belong to which mute section
        if not hasattr(self, '_section_keys'):
            self._section_keys = {}

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        # ── Legs ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Legs', legs, 'legs')
        self._slider('Stride Length', 'stride', d['stride'], RNG_TRANS)
        self._slider('Stride Width', 'stride_width', d['stride_width'], (0, 10, 0, 30))
        self._slider('Stride Height', 'stride_height', d['stride_height'], (0, 20, 0, 50))
        self._slider('Foot Raise', 'foot_raise', d['foot_raise'], (0, 40, 0, 90))
        self._slider('Roll Heel', 'foot_roll_heel', d['foot_roll_heel'], RNG_ROLL)
        self._slider('Roll Toe', 'foot_roll_toe', d['foot_roll_toe'], RNG_ROLL)
        self._section_keys['legs'] = ['stride', 'stride_width', 'stride_height',
                                       'foot_raise', 'foot_roll_heel', 'foot_roll_toe']
        cmds.setParent(col)

        # ── Hip ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Hip', hip, 'hip')
        self._slider('Nod  rZ', 'hip_nod', d['hip_nod'], RNG_AMP, CLR_Z)
        self._slider('Lean  rY', 'hip_lean', d['hip_lean'], RNG_AMP, CLR_Y)
        self._slider('Twist  rX', 'hip_twist', d['hip_twist'], RNG_AMP, CLR_X)
        self._section_keys['hip'] = ['hip_nod', 'hip_lean', 'hip_twist']
        cmds.setParent(col)

        # ── Root ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Root', root, 'root')
        self._slider('Bounce  tX', 'root_bounce', d['root_bounce'], RNG_TRANS, CLR_X)
        self._slider('Bounce Offset', 'bounce_offset', d['bounce_offset'], RNG_OFF, CLR_X)
        self._nod_range('root_nod_front', 'root_nod_back',
                        d['root_nod_front'], d['root_nod_back'], CLR_Z)
        self._slider('Lean  rY', 'root_lean', d['root_lean'], RNG_AMP, CLR_Y)
        self._slider('Twist  rX', 'root_twist', d['root_twist'], RNG_AMP, CLR_X)
        self._slider('Left-Right  tZ', 'root_lr', d['root_lr'], RNG_TRANS, CLR_Z)
        self._slider('Back-Forth  tY', 'root_bf', d['root_bf'], RNG_TRANS, CLR_Y)
        self._section_keys['root'] = ['root_bounce', 'bounce_offset', 'root_nod_front',
                                       'root_nod_back', 'root_lean', 'root_twist',
                                       'root_lr', 'root_bf']
        cmds.setParent(col)

        # Bottom buttons
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 280),
                       adjustableColumn=2, height=26)
        cmds.button(label='Set All to 0', height=22,
                    command=lambda *_: self._zero_fields(
                        list(self.walk_primary.DEFAULTS.keys())))
        cmds.button(label='Select All Primary', height=22,
                    command=lambda *_: self._sel(legs + hip + root))
        cmds.setParent('..')
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Walk Secondary section
    # ──────────────────────────────────────────────

    def _build_walk_secondary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Secondary  (Spine / Chest / Neck / Head)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        part_ctrls = {
            'spine': 'FKSpine_M', 'chest': 'FKChest_M',
            'neck': 'FKNeck_M', 'head': 'FKHead_M',
        }

        for part in ('spine', 'chest', 'neck', 'head'):
            ctrl = [part_ctrls[part]]
            cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                             marginHeight=3, marginWidth=4, collapsable=False)
            self._section_header(part.title(), ctrl, part)

            nod_f = self.walk_secondary._params['{}_nod_front'.format(part)]
            nod_b = self.walk_secondary._params['{}_nod_back'.format(part)]
            lean = self.walk_secondary._params['{}_lean'.format(part)]
            twist = self.walk_secondary._params['{}_twist'.format(part)]

            self._nod_range('{}_nod_front'.format(part),
                            '{}_nod_back'.format(part),
                            nod_f, nod_b, CLR_Z)
            self._slider('Lean  rY', '{}_lean'.format(part), lean, RNG_AMP, CLR_Y)
            self._slider('Twist  rX', '{}_twist'.format(part), twist, RNG_AMP, CLR_X)

            self._section_keys[part] = ['{}_nod_front'.format(part),
                                         '{}_nod_back'.format(part),
                                         '{}_lean'.format(part),
                                         '{}_twist'.format(part)]
            cmds.setParent(col)

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 280),
                       adjustableColumn=2, height=26)
        cmds.button(label='Set All to 0', height=22,
                    command=lambda *_: self._zero_fields(
                        list(self.walk_secondary._params.keys())))
        cmds.button(label='Select All Secondary', height=22,
                    command=lambda *_: self._sel(list(part_ctrls.values())))
        cmds.setParent('..')
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Walk Arms section
    # ──────────────────────────────────────────────

    def _build_walk_arms(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Arms', collapsable=True,
                         marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        sh = ['FKShoulder_R', 'FKShoulder_L']
        sc = ['FKScapula_R', 'FKScapula_L']
        el = ['FKElbow_R', 'FKElbow_L']
        wr = ['FKWrist_R', 'FKWrist_L']
        all_arm = sc + sh + el + wr

        d = self.walk_arms.DEFAULTS

        # ── Shoulder ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Shoulder', sh, 'shoulder')
        self._slider('Droop  rY', 'shoulder_droop', d['shoulder_droop'], RNG_AMP, CLR_Y)
        self._slider('Swing  rZ', 'shoulder_swing', d['shoulder_swing'], RNG_AMP, CLR_Z)
        self._slider('Twist  rX', 'shoulder_twist', d['shoulder_twist'], RNG_AMP, CLR_X)
        self._section_keys['shoulder'] = ['shoulder_droop', 'shoulder_swing', 'shoulder_twist']
        cmds.setParent(col)

        # ── Scapula ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Scapula', sc, 'scapula')
        self._slider('Droop  rY', 'scapula_droop', d['scapula_droop'], RNG_AMP, CLR_Y)
        self._slider('Swing  rZ', 'scapula_swing', d['scapula_swing'], RNG_AMP, CLR_Z)
        self._section_keys['scapula'] = ['scapula_droop', 'scapula_swing']
        cmds.setParent(col)

        # ── Elbow ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Elbow', el, 'elbow')
        self._slider('Bend  rZ', 'elbow_bend', d['elbow_bend'], RNG_AMP, CLR_Z)
        self._section_keys['elbow'] = ['elbow_bend']
        cmds.setParent(col)

        # ── Wrist ──
        cmds.frameLayout(label='', borderVisible=True, borderStyle='etchedIn',
                         marginHeight=3, marginWidth=4, collapsable=False)
        self._section_header('Wrist', wr, 'wrist')
        self._slider('Swing  rZ', 'wrist_swing', d['wrist_swing'], RNG_AMP, CLR_Z)
        self._section_keys['wrist'] = ['wrist_swing']
        cmds.setParent(col)

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(300, 280),
                       adjustableColumn=2, height=26)
        cmds.button(label='Set All to 0', height=22,
                    command=lambda *_: self._zero_fields(
                        list(self.walk_arms.DEFAULTS.keys())))
        cmds.button(label='Select All Arms', height=22,
                    command=lambda *_: self._sel(all_arm))
        cmds.setParent('..')
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Actions
    # ──────────────────────────────────────────────

    def _build_actions(self, parent):
        cmds.setParent(parent)
        cmds.separator(height=10, style='in')

        cmds.rowLayout(numberOfColumns=4, columnWidth4=(200, 150, 150, 100),
                       adjustableColumn=1)
        cmds.button(label='Generate Walk Cycle', height=36,
                    command=lambda *_: self._generate())
        cmds.button(label='Delete Animation', height=36,
                    command=lambda *_: self._delete_anim())
        cmds.button(label='Select All Controls', height=36,
                    command=lambda *_: self._sel_all())
        cmds.checkBox(label='Auto', value=False,
                      changeCommand=lambda val: self._toggle_auto(val))
        cmds.setParent('..')

        cmds.separator(height=6, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(280, 150, 150),
                       adjustableColumn=1)
        self._preset_menu = cmds.optionMenu(label='Preset:', changeCommand=lambda *_: None)
        self._refresh_preset_list()
        cmds.button(label='Load Selected',
                    command=lambda *_: self._load_selected_preset())
        cmds.button(label='Print Settings',
                    command=lambda *_: self._print_settings())
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=4, columnWidth4=(150, 150, 150, 150),
                       adjustableColumn=4)
        cmds.button(label='Save to Library',
                    command=lambda *_: self._save_to_library())
        cmds.button(label='Save to Project',
                    command=lambda *_: self._save_to_project())
        cmds.button(label='Save As...',
                    command=lambda *_: self._save_preset_browse())
        cmds.button(label='Load File...',
                    command=lambda *_: self._load_preset_browse())
        cmds.setParent('..')

    # ──────────────────────────────────────────────
    #  Callbacks
    # ──────────────────────────────────────────────

    def _read_fields(self):
        for key in self._fields:
            val = self._get_val(key)
            if key in self.walk_primary.DEFAULTS:
                self.walk_primary._params[key] = val
            elif key in self.walk_secondary._params:
                self.walk_secondary._params[key] = val
            elif key in self.walk_arms.DEFAULTS:
                self.walk_arms._params[key] = val

    def _delete_anim(self):
        all_ctrls = set()
        fkik_ctrls = set()
        for layer in (self.walk_primary, self.walk_secondary, self.walk_arms):
            all_ctrls.update(layer.controls())
            fkik_ctrls.update(layer.fkik_state().keys())
        cmds.undoInfo(openChunk=True, chunkName='AnimGenV2_delete')
        try:
            engine.clear_keys(list(all_ctrls))
            engine.clear_keys(list(fkik_ctrls), attrs=['FKIKBlend'])
        finally:
            cmds.undoInfo(closeChunk=True)

    def _generate(self):
        self._read_fields()
        engine.generate([self.walk_primary,
                         self.walk_secondary,
                         self.walk_arms])

    def _sel_all(self):
        all_ctrls = (self.walk_primary.controls()
                     + self.walk_secondary.controls()
                     + self.walk_arms.controls())
        self._sel(all_ctrls)

    def _toggle_auto(self, val):
        self._auto_update = val
        cb = (lambda *_: self._generate()) if val else (lambda *_: None)
        for key, f in self._fields.items():
            try:
                if key in self._plain_fields:
                    cmds.floatField(f, e=True, changeCommand=cb)
                else:
                    cmds.floatSliderGrp(f, e=True, changeCommand=cb,
                                        dragCommand=cb)
            except Exception:
                pass

    def _all_params(self):
        self._read_fields()
        return {
            'primary': self.walk_primary.params(),
            'secondary': self.walk_secondary.params(),
            'arms': self.walk_arms.params(),
        }

    # ── preset callbacks ──

    def _refresh_preset_list(self):
        existing = cmds.optionMenu(self._preset_menu, q=True, ill=True) or []
        for item in existing:
            cmds.deleteUI(item)
        self._preset_entries = presets.list_presets('walk')
        for entry in self._preset_entries:
            tag = '[lib]' if entry['source'] == 'library' else '[proj]'
            cmds.menuItem(label='{} {}'.format(tag, entry['name']),
                          parent=self._preset_menu)
        if not self._preset_entries:
            cmds.menuItem(label='(no presets found)', parent=self._preset_menu)

    def _load_selected_preset(self):
        if not self._preset_entries:
            return
        idx = cmds.optionMenu(self._preset_menu, q=True, sl=True) - 1
        if idx < 0 or idx >= len(self._preset_entries):
            return
        data = presets.load(self._preset_entries[idx]['path'])
        self._apply_preset_data(data)

    def _prompt_name(self, title='Preset Name'):
        result = cmds.promptDialog(title=title, message='Preset name:',
                                   button=['OK', 'Cancel'],
                                   defaultButton='OK',
                                   cancelButton='Cancel',
                                   dismissString='Cancel')
        if result != 'OK':
            return None
        name = cmds.promptDialog(q=True, text=True).strip()
        return name if name else None

    def _save_to_library(self):
        name = self._prompt_name('Save to Library')
        if not name:
            return
        path = presets.save_to_library(self._all_params(), name)
        if path:
            print('// Saved to library: {}'.format(path))
            self._refresh_preset_list()

    def _save_to_project(self):
        name = self._prompt_name('Save to Project')
        if not name:
            return
        path = presets.save_to_project(self._all_params(), name)
        if path:
            print('// Saved to project: {}'.format(path))
            self._refresh_preset_list()

    def _save_preset_browse(self):
        presets.browse_save(self._all_params())

    def _load_preset_browse(self):
        data = presets.browse_load()
        if not data:
            return
        self._apply_preset_data(data)

    def _apply_preset_data(self, data):
        if 'primary' in data:
            self.walk_primary.set_params(data['primary'])
        if 'secondary' in data:
            self.walk_secondary.set_params(data['secondary'])
        if 'arms' in data:
            self.walk_arms.set_params(data['arms'])
        self._refresh_fields()

    def _refresh_fields(self):
        all_p = {}
        all_p.update(self.walk_primary._params)
        all_p.update(self.walk_secondary._params)
        all_p.update(self.walk_arms._params)
        for key in self._fields:
            if key in all_p:
                try:
                    self._set_val(key, all_p[key])
                except Exception:
                    pass

    def _print_settings(self):
        data = self._all_params()
        print('// AnimGenV2 Settings:\n' + json.dumps(data, indent=2))


# ── module-level convenience ──

def show():
    """Create and show the animation generator window."""
    win = AnimGenWindow()
    win.show()
    return win
