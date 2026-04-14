"""Unified animation generator window.

Usage in Maya::

    from anim_gen_v2.ui.window import show
    show()
"""

import json
import os

import maya.cmds as cmds

from ..core import engine, presets
from ..layers.walk_primary import WalkPrimary
from ..layers.run_primary import RunPrimary
from ..layers.sidestep_primary import SidestepPrimary
from ..layers.walk_secondary import WalkSecondary
from ..layers.walk_arms import WalkArms
from .range_slider import (RangeSlider, SingleSlider,
                           embed_in_layout, embed_single_in_layout)

import maya.OpenMayaUI as omui
from shiboken6 import wrapInstance
from PySide6 import QtWidgets, QtGui, QtCore

WINDOW_NAME = 'animGenV2Win'
WINDOW_TITLE = 'Animation Generator v2'

# Absolute path to the single source of truth for slider ranges.
_SETTINGS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'settings.json')

# Axis colour coding (RGB = XYZ)
CLR_X = (0.45, 0.18, 0.18)
CLR_Y = (0.18, 0.45, 0.18)
CLR_Z = (0.18, 0.18, 0.45)

# Dim yellow for Select buttons
CLR_SELECT_BTN = (0.45, 0.42, 0.22)

# Yellow for Scale slider
CLR_SCALE = (0.55, 0.50, 0.15)

# Subtle tints for Library vs Project presets
CLR_LIB  = (0.25, 0.38, 0.55)   # distinct blue
CLR_PROJ = (0.55, 0.38, 0.18)   # distinct orange

# Range category labels for the settings editor
_RANGE_LABELS = {
    'rotation':    'Rotation (nod, lean)',
    'translation': 'Translation (bounce, LR, BF)',
    'roll':        'Foot Roll',
    'stride':      'Stride Length',
    'stride_wh':   'Stride Width',
    'stride_h':    'Stride Height',
    'foot_raise':  'Foot Raise',
    'swing':       'Arm Swing',
    'droop':       'Arm Droop',
    'twist':       'Twist (all rX)',
    'elbow_bend':  'Elbow Bend',
}


class AnimGenWindow:

    def __init__(self):
        self.walk_primary = WalkPrimary()
        self.run_primary = RunPrimary()
        self.sidestep_primary = SidestepPrimary()
        self.walk_secondary = WalkSecondary()
        self.walk_arms = WalkArms()
        self._active_clip = 'walk'   # 'walk', 'run', or 'sidestep'
        self._fields = {}        # key -> floatField handle (cmds)
        self._range_sliders = {}  # (key_lo, key_hi) -> RangeSlider widget
        self._range_keys = {}     # key -> (RangeSlider, 'low'|'high')
        self._single_keys = {}   # key -> SingleSlider widget
        self._auto_update = False
        self._mute_cbs = {}      # section_name -> checkBox
        self._ranges = self._load_ranges()
        self._section_keys = {}  # section_name -> [keys]
        self._current_section = None

    @staticmethod
    def _load_ranges():
        """Read ranges from settings.json — the only source of truth."""
        print('// AnimGenV2: reading ranges from {}'.format(_SETTINGS_JSON))
        with open(_SETTINGS_JSON, 'r') as f:
            data = json.load(f)['ranges']
        print('// AnimGenV2: loaded ranges = {}'.format(data))
        return data

    def _rng(self, name):
        """Return (min, max) for a range category."""
        return tuple(self._ranges[name])

    # ──────────────────────────────────────────────
    #  Show
    # ──────────────────────────────────────────────

    def show(self):
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)
        span = (cmds.playbackOptions(q=True, max=True)
                - cmds.playbackOptions(q=True, min=True))
        self._off_half = max(1, int(span / 2))
        self._off_quarter = max(1, int(span / 4))
        win = cmds.window(WINDOW_NAME, title=WINDOW_TITLE,
                          widthHeight=(600, 780), sizeable=True)

        # Root form: scrollable sliders on top, fixed actions at bottom
        root_form = cmds.formLayout()

        # ── Scrollable area (sliders / settings) ──
        scroll = cmds.scrollLayout(childResizable=True)
        main_col = cmds.columnLayout(adjustableColumn=True)

        # ── Clip type tabs (Primary section only per type) ──
        self._clip_tabs = cmds.tabLayout(
            changeCommand=lambda: self._on_tab_changed())
        walk_col = cmds.columnLayout(adjustableColumn=True,
                                     parent=self._clip_tabs)
        self._build_walk_primary(walk_col)
        cmds.setParent(self._clip_tabs)
        run_col = cmds.columnLayout(adjustableColumn=True,
                                    parent=self._clip_tabs)
        self._build_run_primary(run_col)
        cmds.setParent(self._clip_tabs)
        ss_col = cmds.columnLayout(adjustableColumn=True,
                                   parent=self._clip_tabs)
        self._build_sidestep_primary(ss_col)
        cmds.setParent(self._clip_tabs)
        cmds.tabLayout(self._clip_tabs, e=True,
                       tabLabel=[(walk_col, 'Walk Cycle'),
                                 (run_col, 'Run Cycle'),
                                 (ss_col, 'Strafe')])
        cmds.setParent(main_col)

        # ── Shared sections (Secondary + Arms + Range) ──
        self._build_walk_secondary(main_col)
        self._build_walk_arms(main_col)
        self._build_range_settings(main_col)
        cmds.setParent(root_form)

        # ── Fixed bottom panel (actions + presets) ──
        bottom = cmds.columnLayout(adjustableColumn=True)
        self._build_actions(bottom)
        cmds.setParent(root_form)

        cmds.formLayout(root_form, e=True,
            attachForm=[(scroll, 'top', 0), (scroll, 'left', 0),
                        (scroll, 'right', 0),
                        (bottom, 'left', 0), (bottom, 'right', 0),
                        (bottom, 'bottom', 0)],
            attachControl=[(scroll, 'bottom', 0, bottom)],
            attachNone=[(bottom, 'top')])

        cmds.showWindow(win)

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────

    @property
    def _active_primary(self):
        """Return the primary layer for the currently selected clip type."""
        if self._active_clip == 'run':
            return self.run_primary
        if self._active_clip == 'sidestep':
            return self.sidestep_primary
        return self.walk_primary

    def _on_tab_changed(self):
        """Called when the user switches between Walk / Run / Sidestep tabs."""
        idx = cmds.tabLayout(self._clip_tabs, q=True, selectTabIndex=True)
        if idx == 3:
            self._active_clip = 'sidestep'
        elif idx == 2:
            self._active_clip = 'run'
        else:
            self._active_clip = 'walk'
        self._refresh_preset_list()

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
    def _style_field_zero(fld):
        """Dim field text when value is 0, normal otherwise."""
        v = cmds.floatField(fld, q=True, v=True)
        ptr = omui.MQtUtil.findControl(fld)
        if ptr:
            qt_w = wrapInstance(int(ptr), QtWidgets.QWidget)
            if v == 0.0:
                qt_w.setStyleSheet('color: rgb(90,90,90);')
            else:
                qt_w.setStyleSheet('')

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

    def _slider(self, label, key, default, rng=None, color=None, tip=''):
        """Compact slider row: label [field] ═══slider═══."""
        if rng is None:
            rng = self._rng('rotation')
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label=label, width=130, align='right',
                        annotation=tip)
        self._tint_label(lbl, color)
        fld = cmds.floatField(v=default, precision=2, width=50,
                              minValue=rng[0], maxValue=rng[1],
                              annotation=tip)
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 0), (lbl, 'bottom', 0),
                        (fld, 'top', 0), (fld, 'bottom', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (holder, 'right', 0)],
            attachNone=[(lbl, 'right'), (fld, 'right')],
            attachControl=[(fld, 'left', 4, lbl),
                           (holder, 'left', 2, fld)])
        sl = embed_single_in_layout(holder, minimum=rng[0], maximum=rng[1],
                                    value=default, color=color)
        if tip:
            sl.setToolTip(tip)

        def _slider_changed(v):
            cmds.floatField(fld, e=True, v=v)
            self._style_field_zero(fld)
            if self._auto_update:
                self._generate()

        def _field_changed(v):
            sl.setValue(v)
            self._style_field_zero(fld)
            if self._auto_update:
                self._generate()

        sl.valueChanged.connect(_slider_changed)
        cmds.floatField(fld, e=True, changeCommand=_field_changed)
        self._style_field_zero(fld)
        cmds.setParent('..')
        self._fields[key] = fld
        self._single_keys[key] = sl
        if self._current_section is not None:
            self._section_keys[self._current_section].append(key)

    def _range_slider(self, label, key_lo, key_hi, def_lo, def_hi,
                      rng=None, color=None, tip=''):
        """Compact range row: label [lo field] ═══slider═══ [hi field]."""
        if rng is None:
            rng = self._rng('rotation')
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label=label, width=130, align='right',
                        annotation=tip)
        self._tint_label(lbl, color)
        f_lo = cmds.floatField(v=def_lo, precision=2, width=50,
                               minValue=rng[0], maxValue=rng[1],
                               annotation=tip)
        # placeholder for the Qt slider
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        f_hi = cmds.floatField(v=def_hi, precision=2, width=50,
                               minValue=rng[0], maxValue=rng[1],
                               annotation=tip)
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 0), (lbl, 'bottom', 0),
                        (f_lo, 'top', 0), (f_lo, 'bottom', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (f_hi, 'top', 0), (f_hi, 'bottom', 0),
                        (f_hi, 'right', 0)],
            attachNone=[(lbl, 'right'), (f_lo, 'right'), (f_hi, 'left')],
            attachControl=[(f_lo, 'left', 4, lbl),
                           (holder, 'left', 2, f_lo),
                           (holder, 'right', 2, f_hi)])

        # embed Qt range slider into the cmds holder layout
        sl = embed_in_layout(holder, minimum=rng[0], maximum=rng[1],
                             low=def_lo, high=def_hi, color=color)
        if tip:
            sl.setToolTip(tip)

        # bidirectional sync
        def _slider_changed(lo, hi):
            cmds.floatField(f_lo, e=True, v=lo)
            cmds.floatField(f_hi, e=True, v=hi)
            self._style_field_zero(f_lo)
            self._style_field_zero(f_hi)
            if self._auto_update:
                self._generate()

        def _lo_field_changed(val):
            sl.setLow(val)
            self._style_field_zero(f_lo)
            if self._auto_update:
                self._generate()

        def _hi_field_changed(val):
            sl.setHigh(val)
            self._style_field_zero(f_hi)
            if self._auto_update:
                self._generate()

        sl.rangeChanged.connect(_slider_changed)
        cmds.floatField(f_lo, e=True, changeCommand=_lo_field_changed)
        cmds.floatField(f_hi, e=True, changeCommand=_hi_field_changed)
        self._style_field_zero(f_lo)
        self._style_field_zero(f_hi)

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
        if self._current_section is not None:
            self._section_keys[self._current_section].extend([key_lo, key_hi])

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
        if key in self._fields:
            self._style_field_zero(self._fields[key])

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
                    annotation='Reset all sliders in this category to zero',
                    command=lambda *_: self._zero_fields(reset_keys))
        cmds.button(label='Select Controls', height=20, width=105,
                    backgroundColor=CLR_SELECT_BTN,
                    annotation='Select all rig controls belonging to this category',
                    command=lambda *_, c=list(all_ctrls): self._sel(c))
        cb = cmds.checkBox(label='Mute', value=False,
                           annotation='Mute all sections: store current values, set to zero, and disable sliders',
                           changeCommand=lambda val, s=list(mute_sections):
                               self._toggle_mute_category(s, val))
        cmds.setParent('..')

    def _section_header(self, label, ctrls, mute_key):
        """Sub-section header: label + select button + mute checkbox."""
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 60, 80),
                       adjustableColumn=1, height=24)
        cmds.text(label='  ' + label, align='left', font='boldLabelFont')
        cmds.button(label='Select', height=20, width=50,
                    backgroundColor=CLR_SELECT_BTN,
                    annotation='Select the {} rig controls in the viewport'.format(label),
                    command=lambda *_, c=list(ctrls): self._sel(c))
        cb = cmds.checkBox(label='Mute', value=False,
                           annotation='Mute {}: store values, zero out, and disable sliders'.format(label),
                           changeCommand=lambda val, k=mute_key: self._toggle_mute(k, val))
        self._mute_cbs[mute_key] = cb
        self._current_section = mute_key
        self._section_keys.setdefault(mute_key, [])
        cmds.setParent('..')

    def _zero_fields(self, keys):
        for k in keys:
            if k in self._fields:
                self._set_val(k, 0)
        if self._auto_update:
            self._generate()

    def _slider_pair(self, label_a, key_a, def_a, label_b, key_b, def_b,
                     rng=None, color_a=None, color_b=None,
                     tip_a='', tip_b='', rng_b=None):
        """Two sliders side by side, each getting 50 % of the width."""
        if rng is None:
            rng = self._rng('rotation')
        rng_actual_b = rng_b if rng_b is not None else rng
        form = cmds.formLayout(height=22)
        cmds.setParent(form)
        self._slider(label_a, key_a, def_a, rng, color_a, tip=tip_a)
        sl_a = self._fields[key_a]          # floatField just registered
        # the formLayout wrapping sl_a is its direct parent
        frm_a = cmds.floatField(sl_a, q=True, parent=True)
        cmds.setParent(form)
        self._slider(label_b, key_b, def_b, rng_actual_b, color_b, tip=tip_b)
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

    def _offset_slider(self, key, max_off):
        """Integer offset slider row for shifting curves in time."""
        tip = ('Shift this section\u2019s animation curves forward or backward '
               'in time (frames). Extended keys keep the cycle seamless.')
        mn, mx = -max_off, max_off
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label='Offset', width=130, align='right',
                        annotation=tip)
        fld = cmds.floatField(v=0, precision=0, width=50,
                              minValue=mn, maxValue=mx,
                              annotation=tip)
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 0), (lbl, 'bottom', 0),
                        (fld, 'top', 0), (fld, 'bottom', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (holder, 'right', 0)],
            attachNone=[(lbl, 'right'), (fld, 'right')],
            attachControl=[(fld, 'left', 4, lbl),
                           (holder, 'left', 2, fld)])
        sl = embed_single_in_layout(holder, minimum=mn, maximum=mx,
                                    value=0, color=None, snap_int=True)
        sl.setToolTip(tip)

        def _slider_changed(v):
            cmds.floatField(fld, e=True, v=round(v))
            if self._auto_update:
                self._generate()

        def _field_changed(v):
            v = round(v)
            sl.setValue(v)
            if self._auto_update:
                self._generate()

        sl.valueChanged.connect(_slider_changed)
        cmds.floatField(fld, e=True, changeCommand=_field_changed)
        cmds.setParent('..')
        self._fields[key] = fld
        self._single_keys[key] = sl
        if self._current_section is not None:
            self._section_keys[self._current_section].append(key)

    def _scalar_row(self, sections):
        """Scale slider (0-10, default 1) + Apply button for an entire region."""
        tip = ('Multiply all values in this region by the scale factor.\n'
               '1.0 = no change, 0.5 = halve, 2.0 = double, etc.')
        form = cmds.formLayout(height=22)
        lbl = cmds.text(label='Scale', width=130, align='right',
                        annotation=tip)
        self._tint_label(lbl, CLR_SCALE)
        fld = cmds.floatField(v=1.0, precision=2, width=50,
                              minValue=0.0, maxValue=10.0,
                              annotation=tip)
        holder = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form)
        btn = cmds.button(label='Apply', width=50, height=20,
                          annotation='Multiply all region values by the scale factor, then reset to 1.0')
        cmds.formLayout(form, e=True,
            attachForm=[(lbl, 'left', 0), (lbl, 'top', 0), (lbl, 'bottom', 0),
                        (fld, 'top', 0), (fld, 'bottom', 0),
                        (holder, 'top', 0), (holder, 'bottom', 0),
                        (btn, 'top', 0), (btn, 'bottom', 0),
                        (btn, 'right', 0)],
            attachNone=[(lbl, 'right'), (fld, 'right'), (btn, 'left')],
            attachControl=[(fld, 'left', 4, lbl),
                           (holder, 'left', 2, fld),
                           (holder, 'right', 2, btn)])
        sl = embed_single_in_layout(holder, minimum=0.0, maximum=10.0,
                                    value=1.0, color=CLR_SCALE)
        sl.setToolTip(tip)

        def _slider_changed(v):
            cmds.floatField(fld, e=True, v=v)

        def _field_changed(v):
            sl.setValue(v)

        def _apply(*_):
            scale = sl.value()
            if scale == 1.0:
                return
            for sec in sections:
                keys = self._section_keys.get(sec, [])
                for key in keys:
                    if key.endswith('_offset'):
                        continue
                    val = self._get_val(key)
                    self._set_val(key, val * scale)
            sl.setValue(1.0)
            cmds.floatField(fld, e=True, v=1.0)
            if self._auto_update:
                self._generate()

        sl.valueChanged.connect(_slider_changed)
        cmds.floatField(fld, e=True, changeCommand=_field_changed)
        cmds.button(btn, e=True, command=_apply)
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

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        self._category_header('Primary', legs + hip + root,
                              list(d.keys()), ['legs', 'hip', 'root'])
        self._scalar_row(['legs', 'hip', 'root'])

        # ── Legs ──
        cmds.separator(height=6, style='none')
        self._section_header('Legs', legs, 'legs')
        self._offset_slider('legs_offset', self._off_half)
        self._slider('Stride Length', 'stride', d['stride'], self._rng('stride'),
                     tip='Forward distance (translateZ) the foot travels per step')
        self._range_slider('Stride Width', 'stride_width', 'stride_width_swing',
                           d['stride_width'], d.get('stride_width_swing', d['stride_width']),
                           self._rng('stride_wh'), None,
                           tip='Lateral spread (translateX). Low = grounded width, Hi = swing-out width when foot is raised.')
        self._slider('Stride Height', 'stride_height', d['stride_height'],
                     self._rng('stride_h'),
                     tip='Vertical lift of the IK leg goal at mid-stride (translateY)')
        self._slider('Foot Raise', 'foot_raise', d['foot_raise'], self._rng('foot_raise'),
                     tip='Peak height the foot reaches during the passing position')
        self._slider_pair('Roll Heel', 'foot_roll_heel', d['foot_roll_heel'],
                          'Roll Toe', 'foot_roll_toe', d['foot_roll_toe'],
                          self._rng('roll'),
                          tip_a='Heel-strike roll angle at the start of contact phase',
                          tip_b='Toe-off roll angle at the end of contact phase')
        self._slider('Foot Bank  rZ', 'foot_bank', d.get('foot_bank', 0.0),
                     self._rng('rotation'), CLR_Z,
                     tip='Lateral foot tilt during push-off (rotateZ on IK leg). Inward bank.')

        # ── Hip ──
        cmds.separator(height=4, style='in')
        self._section_header('Hip', hip, 'hip')
        self._offset_slider('hip_offset', self._off_quarter)
        self._range_slider('Nod  rZ', 'hip_nod_back', 'hip_nod_front',
                           d['hip_nod_back'], d['hip_nod_front'],
                           self._rng('rotation'), CLR_Z,
                           tip='Forward/back pitch of the hip swinger (rotateZ). Range sets front and back extremes.')
        self._slider_pair('Lean  rY', 'hip_lean', d['hip_lean'],
                          'Twist  rX', 'hip_twist', d['hip_twist'],
                          self._rng('rotation'), CLR_Y, CLR_X,
                          tip_a='Lateral side-to-side tilt of the hips (rotateY)',
                          tip_b='Axial rotation of the hips around the spine (rotateX)',
                          rng_b=self._rng('twist'))

        # ── Root ──
        cmds.separator(height=4, style='in')
        self._section_header('Root', root, 'root')
        self._offset_slider('root_offset', self._off_quarter)
        self._range_slider('Bounce  tX', 'root_bounce_lo', 'root_bounce_hi',
                           d['root_bounce_lo'], d['root_bounce_hi'],
                           self._rng('translation'), CLR_X,
                           tip='Vertical bounce of the root (translateX). Low = contact, High = passing position.')
        self._range_slider('Nod  rZ', 'root_nod_back', 'root_nod_front',
                           d['root_nod_back'], d['root_nod_front'],
                           self._rng('rotation'), CLR_Z,
                           tip='Forward/back pitch of the root control (rotateZ)')
        self._slider_pair('Lean  rY', 'root_lean', d['root_lean'],
                          'Twist  rX', 'root_twist', d['root_twist'],
                          self._rng('rotation'), CLR_Y, CLR_X,
                          tip_a='Lateral side-to-side tilt of the root (rotateY)',
                          tip_b='Axial rotation of the root around the spine (rotateX)',
                          rng_b=self._rng('twist'))
        self._slider_pair('Left-Right  tZ', 'root_lr', d['root_lr'],
                          'Back-Forth  tY', 'root_bf', d['root_bf'],
                          self._rng('translation'), CLR_Z, CLR_Y,
                          tip_a='Lateral sway of the root centre of mass (translateZ)',
                          tip_b='Forward lean of the root centre of mass (translateY)')
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Run Primary section
    # ──────────────────────────────────────────────

    def _build_run_primary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Primary  (Root / Hips / Legs)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        d = self.run_primary.DEFAULTS

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        self._category_header('Run_Primary', legs + hip + root,
                              ['r_' + k for k in d.keys()],
                              ['run_legs', 'run_hip', 'run_root'])
        self._scalar_row(['run_legs', 'run_hip', 'run_root'])

        # ── Legs ──
        cmds.separator(height=6, style='none')
        self._section_header('Legs', legs, 'run_legs')
        self._offset_slider('r_legs_offset', self._off_half)
        self._slider('Stride Length', 'r_stride', d['stride'], self._rng('stride'),
                     tip='Forward distance (translateZ) per step')
        self._slider('Stride Height', 'r_stride_height', d['stride_height'],
                     self._rng('stride_h'),
                     tip='Peak foot height during swing phase (translateY)')
        self._slider_pair('Roll Ball', 'r_foot_roll_ball', d['foot_roll_ball'],
                          'Roll Toe', 'r_foot_roll_toe', d['foot_roll_toe'],
                          self._rng('roll'),
                          tip_a='Ball-strike angle at initial contact',
                          tip_b='Toe push-off angle')

        # ── Hip ──
        cmds.separator(height=4, style='in')
        self._section_header('Hip', hip, 'run_hip')
        self._offset_slider('r_hip_offset', self._off_quarter)
        self._slider('Twist  rX', 'r_hip_twist', d['hip_twist'],
                     self._rng('twist'), CLR_X,
                     tip='Hip counter-rotation around the spine (rotateX)')

        # ── Root ──
        cmds.separator(height=4, style='in')
        self._section_header('Root', root, 'run_root')
        self._offset_slider('r_root_offset', self._off_quarter)
        self._range_slider('Bounce  tX', 'r_root_bounce_lo', 'r_root_bounce_hi',
                           d['root_bounce_lo'], d['root_bounce_hi'],
                           self._rng('translation'), CLR_X,
                           tip='Root height. Low = contact compression, High = flight apex. '
                               'Opposite phase to walk (walk is high at contact).')
        self._slider('Forward Lean  rZ', 'r_forward_lean', d['forward_lean'],
                     self._rng('rotation'), CLR_Z,
                     tip='Constant forward pitch of the root (rotateZ). Run posture.')
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Sidestep Primary section
    # ──────────────────────────────────────────────

    def _build_sidestep_primary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Primary  (Root / Hips / Legs)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        col = cmds.columnLayout(adjustableColumn=True)

        d = self.sidestep_primary.DEFAULTS

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        self._category_header('Sidestep_Primary', legs + hip + root,
                              ['s_' + k for k in d.keys()],
                              ['ss_legs', 'ss_hip', 'ss_root'])
        self._scalar_row(['ss_legs', 'ss_hip', 'ss_root'])

        # ── Direction toggle ──
        cmds.separator(height=6, style='none')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(135, 200), height=24)
        cmds.text(label='Direction', width=130, align='right')
        self._strafe_dir_cb = cmds.checkBox(
            label='Strafe Right', value=bool(d.get('strafe_right', 1.0) >= 0.5),
            annotation='Checked = strafe right, unchecked = strafe left',
            changeCommand=lambda *_: self._generate() if self._auto_update else None)
        cmds.setParent('..')

        # ── Legs ──
        cmds.separator(height=6, style='none')
        self._section_header('Legs', legs, 'ss_legs')
        self._offset_slider('s_legs_offset', self._off_half)
        self._slider('Stride Length', 's_stride', d['stride'], self._rng('stride'),
                     tip='Lateral reach distance per step (translateX)')
        self._slider('Stride Height', 's_stride_height', d['stride_height'],
                     self._rng('stride_h'),
                     tip='Foot lift height during swing phase (translateY)')
        self._slider_pair('Roll Heel', 's_foot_roll_heel', d['foot_roll_heel'],
                          'Roll Toe', 's_foot_roll_toe', d['foot_roll_toe'],
                          self._rng('roll'),
                          tip_a='Heel contact angle',
                          tip_b='Toe push-off angle')

        # ── Hip ──
        cmds.separator(height=4, style='in')
        self._section_header('Hip', hip, 'ss_hip')
        self._offset_slider('s_hip_offset', self._off_quarter)
        self._slider('Lean  rY', 's_hip_lean', d['hip_lean'],
                     self._rng('rotation'), CLR_Y,
                     tip='Constant lean into travel direction (rotateY)')

        # ── Root ──
        cmds.separator(height=4, style='in')
        self._section_header('Root', root, 'ss_root')
        self._offset_slider('s_root_offset', self._off_quarter)
        self._range_slider('Bounce  tX', 's_root_bounce_lo', 's_root_bounce_hi',
                           d['root_bounce_lo'], d['root_bounce_hi'],
                           self._rng('translation'), CLR_X,
                           tip='Vertical root bounce. High at mid-stance (walk-style phase).')
        self._slider('Sway  tZ', 's_root_sway', d['root_sway'],
                     self._rng('translation'), CLR_Z,
                     tip='Lateral root shift following the stepping pattern (translateZ)')
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
                              list(self.walk_secondary.DEFAULTS.keys()),
                              list(part_ctrls.keys()))
        self._scalar_row(list(part_ctrls.keys()))

        for part in ('spine', 'chest', 'neck', 'head'):
            ctrl = [part_ctrls[part]]
            cmds.separator(height=4, style='in')
            self._section_header(part.title(), ctrl, part)
            self._offset_slider('{}_offset'.format(part), self._off_quarter)

            nod_f = self.walk_secondary._params['{}_nod_front'.format(part)]
            nod_b = self.walk_secondary._params['{}_nod_back'.format(part)]
            lean = self.walk_secondary._params['{}_lean'.format(part)]
            twist = self.walk_secondary._params['{}_twist'.format(part)]

            self._range_slider('Nod  rZ', '{}_nod_back'.format(part),
                               '{}_nod_front'.format(part),
                               nod_b, nod_f, self._rng('rotation'), CLR_Z,
                               tip='Forward/back pitch of the {} (rotateZ). '
                                   'Counters walk rhythm twice per cycle.'.format(part))
            self._slider_pair('Lean  rY', '{}_lean'.format(part), lean,
                              'Twist  rX', '{}_twist'.format(part), twist,
                              self._rng('rotation'), CLR_Y, CLR_X,
                              tip_a='Lateral side bend of the {} (rotateY)'.format(part),
                              tip_b='Axial roll of the {} around the spine axis (rotateX)'.format(part))

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
                              ['scapula', 'shoulder', 'elbow', 'wrist'])
        self._scalar_row(['scapula', 'shoulder', 'elbow', 'wrist'])

        # ── Scapula ──
        cmds.separator(height=6, style='none')
        self._section_header('Scapula', sc, 'scapula')
        self._offset_slider('scapula_offset', self._off_half)
        self._slider('Droop  rY', 'scapula_droop', d['scapula_droop'], self._rng('droop'), CLR_Y,
                     tip='Resting down-angle of the scapula (rotateY). Mirrored between sides.')
        self._range_slider('Swing  rZ', 'scapula_swing_back', 'scapula_swing_front',
                           d['scapula_swing_back'], d['scapula_swing_front'],
                           self._rng('swing'), CLR_Z,
                           tip='Forward/back scapula swing linked to arm movement (rotateZ)')
        self._slider('Twist  rX', 'scapula_twist', d.get('scapula_twist', 0.0),
                     self._rng('twist'), CLR_X,
                     tip='Axial twist of the scapula bone (rotateX). Mirrored between sides.')

        # ── Shoulder ──
        cmds.separator(height=4, style='in')
        self._section_header('Shoulder', sh, 'shoulder')
        self._offset_slider('shoulder_offset', self._off_half)
        self._range_slider('Swing  rZ', 'shoulder_swing_back', 'shoulder_swing_front',
                           d['shoulder_swing_back'], d['shoulder_swing_front'],
                           self._rng('swing'), CLR_Z,
                           tip='Forward/back arm swing arc (rotateZ). Back extreme and front extreme.')
        self._slider_pair('Droop  rY', 'shoulder_droop', d['shoulder_droop'],
                          'Twist  rX', 'shoulder_twist', d['shoulder_twist'],
                          self._rng('droop'), CLR_Y, CLR_X,
                          tip_a='Resting angle of the upper arm hanging down (rotateY). Mirrored between sides.',
                          tip_b='Axial twist of the upper arm bone (rotateX). Mirrored between sides.',
                          rng_b=self._rng('twist'))

        # ── Elbow ──
        cmds.separator(height=4, style='in')
        self._section_header('Elbow', el, 'elbow')
        self._offset_slider('elbow_offset', self._off_half)
        self._range_slider('Bend  rZ', 'elbow_bend_lo', 'elbow_bend_hi',
                           d['elbow_bend_lo'], d['elbow_bend_hi'], self._rng('elbow_bend'), CLR_Z,
                           tip='Elbow flexion range (rotateZ). Lo = arm extended, Hi = arm bent at mid-swing.')

        # ── Wrist ──
        cmds.separator(height=4, style='in')
        self._section_header('Wrist', wr, 'wrist')
        self._offset_slider('wrist_offset', self._off_half)
        self._range_slider('Swing  rZ', 'wrist_swing_back', 'wrist_swing_front',
                           d['wrist_swing_back'], d['wrist_swing_front'],
                           self._rng('swing'), CLR_Z,
                           tip='Wrist fore/aft swing following the arm arc (rotateZ)')
        self._slider('Twist  rX', 'wrist_twist', d.get('wrist_twist', 0.0),
                     self._rng('twist'), CLR_X,
                     tip='Axial twist of the wrist bone (rotateX). Mirrored between sides.')

        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Range Settings (collapsed section at bottom)
    # ──────────────────────────────────────────────

    def _build_range_settings(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Range Settings', collapsable=True,
                         collapse=True, marginHeight=6, marginWidth=6,
                         annotation='Configure the min/max limits for each slider category')
        col = cmds.columnLayout(adjustableColumn=True)

        self._rng_fields = {}  # name -> (min_fld, max_fld)
        for name in ('rotation', 'translation', 'roll',
                     'stride', 'stride_wh', 'stride_h', 'foot_raise',
                     'swing', 'droop', 'twist', 'elbow_bend'):
            label = _RANGE_LABELS.get(name, name)
            rng = self._rng(name)
            cmds.text(label=label, align='left', font='boldLabelFont')
            row = cmds.rowLayout(numberOfColumns=4, columnWidth4=(
                40, 60, 10, 60), adjustableColumn=4)
            cmds.text(label='Min:')
            f_min = cmds.floatField(v=rng[0], precision=1, width=55)
            cmds.text(label='Max:')
            f_max = cmds.floatField(v=rng[1], precision=1, width=55)
            cmds.setParent(col)
            self._rng_fields[name] = (f_min, f_max)
            cmds.separator(height=4, style='none')

        cmds.separator(height=6, style='in')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 150),
                       adjustableColumn=2)
        cmds.button(label='Save Range Settings',
                    annotation='Write the current min/max values to settings.json on disk',
                    command=lambda *_: self._save_range_settings())
        cmds.button(label='Reset to Defaults',
                    annotation='Restore all range limits to their factory defaults',
                    command=lambda *_: self._reset_range_settings())
        cmds.setParent(parent)

    def _settings_path(self):
        return _SETTINGS_JSON

    def _save_range_settings(self):
        new_ranges = {}
        for name, (f_min, f_max) in self._rng_fields.items():
            new_ranges[name] = [
                cmds.floatField(f_min, q=True, v=True),
                cmds.floatField(f_max, q=True, v=True),
            ]
        with open(_SETTINGS_JSON, 'w') as f:
            json.dump({'ranges': new_ranges}, f, indent=2)
            f.write('\n')
        self._ranges = self._load_ranges()
        cmds.confirmDialog(title='Saved', message='Range settings saved.\n'
                           'Reopen the window to apply new ranges.',
                           button=['OK'])

    def _reset_range_settings(self):
        # Read the defaults from settings.py (the template)
        from . import settings as _s
        with open(_SETTINGS_JSON, 'w') as f:
            json.dump({'ranges': dict(_s._DEFAULTS)}, f, indent=2)
            f.write('\n')
        self._ranges = self._load_ranges()
        for name, (f_min, f_max) in self._rng_fields.items():
            rng = self._rng(name)
            cmds.floatField(f_min, e=True, v=rng[0])
            cmds.floatField(f_max, e=True, v=rng[1])

    # ──────────────────────────────────────────────
    #  Actions
    # ──────────────────────────────────────────────

    def _build_actions(self, parent):
        cmds.setParent(parent)
        cmds.separator(height=10, style='in')

        # ── Main actions ──
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(200, 150, 150, 100),
                       adjustableColumn=1)
        cmds.button(label='Generate', height=36,
                    backgroundColor=(0.22, 0.55, 0.22),
                    annotation='Key all layers on the current timeline range using the slider values above',
                    command=lambda *_: self._generate())
        cmds.button(label='Delete Animation', height=36,
                    backgroundColor=(0.55, 0.22, 0.22),
                    annotation='Remove all keyframes set by this tool from every affected control',
                    command=lambda *_: self._delete_anim())
        cmds.button(label='Select All Controls', height=36,
                    backgroundColor=CLR_SELECT_BTN,
                    annotation='Select every rig control used by all layers in the viewport',
                    command=lambda *_: self._sel_all())
        cmds.checkBox(label='Auto', value=False,
                      annotation='Automatically regenerate the walk cycle whenever any slider changes',
                      changeCommand=lambda val: self._toggle_auto(val))
        cmds.setParent('..')

        # ── Variation ──
        form_var = cmds.formLayout(height=22)
        lbl_var = cmds.text(label='Variation %', width=80, align='right',
                            annotation='Random amplitude perturbation (0 = none, higher = more organic)')
        fld_var = cmds.floatField(v=0, precision=1, width=45,
                                  minValue=0, maxValue=50,
                                  annotation='Percentage of random variation applied to amplitudes')
        holder_var = cmds.columnLayout(adjustableColumn=True, height=20)
        cmds.setParent(form_var)
        cmds.formLayout(form_var, e=True,
            attachForm=[(lbl_var, 'left', 0), (lbl_var, 'top', 0), (lbl_var, 'bottom', 0),
                        (fld_var, 'top', 0), (fld_var, 'bottom', 0),
                        (holder_var, 'top', 0), (holder_var, 'bottom', 0),
                        (holder_var, 'right', 0)],
            attachNone=[(lbl_var, 'right'), (fld_var, 'right')],
            attachControl=[(fld_var, 'left', 4, lbl_var),
                           (holder_var, 'left', 2, fld_var)])
        self._var_slider = embed_single_in_layout(holder_var, minimum=0,
                                                   maximum=50, value=0)
        self._var_slider.setToolTip('Random amplitude perturbation (0 = none)')
        self._var_slider.valueChanged.connect(
            lambda v: cmds.floatField(fld_var, e=True, v=v))
        cmds.floatField(fld_var, e=True,
                        changeCommand=lambda v: self._var_slider.setValue(v))
        self._var_field = fld_var
        cmds.setParent('..')

        # ── Presets ──
        cmds.separator(height=8, style='in')
        cmds.frameLayout(label='Presets', collapsable=True,
                         marginHeight=4, marginWidth=4)
        pre_col = cmds.columnLayout(adjustableColumn=True)

        form_pre = cmds.formLayout(height=24)
        lbl_pre = cmds.text(label='Preset:', align='right', width=50)
        combo_holder = cmds.columnLayout(adjustableColumn=True, height=22)
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.setToolTip('Choose a saved preset from the library or project')
        ptr = omui.MQtUtil.findControl(combo_holder)
        if ptr:
            qt_parent = wrapInstance(int(ptr), QtWidgets.QWidget)
            lay = qt_parent.layout() or QtWidgets.QVBoxLayout(qt_parent)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._preset_combo)
        cmds.setParent(form_pre)
        self._refresh_preset_list()
        btn_save = cmds.button(label='Save', width=55,
                    backgroundColor=(0.45, 0.45, 0.22),
                    annotation='Overwrite the selected preset file with current settings',
                    command=lambda *_: self._save_selected_preset())
        btn_load = cmds.button(label='Load', width=55,
                    backgroundColor=(0.22, 0.55, 0.22),
                    annotation='Apply the selected preset, updating all sliders to its stored values',
                    command=lambda *_: self._load_selected_preset())
        btn_del = cmds.button(label='Delete', width=55,
                    backgroundColor=(0.55, 0.22, 0.22),
                    annotation='Permanently delete the selected preset file from disk',
                    command=lambda *_: self._delete_selected_preset())
        cmds.formLayout(form_pre, e=True,
            attachForm=[(lbl_pre, 'left', 0), (lbl_pre, 'top', 0), (lbl_pre, 'bottom', 0),
                        (combo_holder, 'top', 0), (combo_holder, 'bottom', 0),
                        (btn_save, 'top', 0), (btn_save, 'bottom', 0),
                        (btn_load, 'top', 0), (btn_load, 'bottom', 0),
                        (btn_del, 'top', 0), (btn_del, 'bottom', 0),
                        (btn_del, 'right', 0)],
            attachNone=[(lbl_pre, 'right'), (btn_save, 'left'),
                        (btn_load, 'left'), (btn_del, 'left')],
            attachControl=[(combo_holder, 'left', 4, lbl_pre),
                           (combo_holder, 'right', 4, btn_save),
                           (btn_save, 'right', 2, btn_load),
                           (btn_load, 'right', 2, btn_del)])
        cmds.setParent(pre_col)

        cmds.separator(height=4, style='none')
        form_save = cmds.formLayout(height=26)
        btn_lib = cmds.button(label='Save to Library',
                    backgroundColor=CLR_LIB,
                    annotation='Save current settings as a named preset in the global library folder',
                    command=lambda *_: self._save_to_library())
        btn_proj = cmds.button(label='Save to Project',
                    backgroundColor=CLR_PROJ,
                    annotation='Save current settings as a named preset inside the active Maya project',
                    command=lambda *_: self._save_to_project())
        cmds.formLayout(form_save, e=True,
            attachForm=[(btn_lib, 'left', 0), (btn_lib, 'top', 0), (btn_lib, 'bottom', 0),
                        (btn_proj, 'right', 0), (btn_proj, 'top', 0), (btn_proj, 'bottom', 0)],
            attachPosition=[(btn_lib, 'right', 2, 50),
                            (btn_proj, 'left', 2, 50)])
        cmds.setParent(pre_col)

        cmds.separator(height=4, style='none')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(190, 190, 190),
                       adjustableColumn=3)
        cmds.button(label='Save As...',
                    annotation='Browse for a location and save current settings as a JSON preset file',
                    command=lambda *_: self._save_preset_browse())
        cmds.button(label='Load File...',
                    annotation='Browse for and load a JSON preset file from disk',
                    command=lambda *_: self._load_preset_browse())
        cmds.button(label='Print Settings',
                    annotation='Print all current slider values to the Script Editor as JSON',
                    command=lambda *_: self._print_settings())
        cmds.setParent(parent)

    # ──────────────────────────────────────────────
    #  Callbacks
    # ──────────────────────────────────────────────

    def _read_fields(self):
        for key in self._fields:
            val = self._get_val(key)
            # Run primary keys are prefixed with 'r_'
            if key.startswith('r_') and key[2:] in self.run_primary.DEFAULTS:
                self.run_primary._params[key[2:]] = val
            elif key.startswith('s_') and key[2:] in self.sidestep_primary.DEFAULTS:
                self.sidestep_primary._params[key[2:]] = val
            elif key in self.walk_primary.DEFAULTS:
                self.walk_primary._params[key] = val
            elif key in self.walk_secondary.DEFAULTS:
                self.walk_secondary._params[key] = val
            elif key in self.walk_arms.DEFAULTS:
                self.walk_arms._params[key] = val
        # Sidestep direction checkbox (not a float slider)
        if hasattr(self, '_strafe_dir_cb'):
            self.sidestep_primary._params['strafe_right'] = (
                1.0 if cmds.checkBox(self._strafe_dir_cb, q=True, value=True)
                else 0.0)

    def _layers(self):
        """Return the layer list for the active clip type."""
        return [self._active_primary, self.walk_secondary, self.walk_arms]

    def _delete_anim(self):
        all_ctrls = set()
        fkik_ctrls = set()
        for layer in self._layers():
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
        variation = self._var_slider.value() if hasattr(self, '_var_slider') else 0
        engine.generate(self._layers(), variation=variation)

    def _sel_all(self):
        all_ctrls = []
        for layer in self._layers():
            all_ctrls.extend(layer.controls())
        self._sel(all_ctrls)

    def _toggle_auto(self, val):
        self._auto_update = val
        # Single and range sliders already fire callbacks that check
        # self._auto_update, so nothing extra is needed here.

    def _all_params(self):
        self._read_fields()
        return {
            'primary': self._active_primary.params(),
            'secondary': self.walk_secondary.params(),
            'arms': self.walk_arms.params(),
        }

    # ── preset callbacks ──

    def _refresh_preset_list(self):
        combo = self._preset_combo
        combo.clear()
        self._preset_entries = presets.list_presets(self._active_clip)
        for i, entry in enumerate(self._preset_entries):
            is_lib = entry['source'] == 'library'
            clr = CLR_LIB if is_lib else CLR_PROJ
            r, g, b = [int(c * 255) for c in clr]
            # Colored square icon, plain text name
            px = QtGui.QPixmap(12, 12)
            px.fill(QtGui.QColor(r, g, b))
            combo.addItem(QtGui.QIcon(px), entry['name'])
        if not self._preset_entries:
            combo.addItem('(no presets found)')

    def _qt_parent(self):
        """Return the Qt widget parent for modal dialogs."""
        ptr = omui.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None

    def _save_selected_preset(self):
        if not self._preset_entries:
            return
        idx = self._preset_combo.currentIndex()
        if idx < 0 or idx >= len(self._preset_entries):
            return
        entry = self._preset_entries[idx]
        clr = CLR_LIB if entry['source'] == 'library' else CLR_PROJ
        hex_clr = '#{:02x}{:02x}{:02x}'.format(*(int(c * 255) for c in clr))
        msg = QtWidgets.QMessageBox(self._qt_parent())
        msg.setWindowTitle('Overwrite Preset')
        msg.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg.setText(
            'Overwrite <big><b style="color:{}">{}</b></big>'
            '&nbsp; ({})'
            '<br><br><span style="font-size:small; word-wrap:break-word">{}</span>'.format(
                hex_clr, entry['name'], entry['source'], entry['path']))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        if msg.exec() != QtWidgets.QMessageBox.Save:
            return
        data = self._all_params()
        existing = presets.load(entry['path'])
        meta = existing.get('meta', {})
        meta['date'] = __import__('datetime').date.today().isoformat()
        data['meta'] = meta
        presets.save(entry['path'], data)
        print('// Overwritten preset: {}'.format(entry['path']))

    def _load_selected_preset(self):
        if not self._preset_entries:
            return
        idx = self._preset_combo.currentIndex()
        if idx < 0 or idx >= len(self._preset_entries):
            return
        data = presets.load(self._preset_entries[idx]['path'])
        self._apply_preset_data(data)

    def _delete_selected_preset(self):
        if not self._preset_entries:
            return
        idx = self._preset_combo.currentIndex()
        if idx < 0 or idx >= len(self._preset_entries):
            return
        entry = self._preset_entries[idx]
        clr = CLR_LIB if entry['source'] == 'library' else CLR_PROJ
        hex_clr = '#{:02x}{:02x}{:02x}'.format(*(int(c * 255) for c in clr))
        msg = QtWidgets.QMessageBox(self._qt_parent())
        msg.setWindowTitle('Delete Preset')
        msg.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg.setText(
            'Delete <big><b style="color:{}">{}</b></big>'
            '&nbsp; ({})'
            '<br><br><span style="font-size:small; word-wrap:break-word">{}</span>'.format(
                hex_clr, entry['name'], entry['source'], entry['path']))
        btn_del = msg.addButton('Delete', QtWidgets.QMessageBox.DestructiveRole)
        msg.addButton(QtWidgets.QMessageBox.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        msg.exec()
        if msg.clickedButton() != btn_del:
            return
        import os
        try:
            os.remove(entry['path'])
            print('// Deleted preset: {}'.format(entry['path']))
        except OSError as e:
            cmds.warning('Could not delete preset: {}'.format(e))
            return
        self._refresh_preset_list()

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
        path = presets.save_to_library(self._all_params(), name,
                                       cycle_type=self._active_clip)
        if path:
            print('// Saved to library: {}'.format(path))
            self._refresh_preset_list()

    def _save_to_project(self):
        name = self._prompt_name('Save to Project')
        if not name:
            return
        path = presets.save_to_project(self._all_params(), name,
                                       cycle_type=self._active_clip)
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
            self._active_primary.set_params(data['primary'])
        if 'secondary' in data:
            self.walk_secondary.set_params(data['secondary'])
        if 'arms' in data:
            self.walk_arms.set_params(data['arms'])
        self._refresh_fields()

    def _refresh_fields(self):
        all_p = {}
        all_p.update(self.walk_secondary._params)
        all_p.update(self.walk_arms._params)
        # Walk primary keys (no prefix)
        all_p.update(self.walk_primary._params)
        # Run primary keys (r_ prefix for UI)
        for k, v in self.run_primary._params.items():
            all_p['r_' + k] = v
        # Sidestep primary keys (s_ prefix for UI)
        for k, v in self.sidestep_primary._params.items():
            all_p['s_' + k] = v
        for key in self._fields:
            if key in all_p:
                try:
                    self._set_val(key, all_p[key])
                except Exception:
                    pass
        # Sync sidestep direction checkbox
        if hasattr(self, '_strafe_dir_cb'):
            sr = self.sidestep_primary._params.get('strafe_right', 1.0)
            cmds.checkBox(self._strafe_dir_cb, e=True,
                          value=bool(sr >= 0.5))

    def _print_settings(self):
        data = self._all_params()
        print('// AnimGenV2 Settings:\n' + json.dumps(data, indent=2))


# ── module-level convenience ──

def show():
    """Create and show the animation generator window."""
    win = AnimGenWindow()
    win.show()
    return win
