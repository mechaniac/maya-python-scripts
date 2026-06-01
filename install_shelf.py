"""Install / update the C_Scripts Maya shelf.

Run once from the Script Editor (or any shelf button) to create or
refresh the shelf with the latest button definitions.  Safe to
re-run -- existing buttons are deleted first so nothing duplicates.

Usage::

    import install_shelf; install_shelf.install()
"""

import os
import maya.cmds as cmds
import maya.mel as mel
import maya.utils as maya_utils
import textwrap


SHELF_NAME = 'C_Scripts'

# Custom icons live here (a sub-folder of Maya's prefs/icons, which is not
# recursively scanned by default -- we add it to XBMLANGPATH at install).
_ICON_SUBFOLDER = 'toolSuite'

_DEFAULT_ICON_SPECS = {
    'charImporter.png': {
        'label': 'S2',
        'bg': (45, 83, 118),
        'accent': (93, 170, 210),
    },
    'AutoRig.png': {
        'label': 'RIG',
        'bg': (66, 78, 62),
        'accent': (127, 176, 82),
    },
    'AnimGenerator.png': {
        'label': 'AN',
        'bg': (88, 67, 112),
        'accent': (181, 134, 218),
    },
    'ClipSetter.png': {
        'label': 'CLP',
        'bg': (96, 76, 54),
        'accent': (213, 158, 77),
    },
    'gltfImpExp.png': {
        'label': 'GLB',
        'bg': (55, 82, 88),
        'accent': (98, 196, 186),
    },
    'BlendShapeSetup.png': {
        'label': 'BS',
        'bg': (78, 59, 96),
        'accent': (210, 152, 214),
    },
    'SceneTools.png': {
        'label': 'TL',
        'bg': (65, 68, 74),
        'accent': (135, 167, 199),
    },
    'RenderLayerSetter.png': {
        'label': 'RLY',
        'bg': (91, 54, 48),
        'accent': (220, 117, 94),
    },
    'refresh.png': {
        'label': 'SET',
        'bg': (48, 80, 76),
        'accent': (91, 186, 154),
    },
}

_STOCK_ICON_FALLBACKS = {
    'charImporter.png': 'fileOpen.png',
    'AutoRig.png': 'kinJoint.png',
    'AnimGenerator.png': 'setKeyframe.png',
    'ClipSetter.png': 'timeEditorClip.png',
    'gltfImpExp.png': 'polyCube.png',
    'BlendShapeSetup.png': 'blendShape.png',
    'SceneTools.png': 'toolSettings.png',
    'RenderLayerSetter.png': 'renderLayerEditor.png',
    'refresh.png': 'refresh.png',
}

_SHELF_TOOLTIPS = {
    'charImporter.png': (
        'Open the Source 2 Character Importer for loading and converting '
        'Source 2 character assets.'
    ),
    'AutoRig.png': (
        'Open the Auto Control Rig builder for controls, helpers, twist '
        'joints, and stretchy IK setup.'
    ),
    'AnimGenerator.png': (
        'Open Animation Generator v2 for procedural walk, run, sidestep, '
        'and layered animation generation.'
    ),
    'ClipSetter.png': (
        'Open Clip Setter for s&box character clip export and timeline setup.'
    ),
    'gltfImpExp.png': (
        'Open glTF/GLB import and export tools with plugin and fallback '
        'status checks.'
    ),
    'BlendShapeSetup.png': (
        'Open Blendshape Setup for multi-mesh targets, wrap deformers, '
        'BindPose, and keyed modeling poses.'
    ),
    'SceneTools.png': (
        'Open Scene Tools for cleanup, UV/layout helpers, reduced '
        'Hypershade, and scene utilities.'
    ),
    'RenderLayerSetter.png': (
        'Run Render Layer Setter for render layer setup.'
    ),
    'refresh.png': (
        'Rebuild the C_Scripts shelf and recreate missing default shelf icons.'
    ),
}


def _icon_dir():
    """Return the absolute path to the custom icon folder for this Maya version."""
    docs = os.path.expanduser('~/Documents')
    version = cmds.about(version=True)
    return os.path.normpath(os.path.join(
        docs, 'maya', version, 'prefs', 'icons', _ICON_SUBFOLDER))


def _register_icon_path():
    """Add the custom icon folder to XBMLANGPATH so Maya finds the PNGs."""
    path = _icon_dir()
    if not os.path.isdir(path):
        return
    current = os.environ.get('XBMLANGPATH', '')
    parts = [p for p in current.split(os.pathsep) if p]
    if path not in parts:
        os.environ['XBMLANGPATH'] = os.pathsep.join([path] + parts)


def _ensure_default_icons():
    """Create simple default shelf icons if prefs/custom icons were wiped."""
    path = _icon_dir()
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except OSError:
        return

    try:
        try:
            from PySide6 import QtCore, QtGui
        except ImportError:
            from PySide2 import QtCore, QtGui
    except Exception:
        return

    for image_name, spec in _DEFAULT_ICON_SPECS.items():
        icon_path = os.path.join(path, image_name)
        if os.path.isfile(icon_path):
            continue
        _draw_default_icon(icon_path, spec, QtCore, QtGui)


def _draw_default_icon(icon_path, spec, QtCore, QtGui):
    size = 64
    try:
        image_format = QtGui.QImage.Format_ARGB32
    except AttributeError:
        image_format = QtGui.QImage.Format.Format_ARGB32
    image = QtGui.QImage(size, size, image_format)
    try:
        image.fill(QtCore.Qt.transparent)
    except AttributeError:
        image.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(image)
    try:
        hint = QtGui.QPainter.Antialiasing
    except AttributeError:
        hint = QtGui.QPainter.RenderHint.Antialiasing
    painter.setRenderHint(hint)

    bg = QtGui.QColor(*spec['bg'])
    accent = QtGui.QColor(*spec['accent'])
    text = QtGui.QColor(236, 244, 248)

    try:
        painter.setPen(QtCore.Qt.NoPen)
    except AttributeError:
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(bg)
    painter.drawRoundedRect(0, 0, size, size, 10, 10)
    painter.setBrush(accent)
    painter.drawRect(0, size - 12, size, 12)

    font = painter.font()
    font.setBold(True)
    font.setPixelSize(24 if len(spec['label']) <= 2 else 18)
    painter.setFont(font)
    painter.setPen(text)

    try:
        align = QtCore.Qt.AlignCenter
    except AttributeError:
        align = QtCore.Qt.AlignmentFlag.AlignCenter
    painter.drawText(QtCore.QRect(0, 0, size, size - 4), align, spec['label'])
    painter.end()

    image.save(icon_path)


def _button_icon(btn):
    image_name = btn.get('image', 'commandButton.png')
    icon_path = os.path.join(_icon_dir(), image_name)
    if os.path.isfile(icon_path):
        return icon_path
    return _STOCK_ICON_FALLBACKS.get(image_name, 'commandButton.png')


def _button_tooltip(btn):
    image_name = btn.get('image', '')
    return _SHELF_TOOLTIPS.get(
        image_name,
        btn.get('annotation') or btn.get('label', '').replace('\n', ' '),
    )


# ── button definitions ────────────────────────────────────────────

def _apply_rollover_tooltips(button_tooltips):
    for button, tooltip in button_tooltips:
        _set_rollover_tooltip(button, tooltip)


def _set_rollover_tooltip(button, tooltip):
    if not button or not tooltip:
        return False

    for command in (cmds.shelfButton, cmds.control):
        try:
            command(button, edit=True, annotation=tooltip)
        except Exception:
            pass

    try:
        from maya import OpenMayaUI as omui
        try:
            from PySide6 import QtWidgets
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets
            from shiboken2 import wrapInstance
    except Exception:
        return False

    ptr = omui.MQtUtil.findControl(button)
    if ptr is None:
        return False

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    if widget is None:
        return False

    widget.setToolTip(tooltip)
    widget.setStatusTip(tooltip)
    widget.setWhatsThis(tooltip)
    try:
        widget.setToolTipDuration(-1)
    except Exception:
        pass
    return True


_BUTTONS = [
    {
        'label': 'S2 Import',
        'annotation': (
            'Open the Source 2 Character Importer for loading and converting '
            'Source 2 character assets.'
        ),
        'image': 'charImporter.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            import source2_importer.kv3 as _kv3; importlib.reload(_kv3)
            import source2_importer.vrf as _vrf; importlib.reload(_vrf)
            import source2_importer.materials as _mat; importlib.reload(_mat)
            import source2_importer.pipeline as _pip; importlib.reload(_pip)
            import source2_importer.ui as _sui; importlib.reload(_sui)
            import source2Importer; importlib.reload(source2Importer)
            source2Importer.show()
        """),
    },
    {
        'label': 'Ctrl Rig',
        'annotation': (
            'Open the Auto Control Rig builder for controls, helpers, twist '
            'joints, and stretchy IK setup.'
        ),
        'image': 'AutoRig.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            import auto_control_rig.constants as _con; importlib.reload(_con)
            import auto_control_rig.utils as _utl; importlib.reload(_utl)
            import auto_control_rig.helpers as _hlp; importlib.reload(_hlp)
            import auto_control_rig.skeleton as _skl; importlib.reload(_skl)
            import auto_control_rig.controls as _ctl; importlib.reload(_ctl)
            import auto_control_rig.stretchy as _str; importlib.reload(_str)
            import auto_control_rig.twist as _twt; importlib.reload(_twt)
            import auto_control_rig.mapping as _map; importlib.reload(_map)
            import auto_control_rig.operations as _ops; importlib.reload(_ops)
            import auto_control_rig.debug as _dbg; importlib.reload(_dbg)
            import auto_control_rig.builder as _bld; importlib.reload(_bld)
            import auto_control_rig.ui as _ui; importlib.reload(_ui)
            _ui.show_window()
        """),
    },
    {
        'label': 'AnimGen',
        'annotation': (
            'Open Animation Generator v2 for procedural walk, run, sidestep, '
            'and layered animation generation.'
        ),
        'image': 'AnimGenerator.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            # core
            import anim_gen_v2.core.patterns as _pat; importlib.reload(_pat)
            import anim_gen_v2.core.channel as _ch; importlib.reload(_ch)
            import anim_gen_v2.core.resolver as _res; importlib.reload(_res)
            import anim_gen_v2.core.engine as _eng; importlib.reload(_eng)
            import anim_gen_v2.core.presets as _pre; importlib.reload(_pre)
            # layers
            import anim_gen_v2.layers as _lay; importlib.reload(_lay)
            import anim_gen_v2.layers.walk_primary as _wp; importlib.reload(_wp)
            import anim_gen_v2.layers.walk_secondary as _ws; importlib.reload(_ws)
            import anim_gen_v2.layers.walk_arms as _wa; importlib.reload(_wa)
            import anim_gen_v2.layers.run_primary as _rp; importlib.reload(_rp)
            import anim_gen_v2.layers.sidestep_primary as _sp; importlib.reload(_sp)
            # ui
            import anim_gen_v2.ui.range_slider as _rs; importlib.reload(_rs)
            import anim_gen_v2.ui.window as _win; importlib.reload(_win)
            import anim_gen_v2.launcher as _lnc; importlib.reload(_lnc)
            _lnc.show()
        """),
    },
    {
        'label': 'Clip Set',
        'annotation': 'Clip Setter — s&box Character Export',
        'image': 'ClipSetter.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            import clip_setter.clips as _clp; importlib.reload(_clp)
            import clip_setter.export as _exp; importlib.reload(_exp)
            import clip_setter.ui as _cui; importlib.reload(_cui)
            _cui.show()
        """),
    },
    {
        'label': 'glTF\nI/O',
        'annotation': 'glTF / GLB Importer & Exporter',
        'image': 'gltfImpExp.png',
        'command': textwrap.dedent("""\
            import importlib, sys
            import ui_word_weighting as _uww; importlib.reload(_uww)
            # Drop any cached gltf_io.* modules so reload picks up new files
            for _m in [m for m in list(sys.modules) if m == 'gltf_io' or m.startswith('gltf_io.')]:
                del sys.modules[_m]
            import gltf_io
            gltf_io.show()
        """),
    },
    {
        'label': 'Blend\nSetup',
        'annotation': 'Multi-object blendshape setup and edit targets',
        'image': 'BlendShapeSetup.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            import blendshape_setup.logic as _bsl; importlib.reload(_bsl)
            import blendshape_setup.ui as _bsu; importlib.reload(_bsu)
            import blendshapeSetup; importlib.reload(blendshapeSetup)
            blendshapeSetup.show()
        """),
    },
    {
        'label': 'Tools',
        'annotation': 'Scene Tools (cleanup, plugin requires, helpers)',
        'image': 'SceneTools.png',
        'command': textwrap.dedent("""\
            import importlib
            import ui_word_weighting as _uww; importlib.reload(_uww)
            import tools_window.chypershade as _twh; importlib.reload(_twh)
            import tools_window.logic as _twl; importlib.reload(_twl)
            import tools_window.ui as _twu; importlib.reload(_twu)
            _twu.show_window()
        """),
    },
    {
        'label': 'Render\nLyr',
        'annotation': 'Render Layer Setter',
        'image': 'RenderLayerSetter.png',
        'command': textwrap.dedent("""\
            import importlib
            import render_layer_setter.logic as _rls; importlib.reload(_rls)
            import render_layer_setter.run as _rlr; importlib.reload(_rlr)
            _rlr.run()
        """),
    },
    {
        'label': 'Shelf\nSetup',
        'annotation': 'Reinstall / update this C_Scripts shelf',
        'image': 'refresh.png',
        'command': textwrap.dedent("""\
            import importlib
            import install_shelf; importlib.reload(install_shelf)
            install_shelf.install_deferred()
        """),
    },
]


# ── installer ─────────────────────────────────────────────────────

def _ensure_shelf():
    """Create the shelf if it doesn't already exist.  Return its full path."""
    top = mel.eval('$__tmp = $gShelfTopLevel')
    if cmds.shelfLayout(SHELF_NAME, exists=True, parent=top):
        return '{}|{}'.format(top, SHELF_NAME)
    cmds.shelfLayout(SHELF_NAME, parent=top)
    return '{}|{}'.format(top, SHELF_NAME)


def _clear_shelf(shelf_path):
    """Delete every button currently on the shelf."""
    children = cmds.shelfLayout(shelf_path, q=True, childArray=True) or []
    for child in children:
        cmds.deleteUI(child)


def _install_now():
    """Create (or refresh) the C_Scripts shelf with the latest buttons."""
    _ensure_default_icons()
    _register_icon_path()
    shelf_path = _ensure_shelf()
    _clear_shelf(shelf_path)

    button_tooltips = []
    for btn in _BUTTONS:
        tooltip = _button_tooltip(btn)
        button = cmds.shelfButton(
            parent=shelf_path,
            label=btn['label'],
            annotation=tooltip,
            image1=_button_icon(btn),
            command=btn['command'],
            sourceType='python',
        )
        button_tooltips.append((button, tooltip))
        _set_rollover_tooltip(button, tooltip)

    maya_utils.executeDeferred(
        lambda tooltips=button_tooltips: _apply_rollover_tooltips(tooltips)
    )

    # Switch to the newly created/updated shelf so the user sees it
    top = mel.eval('$__tmp = $gShelfTopLevel')
    cmds.tabLayout(top, e=True, selectTab=SHELF_NAME)
    print('// C_Scripts shelf installed  ({} buttons)'.format(len(_BUTTONS)))


def install_deferred():
    """Rebuild the shelf after the current UI callback completes."""
    maya_utils.executeDeferred(_install_now)


def install():
    """Public installer entry point."""
    _install_now()
