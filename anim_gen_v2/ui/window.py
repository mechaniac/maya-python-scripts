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
from .range_slider import (RangeSlider, SingleSlider,
                           embed_in_layout, embed_single_in_layout)

import maya.OpenMayaUI as omui
from shiboken6 import wrapInstance
from PySide6 import QtWidgets

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
        self._fields = {}        # key -> floatField handle (cmds)
        self._range_sliders = {}  # (key_lo, key_hi) -> RangeSlider widget
        self._range_keys = {}     # key -> (RangeSlider, 'low'|'high')
        self._single_keys = {}   # key -> SingleSlider widget
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

    @staticmethod
    def _tint_label(widget, color):
        """Set the font colour of a cmds.text widget via Qt."""
        if not color:
            return
        r, g, b = [min(int(c * 255) + 120, 235) for c in color]
        ptr = omui.MQtUtil.findControl(widget)
        if ptr:
            qt_w = wrapInstance(int(ptr), QtWidgets.QWidget)
            qt_w.setStyleSheet('color: rgb({},{},{});'.format(r, g, b))

    def _slider(self, label, key, default, rng=RNG_AMP, color=None):
        """Compact slider row: label [field] ═══slider═══."""
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label=label, width=130, align='right')
        self._tint_label(lbl, color)
        fld = cmds.floatField(v=default, precision=2, width=50,
                              minValue=rng[2], maxValue=rng[3])
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 2), (lbl, 'bottom', 2),
                        (fld, 'top', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (holder, 'right', 0)],
            attachNone=[(lbl, 'right'), (fld, 'right')],
            attachControl=[(fld, 'left', 4, lbl),
                           (holder, 'left', 2, fld)])
        sl = embed_single_in_layout(holder, minimum=rng[0], maximum=rng[1],
                                    value=default, color=color)

        def _slider_changed(v):
            cmds.floatField(fld, e=True, v=v)
            if self._auto_update:
                self._generate()

        def _field_changed(v):
            sl.setValue(v)
            if self._auto_update:
                self._generate()

        sl.valueChanged.connect(_slider_changed)
        cmds.floatField(fld, e=True, changeCommand=_field_changed)
        cmds.setParent('..')
        self._fields[key] = fld
        self._single_keys[key] = sl

    def _range_slider(self, label, key_lo, key_hi, def_lo, def_hi,
                      rng=RNG_AMP, color=None):
        """Compact range row: label [lo field] ═══slider═══ [hi field]."""
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label=label, width=130, align='right')
        self._tint_label(lbl, color)
        f_lo = cmds.floatField(v=def_lo, precision=2, width=50,
                               minValue=rng[2], maxValue=rng[3])
        # placeholder for the Qt slider
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        f_hi = cmds.floatField(v=def_hi, precision=2, width=50,
                               minValue=rng[2], maxValue=rng[3])
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 2), (lbl, 'bottom', 2),
                        (f_lo, 'top', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (f_hi, 'top', 0), (f_hi, 'right', 0)],
            attachNone=[(lbl, 'right'), (f_lo, 'right'), (f_hi, 'left')],
            attachControl=[(f_lo, 'left', 4, lbl),
                           (holder, 'left', 2, f_lo),
                           (holder, 'right', 2, f_hi)])

        # embed Qt range slider into the cmds holder layout
        sl = embed_in_layout(holder, minimum=rng[0], maximum=rng[1],
                             low=def_lo, high=def_hi, color=color)

        # bidirectional sync
        def _slider_changed(lo, hi):
            cmds.floatField(f_lo, e=True, v=lo)
            cmds.floatField(f_hi, e=True, v=hi)
            if self._auto_update:
                self._generate()

        def _lo_field_changed(val):
            sl.setLow(val)
            if self._auto_update:
                self._generate()

        def _hi_field_changed(val):
            sl.setHigh(val)
            if self._auto_update:
                self._generate()

        sl.rangeChanged.connect(_slider_changed)
        cmds.floatField(f_lo, e=True, changeCommand=_lo_field_changed)
        cmds.floatField(f_hi, e=True, changeCommand=_hi_field_changed)

        # highlight active field while dragging
        _HL = (0.35, 0.35, 0.40)   # subtle highlight bg
        def _lo_bg():
            return cmds.floatField(f_lo, q=True, backgroundColor=True)
        def _hi_bg():
            return cmds.floatField(f_hi, q=True, backgroundColor=True)
        _default_bg = [None, None]  # [lo, hi] captured on first use

        def _handle_changed(which):
            if _default_bg[0] is None:
                _default_bg[0] = _lo_bg()
                _default_bg[1] = _hi_bg()
            if which == 'low':
                cmds.floatField(f_lo, e=True, backgroundColor=_HL)
                cmds.floatField(f_hi, e=True, backgroundColor=_default_bg[1])
            elif which == 'high':
                cmds.floatField(f_hi, e=True, backgroundColor=_HL)
                cmds.floatField(f_lo, e=True, backgroundColor=_default_bg[0])
            else:
                cmds.floatField(f_lo, e=True, backgroundColor=_default_bg[0])
                cmds.floatField(f_hi, e=True, backgroundColor=_default_bg[1])

        sl.handleChanged.connect(_handle_changed)

        cmds.setParent('..')
        self._fields[key_lo] = f_lo
        self._fields[key_hi] = f_hi
        self._range_keys[key_lo] = (sl, 'low')
        self._range_keys[key_hi] = (sl, 'high')
        self._range_sliders[(key_lo, key_hi)] = sl

    def _get_val(self, key):
        if key in self._range_keys:
            sl, which = self._range_keys[key]
            lo, hi = sl.value()
            return lo if which == 'low' else hi
        if key in self._single_keys:
            return self._single_keys[key].value()
        return cmds.floatSliderGrp(self._fields[key], q=True, v=True)

    def _set_val(self, key, val):
        if key in self._range_keys:
            sl, which = self._range_keys[key]
            if which == 'low':
                sl.setLow(val)
            else:
                sl.setHigh(val)
            cmds.floatField(self._fields[key], e=True, v=val)
        elif key in self._single_keys:
            self._single_keys[key].setValue(val)
            cmds.floatField(self._fields[key], e=True, v=val)
        else:
            cmds.floatSliderGrp(self._fields[key], e=True, v=val)

    def _set_field_enabled(self, key, enabled):
        if key in self._range_keys:
            sl, _ = self._range_keys[key]
            sl.setEnabled(enabled)
            cmds.floatField(self._fields[key], e=True, enable=enabled)
        elif key in self._single_keys:
            self._single_keys[key].setEnabled(enabled)
            cmds.floatField(self._fields[key], e=True, enable=enabled)
        else:
            cmds.floatSliderGrp(self._fields[key], e=True, enable=enabled)

    def _category_header(self, label, all_ctrls, reset_keys, mute_sections):
        """Category-level header: label + Reset + Select Controls + Mute."""
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(200, 60, 110, 60),
                       adjustableColumn=1, height=26)
        cmds.text(label='  ' + label, align='left', font='boldLabelFont')
        cmds.button(label='Reset', height=20, width=55,
                    command=lambda *_: self._zero_fields(reset_keys))
        cmds.button(label='Select Controls', height=20, width=105,
                    command=lambda *_, c=list(all_ctrls): self._sel(c))
        cb = cmds.checkBox(label='Mute', value=False,
                           changeCommand=lambda val, s=list(mute_sections):
                               self._toggle_mute_category(s, val))
        cmds.setParent('..')

    def _section_header(self, label, ctrls, mute_key):
        """Sub-section header: label + select button + mute checkbox."""
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

    def _slider_pair(self, label_a, key_a, def_a, label_b, key_b, def_b,
                     rng=RNG_AMP, color_a=None, color_b=None):
        """Two sliders side by side, each getting 50 % of the width."""
        form = cmds.formLayout(height=22)
        cmds.setParent(form)
        self._slider(label_a, key_a, def_a, rng, color_a)
        sl_a = self._fields[key_a]          # floatField just registered
        # the formLayout wrapping sl_a is its direct parent
        frm_a = cmds.floatField(sl_a, q=True, parent=True)
        cmds.setParent(form)
        self._slider(label_b, key_b, def_b, rng, color_b)
        sl_b = self._fields[key_b]
        frm_b = cmds.floatField(sl_b, q=True, parent=True)
        cmds.formLayout(form, e=True,
            attachForm=[(frm_a, 'left', 0), (frm_a, 'top', 0),
                        (frm_a, 'bottom', 0),
                        (frm_b, 'right', 0), (frm_b, 'top', 0),
                        (frm_b, 'bottom', 0)],
            attachPosition=[(frm_a, 'right', 2, 50),
                            (frm_b, 'left', 2, 50)])
        cmds.setParent('..')

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

    def _toggle_mute_category(self, sections, val):
        """Mute/unmute all sub-sections of a category at once."""
        for s in sections:
            cb = self._mute_cbs.get(s)
            if cb:
                cmds.checkBox(cb, e=True, value=val)
            self._toggle_mute(s, val)

    # ──────────────────────────────────────────────
    #  Walk Primary section
    # ──────────────────────────────────────────────

    def _build_walk_primary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Primary  (Root / Hips / Legs)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        d = self.walk_primary.DEFAULTS

        if not hasattr(self, '_section_keys'):
            self._section_keys = {}

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        self._category_header('Primary', legs + hip + root,
                              list(d.keys()), ['legs', 'hip', 'root'])

        # ── Legs ──
        cmds.separator(height=6, style='none')
        self._section_header('Legs', legs, 'legs')
        self._slider('Stride Length', 'stride', d['stride'], (0, 40, 0, 300))
        self._slider_pair('Stride Width', 'stride_width', d['stride_width'],
                          'Stride Height', 'stride_height', d['stride_height'],
                          (0, 20, 0, 50))
        self._slider('Foot Raise', 'foot_raise', d['foot_raise'], (0, 40, 0, 90))
        self._slider_pair('Roll Heel', 'foot_roll_heel', d['foot_roll_heel'],
                          'Roll Toe', 'foot_roll_toe', d['foot_roll_toe'],
                          RNG_ROLL)
        self._section_keys['legs'] = ['stride', 'stride_width', 'stride_height',
                                       'foot_raise', 'foot_roll_heel', 'foot_roll_toe']

        # ── Hip ──
        cmds.separator(height=4, style='in')
        self._section_header('Hip', hip, 'hip')
        self._range_slider('Nod  rZ', 'hip_nod_back', 'hip_nod_front',
                           d['hip_nod_back'], d['hip_nod_front'], RNG_AMP, CLR_Z)
        self._slider_pair('Lean  rY', 'hip_lean', d['hip_lean'],
                          'Twist  rX', 'hip_twist', d['hip_twist'],
                          RNG_AMP, CLR_Y, CLR_X)
        self._section_keys['hip'] = ['hip_nod_front', 'hip_nod_back',
                                      'hip_lean', 'hip_twist']

        # ── Root ──
        cmds.separator(height=4, style='in')
        self._section_header('Root', root, 'root')
        self._range_slider('Bounce  tX', 'root_bounce_lo', 'root_bounce_hi',
                           d['root_bounce_lo'], d['root_bounce_hi'], RNG_TRANS, CLR_X)
        self._range_slider('Nod  rZ', 'root_nod_back', 'root_nod_front',
                           d['root_nod_back'], d['root_nod_front'], RNG_AMP, CLR_Z)
        self._slider_pair('Lean  rY', 'root_lean', d['root_lean'],
                          'Twist  rX', 'root_twist', d['root_twist'],
                          RNG_AMP, CLR_Y, CLR_X)
        self._slider_pair('Left-Right  tZ', 'root_lr', d['root_lr'],
                          'Back-Forth  tY', 'root_bf', d['root_bf'],
                          RNG_TRANS, CLR_Z, CLR_Y)
        self._section_keys['root'] = ['root_bounce_lo', 'root_bounce_hi',
                                       'root_nod_front', 'root_nod_back',
                                       'root_lean', 'root_twist',
                                       'root_lr', 'root_bf']
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

        self._category_header('Secondary', list(part_ctrls.values()),
                              list(self.walk_secondary._params.keys()),
                              list(part_ctrls.keys()))

        for part in ('spine', 'chest', 'neck', 'head'):
            ctrl = [part_ctrls[part]]
            cmds.separator(height=4, style='in')
            self._section_header(part.title(), ctrl, part)

            nod_f = self.walk_secondary._params['{}_nod_front'.format(part)]
            nod_b = self.walk_secondary._params['{}_nod_back'.format(part)]
            lean = self.walk_secondary._params['{}_lean'.format(part)]
            twist = self.walk_secondary._params['{}_twist'.format(part)]

            self._range_slider('Nod  rZ', '{}_nod_back'.format(part),
                               '{}_nod_front'.format(part),
                               nod_b, nod_f, RNG_AMP, CLR_Z)
            self._slider_pair('Lean  rY', '{}_lean'.format(part), lean,
                              'Twist  rX', '{}_twist'.format(part), twist,
                              RNG_AMP, CLR_Y, CLR_X)

            self._section_keys[part] = ['{}_nod_front'.format(part),
                                         '{}_nod_back'.format(part),
                                         '{}_lean'.format(part),
                                         '{}_twist'.format(part)]

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

        self._category_header('Arms', all_arm,
                              list(d.keys()),
                              ['shoulder', 'scapula', 'elbow', 'wrist'])

        # ── Shoulder ──
        cmds.separator(height=6, style='none')
        self._section_header('Shoulder', sh, 'shoulder')
        self._range_slider('Swing  rZ', 'shoulder_swing_back', 'shoulder_swing_front',
                           d['shoulder_swing_back'], d['shoulder_swing_front'],
                           RNG_AMP, CLR_Z)
        self._slider_pair('Droop  rY', 'shoulder_droop', d['shoulder_droop'],
                          'Twist  rX', 'shoulder_twist', d['shoulder_twist'],
                          RNG_AMP, CLR_Y, CLR_X)
        self._section_keys['shoulder'] = ['shoulder_swing_front', 'shoulder_swing_back',
                                           'shoulder_droop', 'shoulder_twist']

        # ── Scapula ──
        cmds.separator(height=4, style='in')
        self._section_header('Scapula', sc, 'scapula')
        self._slider('Droop  rY', 'scapula_droop', d['scapula_droop'], RNG_AMP, CLR_Y)
        self._range_slider('Swing  rZ', 'scapula_swing_back', 'scapula_swing_front',
                           d['scapula_swing_back'], d['scapula_swing_front'],
                           RNG_AMP, CLR_Z)
        self._section_keys['scapula'] = ['scapula_droop', 'scapula_swing_front',
                                          'scapula_swing_back']

        # ── Elbow ──
        cmds.separator(height=4, style='in')
        self._section_header('Elbow', el, 'elbow')
        self._range_slider('Bend  rZ', 'elbow_bend_lo', 'elbow_bend_hi',
                           d['elbow_bend_lo'], d['elbow_bend_hi'], RNG_AMP, CLR_Z)
        self._section_keys['elbow'] = ['elbow_bend_lo', 'elbow_bend_hi']

        # ── Wrist ──
        cmds.separator(height=4, style='in')
        self._section_header('Wrist', wr, 'wrist')
        self._range_slider('Swing  rZ', 'wrist_swing_back', 'wrist_swing_front',
                           d['wrist_swing_back'], d['wrist_swing_front'],
                           RNG_AMP, CLR_Z)
        self._section_keys['wrist'] = ['wrist_swing_front', 'wrist_swing_back']

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
                    backgroundColor=(0.22, 0.55, 0.22),
                    command=lambda *_: self._generate())
        cmds.button(label='Delete Animation', height=36,
                    backgroundColor=(0.55, 0.22, 0.22),
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
        # Single and range sliders already fire callbacks that check
        # self._auto_update, so nothing extra is needed here.

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
