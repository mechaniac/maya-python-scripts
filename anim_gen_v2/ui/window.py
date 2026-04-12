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


class AnimGenWindow:

    def __init__(self):
        self.walk_primary = WalkPrimary()
        self.walk_secondary = WalkSecondary()
        self.walk_arms = WalkArms()
        self._fields = {}
        self._auto_update = False

    # ──────────────────────────────────────────────
    #  Show
    # ──────────────────────────────────────────────

    def show(self):
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)
        win = cmds.window(WINDOW_NAME, title=WINDOW_TITLE,
                          widthHeight=(620, 700), sizeable=True)
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
    #  Field helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _sel(ctrls):
        """Select the given controls in the viewport (resolver-aware)."""
        from ..core import resolver
        nodes = []
        for c in ctrls:
            n = resolver.resolve(c)
            if n and cmds.objExists(n):
                nodes.append(n)
        if nodes:
            cmds.select(nodes, r=True)

    def _sel_btn(self, ctrls):
        """Create a small select-control icon button."""
        cmds.iconTextButton(style='iconOnly', image='aselect.png',
                            width=22, height=22,
                            annotation='Select  ' + ', '.join(ctrls),
                            command=lambda *_, c=list(ctrls): self._sel(c))

    def _float_field(self, key, default, color=None):
        kw = dict(v=default, precision=2, width=80)
        if color:
            kw['backgroundColor'] = color
        f = cmds.floatField(**kw)
        self._fields[key] = f
        return f

    def _row(self, label, key, default, color=None, ctrls=None):
        if ctrls:
            cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 100, 24),
                           adjustableColumn=2)
        else:
            cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 100),
                           adjustableColumn=2)
        cmds.text(label=label)
        self._float_field(key, default, color)
        if ctrls:
            self._sel_btn(ctrls)
        cmds.setParent('..')

    def _two_col(self, l1, k1, d1, c1, l2, k2, d2, c2,
                 ctrls1=None, ctrls2=None):
        has_sel = ctrls1 or ctrls2
        if has_sel:
            cmds.rowLayout(numberOfColumns=6,
                           columnWidth6=(148, 80, 22, 148, 80, 22),
                           adjustableColumn=4)
        else:
            cmds.rowLayout(numberOfColumns=4,
                           columnWidth4=(160, 90, 160, 90),
                           adjustableColumn=4)
        cmds.text(label=l1); self._float_field(k1, d1, c1)
        if has_sel:
            if ctrls1:
                self._sel_btn(ctrls1)
            else:
                cmds.text(label='', width=22)
        cmds.text(label=l2); self._float_field(k2, d2, c2)
        if has_sel:
            if ctrls2:
                self._sel_btn(ctrls2)
            else:
                cmds.text(label='', width=22)
        cmds.setParent('..')

    def _zero_fields(self, keys):
        """Set all float fields in *keys* to 0."""
        for k in keys:
            f = self._fields.get(k)
            if f:
                cmds.floatField(f, e=True, v=0)

    # ──────────────────────────────────────────────
    #  Walk Primary section
    # ──────────────────────────────────────────────

    def _build_walk_primary(self, parent):
        cmds.setParent(parent)
        cmds.frameLayout(label='Primary  (Root / Hips / Legs)',
                         collapsable=True, marginHeight=4, marginWidth=4)
        cmds.columnLayout(adjustableColumn=True)

        legs = ['IKLeg_R', 'IKLeg_L']
        hip = ['HipSwinger_M']
        root = ['RootX_M']

        d = self.walk_primary.DEFAULTS
        self._row('Stride Length', 'stride', d['stride'], ctrls=legs)
        self._two_col('Stride Width  X', 'stride_width', d['stride_width'], CLR_X,
                       'Stride Height  Y', 'stride_height', d['stride_height'], CLR_Y,
                       ctrls1=legs, ctrls2=legs)
        self._row('Foot Raise  rX', 'foot_raise', d['foot_raise'], CLR_X, ctrls=legs)

        cmds.separator(height=8, style='in')
        self._two_col('Hip Swing  rZ', 'hip_swing', d['hip_swing'], CLR_Z,
                       'Hip Sway  rY', 'hip_sway', d['hip_sway'], CLR_Y,
                       ctrls1=hip, ctrls2=hip)

        cmds.separator(height=8, style='in')
        self._two_col('Bounce  tY', 'root_bounce', d['root_bounce'], CLR_Y,
                       'Bounce Offset', 'bounce_offset', d['bounce_offset'], CLR_Y,
                       ctrls1=root, ctrls2=root)
        self._two_col('Sway  rY', 'root_sway', d['root_sway'], CLR_Y,
                       'Rock  rX', 'root_rock', d['root_rock'], CLR_X,
                       ctrls1=root, ctrls2=root)
        self._two_col('Twist  rZ', 'root_twist', d['root_twist'], CLR_Z,
                       'Rock Offset', 'rock_offset', d['rock_offset'], CLR_X,
                       ctrls1=root, ctrls2=root)
        self._two_col('Left-Right  tX', 'root_lr', d['root_lr'], CLR_X,
                       'Back-Forth  tZ', 'root_bf', d['root_bf'], CLR_Z,
                       ctrls1=root, ctrls2=root)

        cmds.separator(height=6, style='none')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(310, 290),
                       adjustableColumn=2)
        cmds.button(label='Set to 0', height=22,
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
        cmds.columnLayout(adjustableColumn=True)

        part_ctrls = {
            'spine1': 'FKSpine1_M', 'chest': 'FKChest_M',
            'neck': 'FKNeck_M', 'head': 'FKHead_M',
        }

        for part in ('spine1', 'chest', 'neck', 'head'):
            ctrl = [part_ctrls[part]]
            cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 24),
                           adjustableColumn=1)
            cmds.text(label='  {} :'.format(part.title()), align='left',
                      font='boldLabelFont')
            self._sel_btn(ctrl)
            cmds.setParent('..')

            nod = self.walk_secondary._params['{}_nod'.format(part)]
            lean = self.walk_secondary._params['{}_lean'.format(part)]
            twist = self.walk_secondary._params['{}_twist'.format(part)]
            twist_off = self.walk_secondary._params['{}_twist_offset'.format(part)]
            self._two_col('Nod  rZ', '{}_nod'.format(part), nod, CLR_Z,
                           'Lean  rY', '{}_lean'.format(part), lean, CLR_Y,
                           ctrls1=ctrl, ctrls2=ctrl)
            self._two_col('Twist  rX', '{}_twist'.format(part), twist, CLR_X,
                           'Twist Offset', '{}_twist_offset'.format(part), twist_off, CLR_X,
                           ctrls1=ctrl, ctrls2=ctrl)

        cmds.separator(height=6, style='none')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(310, 290),
                       adjustableColumn=2)
        cmds.button(label='Set to 0', height=22,
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
        cmds.columnLayout(adjustableColumn=True)

        sh = ['FKShoulder_R', 'FKShoulder_L']
        sc = ['FKScapula_R', 'FKScapula_L']
        el = ['FKElbow_R', 'FKElbow_L']
        wr = ['FKWrist_R', 'FKWrist_L']
        all_arm = sc + sh + el + wr

        d = self.walk_arms.DEFAULTS
        self._two_col('Shoulder Droop  rY', 'shoulder_droop', d['shoulder_droop'], CLR_Y,
                       'Scapula Droop  rY', 'scapula_droop', d['scapula_droop'], CLR_Y,
                       ctrls1=sh, ctrls2=sc)
        self._two_col('Shoulder Swing  rZ', 'shoulder_swing', d['shoulder_swing'], CLR_Z,
                       'Shoulder Twist  rX', 'shoulder_twist', d['shoulder_twist'], CLR_X,
                       ctrls1=sh, ctrls2=sh)
        self._two_col('Scapula Swing  rZ', 'scapula_swing', d['scapula_swing'], CLR_Z,
                       'Elbow Bend  rZ', 'elbow_bend', d['elbow_bend'], CLR_Z,
                       ctrls1=sc, ctrls2=el)
        self._row('Wrist Swing  rZ', 'wrist_swing', d['wrist_swing'], CLR_Z, ctrls=wr)

        cmds.separator(height=6, style='none')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(310, 290),
                       adjustableColumn=2)
        cmds.button(label='Set to 0', height=22,
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
        cmds.separator(height=12, style='in')

        cmds.rowLayout(numberOfColumns=3, columnWidth3=(250, 200, 150),
                       adjustableColumn=1)
        cmds.button(label='Generate Walk Cycle', height=36,
                    command=lambda *_: self._generate())
        cmds.button(label='Select All Controls', height=36,
                    command=lambda *_: self._sel_all())
        cmds.checkBox(label='Auto-update', value=False,
                      changeCommand=lambda val: self._toggle_auto(val))
        cmds.setParent('..')

        cmds.separator(height=8, style='in')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(200, 200, 200),
                       adjustableColumn=3)
        cmds.button(label='Save Preset',
                    command=lambda *_: self._save_preset())
        cmds.button(label='Load Preset',
                    command=lambda *_: self._load_preset())
        cmds.button(label='Print Settings',
                    command=lambda *_: self._print_settings())
        cmds.setParent('..')

    # ──────────────────────────────────────────────
    #  Callbacks
    # ──────────────────────────────────────────────

    def _read_fields(self):
        """Sync current UI field values into layer parameters."""
        for key, ctrl in self._fields.items():
            val = cmds.floatField(ctrl, q=True, v=True)
            if key in self.walk_primary.DEFAULTS:
                self.walk_primary._params[key] = val
            elif key in self.walk_secondary._params:
                self.walk_secondary._params[key] = val
            elif key in self.walk_arms.DEFAULTS:
                self.walk_arms._params[key] = val

    def _generate(self):
        self._read_fields()
        engine.generate([self.walk_primary,
                         self.walk_secondary,
                         self.walk_arms])

    def _sel_all(self):
        """Select every control used by all enabled layers."""
        all_ctrls = (self.walk_primary.controls()
                     + self.walk_secondary.controls()
                     + self.walk_arms.controls())
        self._sel(all_ctrls)

    def _toggle_auto(self, val):
        self._auto_update = val
        cb = (lambda *_: self._generate()) if val else (lambda *_: None)
        for f in self._fields.values():
            try:
                cmds.floatField(f, e=True, changeCommand=cb)
            except Exception:
                pass

    def _all_params(self):
        self._read_fields()
        return {
            'primary': self.walk_primary.params(),
            'secondary': self.walk_secondary.params(),
            'arms': self.walk_arms.params(),
        }

    def _save_preset(self):
        presets.browse_save(self._all_params())

    def _load_preset(self):
        data = presets.browse_load()
        if not data:
            return
        if 'primary' in data:
            self.walk_primary.set_params(data['primary'])
        if 'secondary' in data:
            self.walk_secondary.set_params(data['secondary'])
        if 'arms' in data:
            self.walk_arms.set_params(data['arms'])
        self._refresh_fields()

    def _refresh_fields(self):
        """Push layer params back into the UI fields."""
        all_p = {}
        all_p.update(self.walk_primary._params)
        all_p.update(self.walk_secondary._params)
        all_p.update(self.walk_arms._params)
        for key, ctrl in self._fields.items():
            if key in all_p:
                try:
                    cmds.floatField(ctrl, e=True, v=all_p[key])
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
